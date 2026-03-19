"""Tests for feedback SQLite storage (app/feedback/db.py)."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

import pytest

import app.feedback.db as db_mod


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path: Path):
    """Point the feedback DB at a temp file for every test."""
    test_db = tmp_path / "test_feedback.db"
    original_path = db_mod._DB_PATH
    db_mod._DB_PATH = test_db
    # Reset thread-local so a fresh connection is made
    db_mod._local.conn = None
    yield test_db
    db_mod._DB_PATH = original_path
    db_mod._local.conn = None


class TestSaveFeedback:
    def test_save_returns_row_id(self):
        row_id = db_mod.save_feedback(query="q1", answer="a1", rating="up")
        assert row_id == 1

    def test_save_increments_ids(self):
        id1 = db_mod.save_feedback(query="q1", answer="a1", rating="up")
        id2 = db_mod.save_feedback(query="q2", answer="a2", rating="down")
        assert id2 == id1 + 1

    def test_save_with_suggestion(self):
        row_id = db_mod.save_feedback(
            query="q1", answer="a1", rating="down", suggested_answer="better answer"
        )
        rows = db_mod.list_feedback()
        assert len(rows) == 1
        assert rows[0]["suggested_answer"] == "better answer"

    def test_save_with_citations(self):
        cits = [{"doc_name": "a.pdf", "snippet": "text"}]
        db_mod.save_feedback(query="q1", answer="a1", rating="up", citations=cits)
        rows = db_mod.list_feedback()
        assert rows[0]["citations"] == cits

    def test_save_invalid_rating_rejected(self):
        with pytest.raises(sqlite3.IntegrityError):
            db_mod.save_feedback(query="q", answer="a", rating="maybe")


class TestListFeedback:
    def test_list_empty(self):
        assert db_mod.list_feedback() == []

    def test_list_returns_newest_first(self):
        db_mod.save_feedback(query="first", answer="a", rating="up")
        db_mod.save_feedback(query="second", answer="a", rating="down")
        rows = db_mod.list_feedback()
        assert rows[0]["query"] == "second"
        assert rows[1]["query"] == "first"

    def test_list_respects_limit(self):
        for i in range(5):
            db_mod.save_feedback(query=f"q{i}", answer="a", rating="up")
        rows = db_mod.list_feedback(limit=3)
        assert len(rows) == 3

    def test_list_respects_offset(self):
        for i in range(5):
            db_mod.save_feedback(query=f"q{i}", answer="a", rating="up")
        rows = db_mod.list_feedback(limit=2, offset=3)
        assert len(rows) == 2
        # offset=3 newest-first means q1 and q0
        assert rows[0]["query"] == "q1"
        assert rows[1]["query"] == "q0"

    def test_list_filters_by_rating(self):
        db_mod.save_feedback(query="good", answer="a", rating="up")
        db_mod.save_feedback(query="bad", answer="a", rating="down")
        db_mod.save_feedback(query="good2", answer="a", rating="up")
        ups = db_mod.list_feedback(rating="up")
        assert len(ups) == 2
        assert all(r["rating"] == "up" for r in ups)

    def test_list_citations_deserialized(self):
        cits = [{"doc": "x.pdf"}]
        db_mod.save_feedback(query="q", answer="a", rating="up", citations=cits)
        rows = db_mod.list_feedback()
        assert rows[0]["citations"] == cits

    def test_list_null_citations_stays_none(self):
        db_mod.save_feedback(query="q", answer="a", rating="up")
        rows = db_mod.list_feedback()
        assert rows[0]["citations"] is None


class TestCountFeedback:
    def test_count_empty(self):
        assert db_mod.count_feedback() == 0

    def test_count_all(self):
        db_mod.save_feedback(query="q1", answer="a", rating="up")
        db_mod.save_feedback(query="q2", answer="a", rating="down")
        assert db_mod.count_feedback() == 2

    def test_count_filtered(self):
        db_mod.save_feedback(query="q1", answer="a", rating="up")
        db_mod.save_feedback(query="q2", answer="a", rating="down")
        db_mod.save_feedback(query="q3", answer="a", rating="up")
        assert db_mod.count_feedback(rating="up") == 2
        assert db_mod.count_feedback(rating="down") == 1


class TestInitDb:
    def test_init_db_creates_table(self, tmp_path):
        custom_path = tmp_path / "custom.db"
        db_mod.init_db(custom_path)
        conn = sqlite3.connect(str(custom_path))
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback'"
        ).fetchall()
        assert len(tables) == 1
        conn.close()


class TestEnsureTableIdempotent:
    def test_double_create_no_error(self):
        """Calling _ensure_table twice should not raise."""
        conn = db_mod._get_conn()
        db_mod._ensure_table(conn)
        db_mod._ensure_table(conn)
