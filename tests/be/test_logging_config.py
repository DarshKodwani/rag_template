"""Tests for core/logging.py."""
from __future__ import annotations

import logging

from app.core.logging import configure_logging


class TestConfigureLogging:
    def _reset_logging(self):
        """Remove all root handlers so basicConfig can reconfigure."""
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    def test_sets_root_level_to_info(self):
        self._reset_logging()
        configure_logging("INFO")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_sets_root_level_to_debug(self):
        self._reset_logging()
        configure_logging("DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_quiets_noisy_loggers(self):
        self._reset_logging()
        configure_logging("INFO")
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING
        assert logging.getLogger("qdrant_client").level == logging.WARNING

    def test_invalid_level_defaults_to_info(self):
        self._reset_logging()
        configure_logging("BADLEVEL")
        root = logging.getLogger()
        assert root.level == logging.INFO
