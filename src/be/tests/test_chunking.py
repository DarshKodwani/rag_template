"""Tests for chunking.py — no external dependencies required."""
from __future__ import annotations

import pytest
from app.rag.chunking import chunk_text, iter_chunks_with_offsets


class TestChunkText:
    def test_empty_string_returns_empty_list(self):
        assert chunk_text("") == []

    def test_short_text_returns_single_chunk(self):
        text = "Hello world."
        chunks = chunk_text(text, chunk_size=800, chunk_overlap=120)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_produces_multiple_chunks(self):
        text = ("word " * 300).strip()  # ~1 500 chars
        chunks = chunk_text(text, chunk_size=800, chunk_overlap=120)
        assert len(chunks) >= 2

    def test_chunk_size_respected(self):
        text = "A" * 2000
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        for chunk in chunks:
            # May be slightly over if no sentence boundary found, but within 2x
            assert len(chunk) <= 1000

    def test_overlap_means_content_repeats(self):
        text = ("sentence number one. " * 50)  # make sure there are sentence boundaries
        chunks = chunk_text(text, chunk_size=200, chunk_overlap=50)
        if len(chunks) >= 2:
            tail = chunks[0][-50:]
            head = chunks[1][:100]
            # There should be some common text (overlap)
            assert any(word in head for word in tail.split() if len(word) > 3)

    def test_no_infinite_loop_on_tiny_text(self):
        chunks = chunk_text("ab", chunk_size=10, chunk_overlap=5)
        assert len(chunks) == 1

    def test_chunk_overlap_larger_than_size_does_not_hang(self):
        # overlap >= size is an edge case; just ensure it terminates
        chunks = chunk_text("Hello world this is a test sentence.", chunk_size=10, chunk_overlap=15)
        assert isinstance(chunks, list)


class TestIterChunksWithOffsets:
    def test_offsets_cover_full_text(self):
        text = "Alpha beta gamma. Delta epsilon zeta theta iota kappa lambda."
        chunks = list(iter_chunks_with_offsets(text, chunk_size=30, chunk_overlap=5))
        # First chunk starts at 0
        assert chunks[0][1] == 0
        # Last chunk ends at or after end of text
        assert chunks[-1][2] >= len(text) - 1

    def test_text_reconstructable_without_overlap(self):
        text = "word " * 200
        offsets = list(iter_chunks_with_offsets(text, chunk_size=100, chunk_overlap=20))
        # Each chunk text should equal the slice of the original text
        for chunk_text_part, start, end in offsets:
            assert text[start:end] == chunk_text_part

    def test_empty_text_yields_nothing(self):
        result = list(iter_chunks_with_offsets(""))
        assert result == []
