"""DOCX loader — extracts text with heading/section metadata."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

_HEADING_STYLES = {"Heading 1", "Heading 2", "Heading 3", "Heading 4"}


def load_docx(path: Path) -> tuple[str, list[dict]]:
    """
    Return (full_text, para_map).

    para_map entries:
      {'section': str|None, 'para_index': int, 'start_offset': int, 'end_offset': int}
    """
    try:
        import docx
    except ImportError:
        log.error("python-docx not installed; cannot load DOCX files. pip install python-docx")
        return "", []

    try:
        doc = docx.Document(str(path))
    except Exception as exc:
        log.error("Failed to open DOCX %s: %s", path, exc)
        return "", []

    parts: list[str] = []
    para_map: list[dict] = []
    offset = 0
    current_section: str | None = None

    for para_index, para in enumerate(doc.paragraphs):
        text = para.text
        if not text:
            continue

        # Detect headings to track section
        if para.style and para.style.name in _HEADING_STYLES:
            current_section = text.strip()

        if not text.endswith("\n"):
            text += "\n"

        start = offset
        end = offset + len(text)
        para_map.append(
            {
                "section": current_section,
                "para_index": para_index,
                "start_offset": start,
                "end_offset": end,
            }
        )
        parts.append(text)
        offset = end

    return "".join(parts), para_map
