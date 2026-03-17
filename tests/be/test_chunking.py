"""Tests for chunking.py — no external dependencies required."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from app.rag.chunking import chunk_text, iter_chunks_with_offsets, check_complex_doc


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


class TestCheckComplexDoc:
    def test_no_issues_does_nothing(self, tmp_path):
        """Short document with even paragraphs — no warnings."""
        text = "Short text."
        paragraphs = ["Short text."]
        check_complex_doc("doc1", text, paragraphs, tmp_path)
        runs_dir = tmp_path / "index_runs"
        assert not runs_dir.exists()

    def test_long_document_creates_artifact(self, tmp_path):
        text = "x" * 250_000
        paragraphs = [text]
        check_complex_doc("longdoc", text, paragraphs, tmp_path)
        artifact = tmp_path / "index_runs" / "longdoc.json"
        assert artifact.exists()
        data = json.loads(artifact.read_text())
        assert "very long" in data["suggestions"][0].lower()

    def test_uneven_paragraphs_creates_artifact(self, tmp_path):
        short = "Hi."
        long_para = "word " * 1000
        text = short + "\n" + long_para
        paragraphs = [short, long_para]
        check_complex_doc("uneven", text, paragraphs, tmp_path)
        artifact = tmp_path / "index_runs" / "uneven.json"
        assert artifact.exists()
        data = json.loads(artifact.read_text())
        assert any("uneven" in s.lower() for s in data["suggestions"])

    def test_single_paragraph_no_ratio_issue(self, tmp_path):
        text = "Only one paragraph here."
        paragraphs = ["Only one paragraph here."]
        check_complex_doc("single", text, paragraphs, tmp_path)
        runs_dir = tmp_path / "index_runs"
        assert not runs_dir.exists()
