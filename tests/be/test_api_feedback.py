"""Tests for api/feedback.py endpoints."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.feedback.db as db_mod


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path: Path):
    """Point the feedback DB at a temp file for every test."""
    test_db = tmp_path / "test_feedback.db"
    original_path = db_mod._DB_PATH
    db_mod._DB_PATH = test_db
    db_mod._local.conn = None
    yield
    db_mod._DB_PATH = original_path
    db_mod._local.conn = None


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


class TestPostFeedback:
    def test_submit_thumbs_up(self, client):
        resp = client.post("/feedback", json={
            "query": "What is X?",
            "answer": "X is Y.",
            "rating": "up",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 1
        assert body["status"] == "saved"

    def test_submit_thumbs_down(self, client):
        resp = client.post("/feedback", json={
            "query": "What is X?",
            "answer": "X is Y.",
            "rating": "down",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

    def test_submit_with_suggestion(self, client):
        resp = client.post("/feedback", json={
            "query": "What is X?",
            "answer": "Wrong answer.",
            "rating": "down",
            "suggested_answer": "X is actually Z.",
        })
        assert resp.status_code == 200
        # Verify it was persisted
        items = db_mod.list_feedback()
        assert items[0]["suggested_answer"] == "X is actually Z."

    def test_submit_with_citations(self, client):
        resp = client.post("/feedback", json={
            "query": "What is X?",
            "answer": "X is Y.",
            "rating": "up",
            "citations": [{
                "doc_name": "a.pdf",
                "doc_path": "/documents/a.pdf",
                "snippet": "text",
                "chunk_id": "c1",
            }],
        })
        assert resp.status_code == 200
        items = db_mod.list_feedback()
        assert items[0]["citations"][0]["doc_name"] == "a.pdf"

    def test_submit_invalid_rating_rejected(self, client):
        resp = client.post("/feedback", json={
            "query": "q",
            "answer": "a",
            "rating": "maybe",
        })
        assert resp.status_code == 422

    def test_submit_missing_fields_rejected(self, client):
        resp = client.post("/feedback", json={"query": "q"})
        assert resp.status_code == 422


class TestGetFeedback:
    def test_list_empty(self, client):
        resp = client.get("/feedback")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_list_after_submissions(self, client):
        client.post("/feedback", json={"query": "q1", "answer": "a1", "rating": "up"})
        client.post("/feedback", json={"query": "q2", "answer": "a2", "rating": "down"})
        resp = client.get("/feedback")
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        # Newest first
        assert body["items"][0]["query"] == "q2"

    def test_list_filter_by_rating(self, client):
        client.post("/feedback", json={"query": "q1", "answer": "a1", "rating": "up"})
        client.post("/feedback", json={"query": "q2", "answer": "a2", "rating": "down"})
        resp = client.get("/feedback", params={"rating": "down"})
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["rating"] == "down"

    def test_list_pagination(self, client):
        for i in range(5):
            client.post("/feedback", json={"query": f"q{i}", "answer": "a", "rating": "up"})
        resp = client.get("/feedback", params={"limit": 2, "offset": 0})
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5

    def test_list_invalid_rating_rejected(self, client):
        resp = client.get("/feedback", params={"rating": "maybe"})
        assert resp.status_code == 422
