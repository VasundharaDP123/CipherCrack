"""Socket.IO layer: start a solver, stream its progress, allow cancelling.

Each browser tab gets at most one running solver, tracked by its session id.
The solver itself runs on a background task so the server stays responsive, and
it checks a per-session stop flag every reporting interval -- which is why
``stop_crack`` takes effect within a fraction of a second rather than at the end
of a ten-thousand-iteration run.

Events
------
``start_crack``  -> ``crack_started``, then ``crack_progress`` repeatedly,
                    then ``crack_done`` (or ``crack_error``)
``stop_crack``   -> ``crack_stopped``
"""

import threading
import time

from flask import request

import db
from ciphers.alphabet import clean
from ml import solvers
from ml.mcmc import letter_accuracy

# sid -> {"stop": Event, "started": float}
_jobs = {}
_lock = threading.Lock()

# How often each solver reports.  MCMC counts single iterations and needs a
# coarse interval; the HMM counts EM steps, of which there are only a hundred or
# so, and should report every one.
REPORT_EVERY = {
    "mcmc": 100,
    "hill_climbing": 100,
    "steepest_ascent": 1,
    "hmm": 1,
    "frequency": 0,
}

MAX_TEXT = 20_000

# Fastest the server will push progress frames to a browser (seconds).
MIN_FRAME_SECONDS = 0.05


def register(socketio):
    """Attach the handlers to a Flask-SocketIO server."""

    def emit(event, payload, sid):
        socketio.emit(event, payload, to=sid)

    @socketio.on("connect")
    def on_connect():
        emit("hello", {"solvers": solvers.catalogue()}, request.sid)

    @socketio.on("disconnect")
    def on_disconnect():
        with _lock:
            job = _jobs.pop(request.sid, None)
        if job:
            job["stop"].set()

    @socketio.on("stop_crack")
    def on_stop():
        with _lock:
            job = _jobs.get(request.sid)
        if job:
            job["stop"].set()
        emit("crack_stopped", {"ok": bool(job)}, request.sid)

    @socketio.on("start_crack")
    def on_start(payload):
        sid = request.sid
        payload = payload or {}
        ciphertext = (payload.get("ciphertext") or "").strip()
        solver_name = payload.get("solver", "mcmc")
        options = payload.get("options") or {}
        plaintext = clean(payload.get("plaintext") or "")

        if not ciphertext:
            return emit("crack_error", {"error": "ciphertext is required"}, sid)
        if len(ciphertext) > MAX_TEXT:
            return emit("crack_error",
                        {"error": f"ciphertext is longer than {MAX_TEXT} characters"}, sid)
        if solver_name not in solvers.SOLVERS:
            return emit("crack_error",
                        {"error": f"unknown solver {solver_name!r}"}, sid)

        with _lock:
            existing = _jobs.get(sid)
            if existing:
                existing["stop"].set()          # one run per tab
            stop = threading.Event()
            _jobs[sid] = {"stop": stop, "started": time.time()}

        def work():
            started = time.time()
            emit("crack_started", {
                "solver": solver_name,
                "label": solvers.SOLVERS[solver_name]["label"],
                "length": len(clean(ciphertext)),
                "options": options,
            }, sid)

            # The MCMC solver runs at tens of thousands of iterations a second,
            # so "every 100 iterations" can mean several hundred frames a second
            # -- far faster than the transport can drain them, and far faster
            # than an eye can read them.  Frames are therefore also throttled in
            # *time*: at most one every MIN_FRAME_SECONDS, with the last frame
            # of the run always allowed through.
            last_sent = [0.0]

            def on_progress(update):
                now = time.time()
                if now - last_sent[0] < MIN_FRAME_SECONDS:
                    return
                last_sent[0] = now
                if plaintext:
                    update["accuracy"] = letter_accuracy(update.get("text", ""), plaintext)
                update["elapsed"] = now - started
                emit("crack_progress", update, sid)
                # Hand the event loop a chance to flush, and to deliver any
                # stop_crack that arrived while we were computing.
                socketio.sleep(0.001)

            try:
                result = solvers.run(
                    solver_name, ciphertext, options,
                    callback=on_progress,
                    report_every=REPORT_EVERY.get(solver_name, 100),
                    should_stop=stop.is_set,
                )
            except Exception as error:          # noqa: BLE001 - report, never crash the socket
                emit("crack_error", {"error": str(error)}, sid)
                with _lock:
                    _jobs.pop(sid, None)
                return

            accuracy = letter_accuracy(result.plaintext, plaintext) if plaintext else None
            try:
                db.record_run(result, ciphertext, payload.get("cipher_type"),
                              accuracy, options)
            except Exception:                   # storage must never break the demo
                pass

            body = result.to_dict()
            body["accuracy"] = accuracy
            body["elapsed_wall"] = time.time() - started
            emit("crack_done", body, sid)

            with _lock:
                _jobs.pop(sid, None)

        socketio.start_background_task(work)
