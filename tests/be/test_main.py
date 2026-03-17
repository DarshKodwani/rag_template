"""Tests for main.py — verify app creation, middleware, and routes."""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestApp:
    def test_app_exists(self):
        from app.main import app
        assert app is not None
        assert app.title == "RAG Demo API"

    def test_routes_registered(self):
        from app.main import app
        route_paths = [r.path for r in app.routes]
        assert "/health" in route_paths
        assert "/chat" in route_paths
        assert "/ingest/reindex" in route_paths
        assert "/ingest/upload" in route_paths

    def test_cors_middleware_present(self):
        from app.main import app
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes

    def test_documents_mount(self):
        from app.main import app
        mount_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/documents" in mount_paths
