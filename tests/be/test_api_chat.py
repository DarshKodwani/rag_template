"""Tests for api/chat.py."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Create a TestClient with get_settings overridden."""
    from app.main import app
    return TestClient(app)


class TestChatEndpoint:
    def test_chat_success(self, client):
        from app.core.models import ChatResponse
        fake_response = ChatResponse(answer="Test answer", citations=[])
        fake_settings = MagicMock()
        fake_settings.any_keys_present = True

        with (
            patch("app.api.chat.get_settings", return_value=fake_settings),
            patch("app.api.chat.answer_query", return_value=fake_response),
        ):
            resp = client.post("/chat", json={"message": "hello"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "Test answer"
        assert body["citations"] == []

    def test_chat_no_keys_returns_500(self, client):
        fake_settings = MagicMock()
        fake_settings.any_keys_present = False

        with patch("app.api.chat.get_settings", return_value=fake_settings):
            resp = client.post("/chat", json={"message": "hello"})

        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"]

    def test_chat_exception_returns_500(self, client):
        fake_settings = MagicMock()
        fake_settings.any_keys_present = True

        with (
            patch("app.api.chat.get_settings", return_value=fake_settings),
            patch("app.api.chat.answer_query", side_effect=RuntimeError("boom")),
        ):
            resp = client.post("/chat", json={"message": "hello"})

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Chat query failed"
