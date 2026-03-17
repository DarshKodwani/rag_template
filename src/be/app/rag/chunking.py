"""Text chunking utilities."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)

_COMPLEX_DOC_CHAR_THRESHOLD = 200_000
_UNEVEN_RATIO_THRESHOLD = 10.0  # max / min paragraph length ratio


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[str]:
    """
    Split *text* into overlapping windows of *chunk_size* characters.

    Splitting is sentence-aware: boundaries are placed at sentence endings
    ('. ', '! ', '? ') when possible so chunks don't cut mid-sentence.
    """
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        # Try to find a sentence boundary before the hard cut
        if end < length:
            for sep in (". ", "! ", "? ", "\n\n", "\n"):
                boundary = text.rfind(sep, start, end)
                if boundary != -1 and boundary > start:
                    end = boundary + len(sep)
                    break
        chunks.append(text[start:end])
        if end >= length:
            break  # reached end of text — no more chunks needed
        # Advance by at least (chunk_size - overlap) to avoid tiny duplicate chunks
        step = max(chunk_size - chunk_overlap, 1)
        next_start = start + step
        start = next_start

    return chunks


def iter_chunks_with_offsets(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> Iterator[tuple[str, int, int]]:
    """Yield (chunk_text, start_offset, end_offset) tuples."""
    if not text:
        return

    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            for sep in (". ", "! ", "? ", "\n\n", "\n"):
                boundary = text.rfind(sep, start, end)
                if boundary != -1 and boundary > start:
                    end = boundary + len(sep)
                    break
        yield text[start:end], start, end
        if end >= length:
            break  # reached end of text
        step = max(chunk_size - chunk_overlap, 1)
        next_start = start + step
        start = next_start


def check_complex_doc(
    doc_id: str,
    text: str,
    paragraphs: list[str],
    data_dir: Path,
) -> None:
    """
    Detect complex documents and write a suggestion artifact to data/index_runs/.

    Does NOT prompt the user — just logs and writes a JSON file.
    """
    import json

    issues: list[str] = []

    if len(text) > _COMPLEX_DOC_CHAR_THRESHOLD:
        issues.append(
            f"Document is very long ({len(text):,} chars > {_COMPLEX_DOC_CHAR_THRESHOLD:,}). "
            "Consider reducing CHUNK_SIZE or splitting the document."
        )

    non_empty = [p for p in paragraphs if p.strip()]
    if len(non_empty) >= 2:
        lengths = [len(p) for p in non_empty]
        ratio = max(lengths) / max(min(lengths), 1)
        if ratio > _UNEVEN_RATIO_THRESHOLD:
            issues.append(
                f"Highly uneven paragraph lengths (ratio {ratio:.1f}x). "
                "Consider heading-aware chunking."
            )

    if not issues:
        return

    for issue in issues:
        log.warning("[%s] %s", doc_id, issue)

    runs_dir = Path(data_dir) / "index_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    artifact = runs_dir / f"{doc_id}.json"
    artifact.write_text(
        json.dumps({"doc_id": doc_id, "suggestions": issues}, indent=2),
        encoding="utf-8",
    )
    log.info("Wrote chunking suggestion artifact to %s", artifact)
