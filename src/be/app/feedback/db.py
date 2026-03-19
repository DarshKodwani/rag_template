"""SQLite-backed feedback storage."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import PROJECT_ROOT

_DB_PATH = PROJECT_ROOT / "data" / "feedback.db"
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating the DB/table if needed."""
    conn: Optional[sqlite3.Connection] = getattr(_local, "conn", None)
    if conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(_DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    _ensure_table(conn)
    return conn


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL,
            query       TEXT    NOT NULL,
            answer      TEXT    NOT NULL,
            rating      TEXT    NOT NULL CHECK(rating IN ('up', 'down')),
            suggested_answer TEXT,
            citations   TEXT
        )
        """
    )
    conn.commit()


def save_feedback(
    *,
    query: str,
    answer: str,
    rating: str,
    suggested_answer: Optional[str] = None,
    citations: Optional[list[dict]] = None,
) -> int:
    """Insert a feedback row and return the new row id."""
    conn = _get_conn()
    cur = conn.execute(
        """
        INSERT INTO feedback (timestamp, query, answer, rating, suggested_answer, citations)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            query,
            answer,
            rating,
            suggested_answer,
            json.dumps(citations) if citations else None,
        ),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def list_feedback(
    *,
    limit: int = 50,
    offset: int = 0,
    rating: Optional[str] = None,
) -> list[dict]:
    """Return feedback rows ordered by newest first."""
    conn = _get_conn()
    if rating:
        rows = conn.execute(
            "SELECT * FROM feedback WHERE rating = ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (rating, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    results = []
    for row in rows:
        d = dict(row)
        if d.get("citations"):
            d["citations"] = json.loads(d["citations"])
        results.append(d)
    return results


def count_feedback(*, rating: Optional[str] = None) -> int:
    """Return total count of feedback rows, optionally filtered by rating."""
    conn = _get_conn()
    if rating:
        row = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE rating = ?", (rating,)
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()
    return row[0]


def init_db(db_path: Optional[Path] = None) -> None:
    """Explicitly initialise the DB (useful in tests to point at a temp file)."""
    if db_path is not None:
        import app.feedback.db as _self

        _self._DB_PATH = db_path
        _local.conn = None
    # Force table creation
    _get_conn()
