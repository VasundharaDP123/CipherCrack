"""SQLite storage for solver runs and the Challenge Mode leaderboard.

Deliberately small: two tables, plain SQL, no ORM.  Connections are per-thread
because the solver runs on a background thread and SQLite objects cannot be
shared across threads.
"""

import json
import pathlib
import sqlite3
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "ciphercrack.sqlite3"

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    REAL    NOT NULL,
    solver        TEXT    NOT NULL,
    proposal      TEXT,
    cipher_type   TEXT,
    ciphertext    TEXT    NOT NULL,
    plaintext     TEXT    NOT NULL,
    key           TEXT    NOT NULL,
    score         REAL    NOT NULL,
    score_per_char REAL   NOT NULL,
    iterations    INTEGER NOT NULL,
    elapsed       REAL    NOT NULL,
    accuracy      REAL,
    text_length   INTEGER NOT NULL,
    options       TEXT
);

CREATE TABLE IF NOT EXISTS leaderboard (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   REAL    NOT NULL,
    player       TEXT    NOT NULL,
    text_length  INTEGER NOT NULL,
    difficulty   TEXT    NOT NULL,
    human_seconds REAL   NOT NULL,
    ai_seconds   REAL,
    human_accuracy REAL  NOT NULL,
    ai_accuracy  REAL,
    winner       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runs_solver ON runs(solver);
CREATE INDEX IF NOT EXISTS idx_leaderboard_time ON leaderboard(human_seconds);
"""


def connect():
    """One connection per thread, created on first use."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.commit()
        _local.conn = conn
    return conn


def init():
    connect()
    return DB_PATH


def record_run(result, ciphertext, cipher_type=None, accuracy=None, options=None):
    """Persist a finished solver run.  Returns the new row id."""
    conn = connect()
    cursor = conn.execute(
        """INSERT INTO runs (created_at, solver, proposal, cipher_type, ciphertext,
                             plaintext, key, score, score_per_char, iterations,
                             elapsed, accuracy, text_length, options)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            time.time(), result.solver, result.proposal, cipher_type,
            ciphertext[:4000], result.plaintext[:4000], result.key,
            result.score, result.score_per_char, result.iterations,
            result.elapsed, accuracy, len(ciphertext),
            json.dumps(options or {}),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def recent_runs(limit=50, solver=None):
    conn = connect()
    if solver:
        rows = conn.execute(
            "SELECT * FROM runs WHERE solver = ? ORDER BY id DESC LIMIT ?",
            (solver, limit),
        )
    else:
        rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
    return [dict(row) for row in rows]


def solver_summary():
    """Average accuracy, time and iterations per solver, for the Arena page."""
    conn = connect()
    rows = conn.execute(
        """SELECT solver,
                  COUNT(*)            AS runs,
                  AVG(accuracy)       AS mean_accuracy,
                  AVG(elapsed)        AS mean_seconds,
                  AVG(iterations)     AS mean_iterations,
                  AVG(score_per_char) AS mean_score_per_char
           FROM runs
           WHERE accuracy IS NOT NULL
           GROUP BY solver
           ORDER BY mean_accuracy DESC"""
    )
    return [dict(row) for row in rows]


def add_score(player, text_length, difficulty, human_seconds, human_accuracy,
              ai_seconds=None, ai_accuracy=None):
    if human_accuracy >= 0.95 and (ai_accuracy or 0) >= 0.95:
        winner = "human" if human_seconds <= (ai_seconds or 1e9) else "ai"
    elif human_accuracy >= 0.95:
        winner = "human"
    elif (ai_accuracy or 0) >= 0.95:
        winner = "ai"
    else:
        winner = "nobody"

    conn = connect()
    cursor = conn.execute(
        """INSERT INTO leaderboard (created_at, player, text_length, difficulty,
                                    human_seconds, ai_seconds, human_accuracy,
                                    ai_accuracy, winner)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (time.time(), player[:40] or "anonymous", int(text_length), difficulty,
         float(human_seconds), ai_seconds, float(human_accuracy), ai_accuracy, winner),
    )
    conn.commit()
    return cursor.lastrowid


def leaderboard(limit=25):
    conn = connect()
    rows = conn.execute(
        """SELECT * FROM leaderboard
           ORDER BY human_accuracy DESC, human_seconds ASC
           LIMIT ?""",
        (limit,),
    )
    return [dict(row) for row in rows]


def stats():
    conn = connect()
    runs = conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]
    scores = conn.execute("SELECT COUNT(*) AS n FROM leaderboard").fetchone()["n"]
    wins = conn.execute(
        "SELECT winner, COUNT(*) AS n FROM leaderboard GROUP BY winner"
    )
    return {
        "runs": runs,
        "challenges": scores,
        "wins": {row["winner"]: row["n"] for row in wins},
    }
