"""Tests for api/health.py."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_qdrant_ok(self, client):
        fake_settings = MagicMock()
        mock_store = MagicMock()

        with (
            patch("app.api.health.get_settings", return_value=fake_settings),
            patch("app.api.health.QdrantStore", return_value=mock_store),
        ):
            resp = client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["qdrant"] == "ok"

    def test_health_qdrant_unreachable(self, client):
        fake_settings = MagicMock()
        mock_store = MagicMock()
        mock_store.healthcheck.side_effect = ConnectionError("refused")

        with (
            patch("app.api.health.get_settings", return_value=fake_settings),
            patch("app.api.health.QdrantStore", return_value=mock_store),
        ):
            resp = client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["qdrant"] == "unreachable"
