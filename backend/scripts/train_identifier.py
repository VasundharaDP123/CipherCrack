"""Train the cipher identifier and compare it against scikit-learn.

    python -m scripts.train_identifier

Reports accuracy / precision / recall / F1 and the confusion matrix for the
from-scratch forest and AdaBoost, the same for the scikit-learn equivalents,
and the clustering quality for K-Means -- every number the evaluation plan
asks for, in one run.
"""

import argparse
import pathlib
import time

import numpy as np

from ciphers import CIPHER_NAMES
from ml.identifier import MODEL_PATH, CipherIdentifier, cluster_matrix
from ml.kmeans import KMeans, elbow_curve, silhouette_score
from ml.metrics import classification_report, train_test_split

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "generated" / "cipher_dataset.npz"


def show(title, report):
    print(f"\n{title}")
    print(f"  accuracy {report['accuracy']:.3%}   macro-F1 {report['macro_f1']:.3f}   "
          f"precision {report['macro_precision']:.3f}   recall {report['macro_recall']:.3f}")
    print(f"  {'class':15s} {'prec':>6s} {'rec':>6s} {'f1':>6s} {'n':>6s}")
    for row in report["per_class"]:
        print(f"  {row['cipher']:15s} {row['precision']:6.3f} {row['recall']:6.3f} "
              f"{row['f1']:6.3f} {row['support']:6d}")
    print(f"  confusion (rows = true, cols = predicted): {report['classes']}")
    for name, row in zip(report["classes"], report["confusion_matrix"]):
        print(f"    {name:15s} {row}")


def sklearn_comparison(X_train, y_train, X_test, y_test, seed):
    """Same data, library implementations, for the report's comparison table."""
    try:
        from sklearn.cluster import KMeans as SkKMeans
        from sklearn.ensemble import AdaBoostClassifier, RandomForestClassifier
        from sklearn.metrics import silhouette_score as sk_silhouette
        from sklearn.tree import DecisionTreeClassifier
    except ImportError:
        print("\nscikit-learn is not installed; skipping the library comparison")
        return None

    out = {}
    start = time.perf_counter()
    forest = RandomForestClassifier(
        n_estimators=150, max_features="sqrt", min_samples_leaf=2, random_state=seed
    ).fit(X_train, y_train)
    out["forest"] = (
        classification_report(y_test, forest.predict(X_test), CIPHER_NAMES),
        time.perf_counter() - start,
    )

    start = time.perf_counter()
    boost = AdaBoostClassifier(
        estimator=DecisionTreeClassifier(max_depth=1),
        n_estimators=200, algorithm="SAMME", random_state=seed,
    ).fit(X_train, y_train)
    out["adaboost"] = (
        classification_report(y_test, boost.predict(X_test), CIPHER_NAMES),
        time.perf_counter() - start,
    )
    out["_sk"] = (SkKMeans, sk_silhouette)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trees", type=int, default=150)
    parser.add_argument("--stumps", type=int, default=200)
    parser.add_argument("--skip-sklearn", action="store_true")
    args = parser.parse_args()

    if not DATA.exists():
        raise SystemExit(f"{DATA} is missing. Run: python -m scripts.build_dataset")

    blob = np.load(DATA, allow_pickle=True)
    X, y = blob["X"], blob["y"]
    print(f"dataset {X.shape}, classes {list(blob['classes'])}")

    train_rows, test_rows = train_test_split(
        len(y), test_size=0.2, random_state=args.seed, stratify=y
    )
    X_train, y_train = X[train_rows], y[train_rows]
    X_test, y_test = X[test_rows], y[test_rows]
    print(f"train {len(train_rows)}   test {len(test_rows)}")

    identifier = CipherIdentifier()
    start = time.perf_counter()
    identifier.fit(
        X_train, y_train,
        n_estimators=args.trees, n_stumps=args.stumps, random_state=args.seed,
        progress=lambda stage: print(f"  fitting {stage} ...", flush=True),
    )
    train_seconds = time.perf_counter() - start

    forest_report = classification_report(
        y_test, identifier.forest.predict(X_test), CIPHER_NAMES
    )
    ada_report = classification_report(
        y_test, identifier.adaboost.predict(X_test), CIPHER_NAMES
    )
    show("from-scratch RandomForest", forest_report)
    print(f"  out-of-bag accuracy: {identifier.forest.oob_score_:.3%}")
    show("from-scratch AdaBoost (SAMME stumps)", ada_report)

    print("\ntop features by forest importance:")
    for row in identifier.top_features(10):
        print(f"  {row['feature']:24s} {row['importance']:.4f}")

    # --- clustering -------------------------------------------------------
    scaled = cluster_matrix(identifier, X_test)
    labels = identifier.kmeans.predict(scaled)
    own_silhouette = silhouette_score(scaled[:800], labels[:800])
    print(f"\nK-Means (k=4, unsupervised)")
    print(f"  silhouette (own)        : {own_silhouette:.4f}")
    print(f"  inertia                 : {identifier.kmeans.inertia_:,.1f}")
    print(f"  quantization error      : {identifier.kmeans.quantization_error(scaled):.4f}")
    print(f"  cluster vs true-class contingency (rows = cluster):")
    for k in range(4):
        counts = [int(((labels == k) & (y_test == c)).sum()) for c in range(4)]
        print(f"    cluster {k}: {counts}")
    print("  elbow curve:")
    for point in elbow_curve(scaled[:1500], range(2, 9), random_state=args.seed, n_init=4):
        print(f"    k={point['k']}  inertia={point['inertia']:,.1f}")

    # --- library comparison ----------------------------------------------
    if not args.skip_sklearn:
        results = sklearn_comparison(X_train, y_train, X_test, y_test, args.seed)
        if results:
            show("scikit-learn RandomForestClassifier", results["forest"][0])
            show("scikit-learn AdaBoostClassifier (SAMME)", results["adaboost"][0])
            SkKMeans, sk_silhouette = results["_sk"]
            sk_labels = SkKMeans(n_clusters=4, n_init=10,
                                 random_state=args.seed).fit_predict(scaled)
            print(f"\nsilhouette (sklearn KMeans): "
                  f"{sk_silhouette(scaled[:800], sk_labels[:800]):.4f}")
            print("\nsummary (accuracy, train seconds):")
            print(f"  own forest      {forest_report['accuracy']:.3%}  {train_seconds:6.1f}s (all three models)")
            print(f"  sklearn forest  {results['forest'][0]['accuracy']:.3%}  {results['forest'][1]:6.1f}s")
            print(f"  own adaboost    {ada_report['accuracy']:.3%}")
            print(f"  sklearn adaboost{results['adaboost'][0]['accuracy']:.3%}  {results['adaboost'][1]:6.1f}s")
            identifier.metrics["sklearn"] = {
                "forest": results["forest"][0],
                "adaboost": results["adaboost"][0],
            }

    identifier.metrics.update({
        "forest": forest_report,
        "adaboost": ada_report,
        "oob_score": identifier.forest.oob_score_,
        "silhouette": own_silhouette,
        "train_seconds": train_seconds,
        "n_train": int(len(train_rows)),
        "n_test": int(len(test_rows)),
    })
    identifier.save(MODEL_PATH)
    print(f"\nsaved {MODEL_PATH}")


if __name__ == "__main__":
    main()
