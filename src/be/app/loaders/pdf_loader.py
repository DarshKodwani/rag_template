"""PDF loader — extracts text with page numbers."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def load_pdf(path: Path) -> tuple[str, list[dict]]:
    """
    Return (full_text, page_map).

    page_map is a list of dicts:
      {'page': int, 'start_offset': int, 'end_offset': int}
    """
    try:
        import pypdf
    except ImportError:
        log.error("pypdf not installed; cannot load PDF files. pip install pypdf")
        return "", []

    full_text_parts: list[str] = []
    page_map: list[dict] = []
    offset = 0

    try:
        reader = pypdf.PdfReader(str(path))
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text and not text.endswith("\n"):
                text += "\n"
            start = offset
            end = offset + len(text)
            page_map.append({"page": page_num, "start_offset": start, "end_offset": end})
            full_text_parts.append(text)
            offset = end
    except Exception as exc:
        log.error("Failed to read PDF %s: %s", path, exc)
        return "", []

    return "".join(full_text_parts), page_map
