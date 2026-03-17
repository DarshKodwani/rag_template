"""Tests for citations.py."""
from __future__ import annotations

from app.rag.citations import payload_to_citation, payloads_to_citations
from app.core.models import Citation


class TestPayloadToCitation:
    def test_basic_fields(self):
        payload = {
            "doc_name": "report.pdf",
            "doc_rel_path": "documents/report.pdf",
            "page": 3,
            "section": None,
            "text": "Some relevant text here.",
        }
        cit = payload_to_citation(payload, chunk_id="abc123")
        assert cit.doc_name == "report.pdf"
        assert cit.doc_path == "documents/report.pdf"
        assert cit.page == 3
        assert cit.section is None
        assert cit.snippet == "Some relevant text here."
        assert cit.chunk_id == "abc123"

    def test_long_snippet_is_truncated(self):
        long_text = "x" * 400
        payload = {"doc_name": "a.txt", "doc_rel_path": "a.txt", "text": long_text}
        cit = payload_to_citation(payload, chunk_id="x")
        assert len(cit.snippet) <= 303  # 300 chars + "…"
        assert cit.snippet.endswith("…")

    def test_missing_fields_use_defaults(self):
        cit = payload_to_citation({}, chunk_id="z")
        assert cit.doc_name == ""
        assert cit.page is None
        assert cit.snippet == ""

    def test_section_preserved(self):
        payload = {"section": "Introduction", "doc_name": "a.pdf", "doc_rel_path": "a.pdf", "text": "hi"}
        cit = payload_to_citation(payload, chunk_id="1")
        assert cit.section == "Introduction"


class TestPayloadsToCitations:
    def test_empty_returns_empty_list(self):
        assert payloads_to_citations([]) == []

    def test_multiple_payloads(self):
        results = [
            ({"doc_name": f"doc{i}.pdf", "doc_rel_path": f"doc{i}.pdf", "text": f"text{i}"}, f"id{i}")
            for i in range(3)
        ]
        citations = payloads_to_citations(results)
        assert len(citations) == 3
        assert all(isinstance(c, Citation) for c in citations)
        assert [c.doc_name for c in citations] == ["doc0.pdf", "doc1.pdf", "doc2.pdf"]
