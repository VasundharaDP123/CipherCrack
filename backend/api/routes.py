"""REST routes.  One-shot requests only -- live solving goes over Socket.IO."""

import random

from flask import Blueprint, jsonify, request

import ciphers
import db
from ciphers.alphabet import clean
from ml import solvers
from ml.gaussian import (
    GaussianMixture2D,
    effective_sample_size,
    metropolis_2d,
)
from ml.identifier import get_identifier
from ml.language_model import get_model
from ml.mcmc import letter_accuracy
from ml.proposals import PROPOSAL_LABELS, PROPOSAL_NAMES

api = Blueprint("api", __name__, url_prefix="/api")

MAX_TEXT = 20_000


def _text(payload, field="text", required=True):
    value = (payload.get(field) or "").strip()
    if required and not value:
        raise ValueError(f"'{field}' is required")
    if len(value) > MAX_TEXT:
        raise ValueError(f"'{field}' is longer than {MAX_TEXT} characters")
    return value


@api.errorhandler(ValueError)
def _bad_request(error):
    return jsonify({"error": str(error)}), 400


def _fail(message, status=400):
    return jsonify({"error": message}), status


# --------------------------------------------------------------------- meta

@api.get("/health")
def health():
    model = get_model()
    try:
        identifier = get_identifier()
        identifier_ready = True
        identifier_accuracy = identifier.metrics.get("forest", {}).get("accuracy")
    except FileNotFoundError:
        identifier_ready = False
        identifier_accuracy = None
    return jsonify({
        "status": "ok",
        "language_model": model.summary(),
        "identifier_ready": identifier_ready,
        "identifier_accuracy": identifier_accuracy,
        "database": db.stats(),
    })


@api.get("/catalogue")
def catalogue():
    """Everything the UI needs to build its dropdowns."""
    return jsonify({
        "ciphers": [
            {"name": name, **ciphers.CIPHER_INFO[name]} for name in ciphers.CIPHER_NAMES
        ],
        "solvers": solvers.catalogue(),
        "proposals": [
            {"name": name, "label": PROPOSAL_LABELS[name]} for name in PROPOSAL_NAMES
        ],
    })


# ------------------------------------------------------------------ encrypt

@api.post("/encrypt")
def encrypt():
    payload = request.get_json(silent=True) or {}
    try:
        text = _text(payload)
        name = payload.get("cipher", "substitution")
        key = payload.get("key") or None
        ciphertext, used_key = ciphers.encrypt(name, text, key=key)
    except ValueError as error:
        return _fail(str(error))

    return jsonify({
        "cipher": name,
        "key": str(used_key),
        "plaintext": clean(text),
        "ciphertext": ciphertext,
        "length": len(clean(text)),
        "score_per_char": get_model().score_per_char(text),
    })


@api.post("/decrypt")
def decrypt():
    payload = request.get_json(silent=True) or {}
    try:
        text = _text(payload)
        name = payload.get("cipher", "substitution")
        key = payload.get("key")
        if not key:
            raise ValueError("'key' is required to decrypt")
        plaintext = ciphers.decrypt(name, text, key)
    except ValueError as error:
        return _fail(str(error))
    return jsonify({"cipher": name, "plaintext": plaintext})


@api.get("/random-key/<cipher>")
def random_key(cipher):
    try:
        return jsonify({"cipher": cipher, "key": str(ciphers.random_key(cipher))})
    except ValueError as error:
        return _fail(str(error))


# ----------------------------------------------------------------- identify

@api.post("/identify")
def identify():
    payload = request.get_json(silent=True) or {}
    try:
        text = _text(payload)
        identifier = get_identifier()
    except ValueError as error:
        return _fail(str(error))
    except FileNotFoundError as error:
        return _fail(str(error), 503)

    model = payload.get("model", "forest")
    if model not in ("forest", "adaboost"):
        return _fail("'model' must be 'forest' or 'adaboost'")
    return jsonify(identifier.identify(text, model=model))


@api.get("/identify/clusters")
def clusters():
    """Scatter points for the K-Means map on the Identify page."""
    import pathlib

    import numpy as np

    try:
        identifier = get_identifier()
    except FileNotFoundError as error:
        return _fail(str(error), 503)

    path = pathlib.Path(__file__).resolve().parents[1] / "data" / "generated" / "cipher_dataset.npz"
    if not path.exists():
        return _fail("dataset missing; run python -m scripts.build_dataset", 503)

    blob = np.load(path, allow_pickle=True)
    limit = min(int(request.args.get("limit", 600)), 2000)
    points = identifier.cluster_scatter(blob["X"], blob["y"], limit=limit)
    return jsonify({
        "points": points,
        "classes": identifier.classes,
        "explained_variance": identifier.pca.explained_variance_ratio_,
        "silhouette": identifier.metrics.get("silhouette"),
    })


@api.get("/identify/metrics")
def identifier_metrics():
    try:
        identifier = get_identifier()
    except FileNotFoundError as error:
        return _fail(str(error), 503)
    return jsonify({
        "metrics": identifier.metrics,
        "top_features": identifier.top_features(12),
        "forest": identifier.forest.describe(),
        "adaboost": identifier.adaboost.describe(),
    })


# -------------------------------------------------------------------- crack

@api.post("/crack")
def crack():
    """Blocking solve.  The Crack Live page uses the Socket.IO route instead."""
    payload = request.get_json(silent=True) or {}
    try:
        text = _text(payload, "ciphertext")
        name = payload.get("solver", "mcmc")
        options = payload.get("options") or {}
        result = solvers.run(name, text, options, report_every=0)
    except ValueError as error:
        return _fail(str(error))

    plaintext = payload.get("plaintext")
    accuracy = letter_accuracy(result.plaintext, clean(plaintext)) if plaintext else None
    db.record_run(result, text, payload.get("cipher_type"), accuracy, options)

    body = result.to_dict()
    body["accuracy"] = accuracy
    return jsonify(body)


# -------------------------------------------------------------------- arena

@api.post("/arena/run")
def arena_run():
    """Run several solvers on one ciphertext and compare them fairly."""
    payload = request.get_json(silent=True) or {}
    try:
        text = _text(payload, "ciphertext")
    except ValueError as error:
        return _fail(str(error))

    names = payload.get("solvers") or solvers.SOLVER_NAMES
    plaintext = clean(payload.get("plaintext") or "")
    options = payload.get("options") or {}

    rows = []
    for name in names:
        if name not in solvers.SOLVERS:
            continue
        try:
            result = solvers.run(name, text, options, report_every=0)
        except Exception as error:                      # one solver must not sink the page
            rows.append({"solver": name, "error": str(error)})
            continue
        accuracy = letter_accuracy(result.plaintext, plaintext) if plaintext else None
        db.record_run(result, text, payload.get("cipher_type"), accuracy, options)
        rows.append({
            "solver": name,
            "label": solvers.SOLVERS[name]["label"],
            "accuracy": accuracy,
            "score_per_char": result.extra.get("plaintext_score_per_char"),
            "own_score_per_char": result.score_per_char,
            "iterations": result.iterations,
            "elapsed": result.elapsed,
            "key": result.key,
            "plaintext": result.plaintext[:600],
        })

    rows.sort(key=lambda r: (-(r.get("accuracy") or -1), r.get("elapsed") or 1e9))
    return jsonify({
        "results": rows,
        "target_score_per_char": (
            solvers.plaintext_score(plaintext) if plaintext else None
        ),
    })


@api.get("/arena/results")
def arena_results():
    return jsonify({
        "summary": db.solver_summary(),
        "recent": db.recent_runs(int(request.args.get("limit", 40))),
    })


# --------------------------------------------------------------- playground

@api.post("/playground/sample")
def playground_sample():
    payload = request.get_json(silent=True) or {}
    try:
        step_size = float(payload.get("step_size", 1.0))
        n_samples = min(int(payload.get("n_samples", 3000)), 20000)
        burn_in = min(int(payload.get("burn_in", 300)), 5000)
        seed = payload.get("seed")
    except (TypeError, ValueError):
        return _fail("step_size, n_samples and burn_in must be numbers")
    if not 0.001 <= step_size <= 20:
        return _fail("step_size must be between 0.001 and 20")

    target = GaussianMixture2D()
    run = metropolis_2d(target, step_size=step_size, n_samples=n_samples,
                        burn_in=burn_in, seed=seed)
    samples = run["samples"]
    ess = effective_sample_size(samples)

    # Thin the points sent to the browser; drawing 20,000 dots helps nobody.
    stride = max(1, len(samples) // 2500)
    axis, density = target.grid()

    return jsonify({
        "step_size": step_size,
        "acceptance_rate": run["acceptance_rate_post_burnin"],
        "n_samples": len(samples),
        "effective_sample_size": ess,
        "ess_per_sample": [e / max(len(samples), 1) for e in ess],
        "samples": samples[::stride].tolist(),
        "trace_x": samples[:400, 0].tolist(),
        "grid_axis": axis,
        "grid_density": density,
        "components": [
            {"mean": c["mean"], "weight": c["weight"]} for c in target.components
        ],
    })


@api.post("/playground/compare")
def playground_compare():
    """Our Metropolis sampler against emcee on the same target."""
    payload = request.get_json(silent=True) or {}
    step_size = float(payload.get("step_size", 1.0))
    n_samples = min(int(payload.get("n_samples", 3000)), 20000)
    target = GaussianMixture2D()

    own = metropolis_2d(target, step_size=step_size, n_samples=n_samples,
                        burn_in=300, seed=payload.get("seed"))
    rows = [{
        "sampler": "own Metropolis-Hastings",
        "acceptance_rate": own["acceptance_rate_post_burnin"],
        "effective_sample_size": effective_sample_size(own["samples"]),
        "n_samples": len(own["samples"]),
    }]

    try:
        import emcee
        import numpy as np

        n_walkers = 16
        rng = np.random.default_rng(payload.get("seed") or 0)
        start = rng.normal(size=(n_walkers, 2))
        sampler = emcee.EnsembleSampler(
            n_walkers, 2, lambda p: target.log_density(p)
        )
        steps = max(n_samples // n_walkers, 50)
        sampler.run_mcmc(start, steps + 50, progress=False)
        chain = sampler.get_chain(discard=50, flat=True)
        rows.append({
            "sampler": "emcee (library)",
            "acceptance_rate": float(np.mean(sampler.acceptance_fraction)),
            "effective_sample_size": effective_sample_size(chain),
            "n_samples": int(len(chain)),
        })
    except Exception as error:
        rows.append({"sampler": "emcee (library)", "error": str(error)})

    return jsonify({"results": rows})


# -------------------------------------------------------------- leaderboard

@api.get("/leaderboard")
def get_leaderboard():
    return jsonify({
        "scores": db.leaderboard(int(request.args.get("limit", 25))),
        "stats": db.stats(),
    })


@api.post("/leaderboard")
def post_leaderboard():
    payload = request.get_json(silent=True) or {}
    try:
        row_id = db.add_score(
            player=str(payload.get("player", "anonymous")),
            text_length=int(payload.get("text_length", 0)),
            difficulty=str(payload.get("difficulty", "medium")),
            human_seconds=float(payload.get("human_seconds", 0)),
            human_accuracy=float(payload.get("human_accuracy", 0)),
            ai_seconds=payload.get("ai_seconds"),
            ai_accuracy=payload.get("ai_accuracy"),
        )
    except (TypeError, ValueError) as error:
        return _fail(f"bad score payload: {error}")
    return jsonify({"id": row_id, "scores": db.leaderboard()})


# ----------------------------------------------------------------- challenge

CHALLENGE_TEXTS = [
    "THE ONLY WAY TO DISCOVER THE LIMITS OF THE POSSIBLE IS TO GO BEYOND THEM INTO THE IMPOSSIBLE",
    "IN THE MIDDLE OF DIFFICULTY LIES OPPORTUNITY AND THE PATIENT MIND WILL ALWAYS FIND IT",
    "IT IS A CAPITAL MISTAKE TO THEORISE BEFORE ONE HAS DATA FOR THEN ONE TWISTS FACTS TO SUIT THEORIES",
    "NOT EVERYTHING THAT CAN BE COUNTED COUNTS AND NOT EVERYTHING THAT COUNTS CAN BE COUNTED",
    "THE GREATEST ENEMY OF KNOWLEDGE IS NOT IGNORANCE IT IS THE ILLUSION OF KNOWLEDGE",
    "A ROOM WITHOUT BOOKS IS LIKE A BODY WITHOUT A SOUL AND A MIND WITHOUT QUESTIONS IS QUIETER STILL",
]

DIFFICULTY = {
    "easy": {"length": 220, "hint_letters": 6},
    "medium": {"length": 140, "hint_letters": 3},
    "hard": {"length": 90, "hint_letters": 0},
}


@api.get("/challenge/new")
def challenge_new():
    difficulty = request.args.get("difficulty", "medium")
    if difficulty not in DIFFICULTY:
        return _fail(f"difficulty must be one of {list(DIFFICULTY)}")
    settings = DIFFICULTY[difficulty]

    rng = random.Random()
    plaintext = clean(rng.choice(CHALLENGE_TEXTS))
    while len(plaintext) < settings["length"]:
        plaintext += " " + clean(rng.choice(CHALLENGE_TEXTS))
    plaintext = plaintext[: settings["length"]].rsplit(" ", 1)[0]

    key = ciphers.substitution.random_key(rng)
    ciphertext = ciphers.substitution.encrypt(plaintext, key)
    decryption_key = ciphers.substitution.invert_key(key)

    # Hints reveal a few cipher->plain pairs, chosen from the letters that
    # actually appear, so a hint is never wasted on an absent letter.
    present = sorted({c for c in ciphertext if c != " "})
    rng.shuffle(present)
    hints = {
        letter: decryption_key[ord(letter) - 65]
        for letter in present[: settings["hint_letters"]]
    }

    return jsonify({
        "ciphertext": ciphertext,
        "plaintext": plaintext,
        "difficulty": difficulty,
        "length": len(plaintext),
        "hints": hints,
    })
