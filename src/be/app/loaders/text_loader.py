"""Plain-text loader."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def load_text(path: Path) -> tuple[str, list[dict]]:
    """
    Return (full_text, para_map).

    For plain text we produce a single metadata entry covering the whole file.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        log.error("Failed to read text file %s: %s", path, exc)
        return "", []

    return text, [{"start_offset": 0, "end_offset": len(text)}]
