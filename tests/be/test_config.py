"""Tests for core/config.py."""
from __future__ import annotations

from unittest.mock import patch

import pytest


class TestSettings:
    def test_default_values(self):
        from app.core.config import Settings

        with patch.dict("os.environ", {}, clear=True):
            s = Settings(
                _env_file=None,  # type: ignore[call-arg]
            )
        assert s.qdrant_url == "http://localhost:6333"
        assert s.qdrant_collection == "documents"
        assert s.chunk_size == 800
        assert s.chunk_overlap == 120
        assert s.top_k == 5
        assert s.openai_chat_model == "gpt-4o"
        assert s.openai_embedding_model == "text-embedding-3-small"
        assert s.azure_openai_api_version == "2024-02-01"

    def test_azure_keys_present_true(self):
        from app.core.config import Settings

        s = Settings(
            azure_openai_endpoint="https://foo.openai.azure.com/",
            azure_openai_api_key="key123",
            _env_file=None,  # type: ignore[call-arg]
        )
        assert s.azure_keys_present is True

    def test_azure_keys_present_false_when_missing(self):
        from app.core.config import Settings

        s = Settings(
            azure_openai_endpoint="",
            azure_openai_api_key="",
            _env_file=None,  # type: ignore[call-arg]
        )
        assert s.azure_keys_present is False

    def test_openai_keys_present_true(self):
        from app.core.config import Settings

        s = Settings(
            openai_api_key="sk-test123",
            _env_file=None,  # type: ignore[call-arg]
        )
        assert s.openai_keys_present is True

    def test_openai_keys_present_false(self):
        from app.core.config import Settings

        s = Settings(
            openai_api_key="",
            _env_file=None,  # type: ignore[call-arg]
        )
        assert s.openai_keys_present is False

    def test_any_keys_present_with_openai(self):
        from app.core.config import Settings

        s = Settings(
            openai_api_key="sk-test",
            _env_file=None,  # type: ignore[call-arg]
        )
        assert s.any_keys_present is True

    def test_any_keys_present_with_azure(self):
        from app.core.config import Settings

        s = Settings(
            azure_openai_endpoint="https://foo.openai.azure.com/",
            azure_openai_api_key="key",
            _env_file=None,  # type: ignore[call-arg]
        )
        assert s.any_keys_present is True

    def test_any_keys_present_false(self):
        from app.core.config import Settings

        s = Settings(
            openai_api_key="",
            azure_openai_endpoint="",
            azure_openai_api_key="",
            _env_file=None,  # type: ignore[call-arg]
        )
        assert s.any_keys_present is False


class TestGetSettings:
    def test_get_settings_returns_settings_instance(self):
        from app.core.config import Settings, get_settings

        # Clear the lru_cache to get a fresh instance
        get_settings.cache_clear()
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_is_cached(self):
        from app.core.config import get_settings

        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
