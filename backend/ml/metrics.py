"""Classification metrics, written from scratch so the report can quote them."""

import numpy as np


def confusion_matrix(y_true, y_pred, n_classes):
    y_true = np.asarray(y_true, dtype=np.int64)
    y_pred = np.asarray(y_pred, dtype=np.int64)
    flat = np.bincount(y_true * n_classes + y_pred, minlength=n_classes ** 2)
    return flat.reshape(n_classes, n_classes)


def classification_report(y_true, y_pred, classes):
    """Per-class precision / recall / F1 plus macro averages and accuracy."""
    n = len(classes)
    matrix = confusion_matrix(y_true, y_pred, n)
    support = matrix.sum(axis=1)
    predicted = matrix.sum(axis=0)
    correct = np.diag(matrix)

    precision = np.divide(correct, predicted, out=np.zeros(n), where=predicted > 0)
    recall = np.divide(correct, support, out=np.zeros(n), where=support > 0)
    denominator = precision + recall
    f1 = np.divide(2 * precision * recall, denominator,
                   out=np.zeros(n), where=denominator > 0)

    return {
        "accuracy": float(correct.sum() / max(matrix.sum(), 1)),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1.mean()),
        "confusion_matrix": matrix.tolist(),
        "classes": list(classes),
        "per_class": [
            {
                "cipher": classes[i],
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i in range(n)
        ],
    }


def train_test_split(n, test_size=0.2, random_state=0, stratify=None):
    """Index split, stratified by class when ``stratify`` is given."""
    rng = np.random.default_rng(random_state)
    if stratify is None:
        order = rng.permutation(n)
        cut = int(n * (1 - test_size))
        return order[:cut], order[cut:]

    stratify = np.asarray(stratify)
    train, test = [], []
    for label in np.unique(stratify):
        rows = np.flatnonzero(stratify == label)
        rows = rows[rng.permutation(len(rows))]
        cut = int(len(rows) * (1 - test_size))
        train.append(rows[:cut])
        test.append(rows[cut:])
    train, test = np.concatenate(train), np.concatenate(test)
    return train[rng.permutation(len(train))], test[rng.permutation(len(test))]
