"""Tests for loaders (pdf_loader, docx_loader, text_loader)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# text_loader
# ---------------------------------------------------------------------------

class TestLoadText:
    def test_loads_simple_file(self, tmp_path):
        from app.loaders.text_loader import load_text

        f = tmp_path / "test.txt"
        f.write_text("Hello world", encoding="utf-8")

        text, meta = load_text(f)
        assert text == "Hello world"
        assert len(meta) == 1
        assert meta[0]["start_offset"] == 0
        assert meta[0]["end_offset"] == len("Hello world")

    def test_read_error_returns_empty(self, tmp_path):
        from app.loaders.text_loader import load_text

        fake_path = tmp_path / "nonexistent.txt"
        text, meta = load_text(fake_path)
        assert text == ""
        assert meta == []


# ---------------------------------------------------------------------------
# pdf_loader
# ---------------------------------------------------------------------------

class TestLoadPdf:
    def test_loads_pages(self, tmp_path):
        from app.loaders.pdf_loader import load_pdf

        fake_page1 = MagicMock()
        fake_page1.extract_text.return_value = "Page 1 content"
        fake_page2 = MagicMock()
        fake_page2.extract_text.return_value = "Page 2 content"

        fake_reader = MagicMock()
        fake_reader.pages = [fake_page1, fake_page2]

        with patch("pypdf.PdfReader", return_value=fake_reader):
            text, page_map = load_pdf(tmp_path / "test.pdf")

        assert "Page 1 content" in text
        assert "Page 2 content" in text
        assert len(page_map) == 2
        assert page_map[0]["page"] == 1
        assert page_map[1]["page"] == 2

    def test_empty_page_text(self, tmp_path):
        from app.loaders.pdf_loader import load_pdf

        fake_page = MagicMock()
        fake_page.extract_text.return_value = None

        fake_reader = MagicMock()
        fake_reader.pages = [fake_page]

        with patch("pypdf.PdfReader", return_value=fake_reader):
            text, page_map = load_pdf(tmp_path / "test.pdf")

        assert text == ""
        assert len(page_map) == 1

    def test_pypdf_import_error(self, tmp_path):
        """When pypdf is not installed, return empty."""
        import importlib
        import app.loaders.pdf_loader as pdf_mod

        saved = sys.modules.pop("pypdf", None)
        try:
            with patch.dict(sys.modules, {"pypdf": None}):
                importlib.reload(pdf_mod)
                text, meta = pdf_mod.load_pdf(tmp_path / "test.pdf")
            assert text == ""
            assert meta == []
        finally:
            if saved is not None:
                sys.modules["pypdf"] = saved
            importlib.reload(pdf_mod)

    def test_pdf_read_exception(self, tmp_path):
        from app.loaders.pdf_loader import load_pdf

        with patch("pypdf.PdfReader", side_effect=Exception("corrupt file")):
            text, meta = load_pdf(tmp_path / "bad.pdf")

        assert text == ""
        assert meta == []


# ---------------------------------------------------------------------------
# docx_loader
# ---------------------------------------------------------------------------

class TestLoadDocx:
    def test_loads_paragraphs(self, tmp_path):
        from app.loaders.docx_loader import load_docx

        para1 = MagicMock()
        para1.text = "Introduction"
        para1.style = MagicMock()
        para1.style.name = "Heading 1"

        para2 = MagicMock()
        para2.text = "Some body text here."
        para2.style = MagicMock()
        para2.style.name = "Normal"

        fake_doc = MagicMock()
        fake_doc.paragraphs = [para1, para2]

        with patch("docx.Document", return_value=fake_doc):
            text, para_map = load_docx(tmp_path / "test.docx")

        assert "Introduction" in text
        assert "Some body text here." in text
        assert len(para_map) == 2
        assert para_map[0]["section"] == "Introduction"  # heading sets current_section before appending
        assert para_map[1]["section"] == "Introduction"

    def test_empty_paragraphs_skipped(self, tmp_path):
        from app.loaders.docx_loader import load_docx

        para_empty = MagicMock()
        para_empty.text = ""
        para_empty.style = MagicMock()
        para_empty.style.name = "Normal"

        para_content = MagicMock()
        para_content.text = "Real content"
        para_content.style = MagicMock()
        para_content.style.name = "Normal"

        fake_doc = MagicMock()
        fake_doc.paragraphs = [para_empty, para_content]

        with patch("docx.Document", return_value=fake_doc):
            text, para_map = load_docx(tmp_path / "test.docx")

        assert len(para_map) == 1  # empty paragraph skipped
        assert "Real content" in text

    def test_docx_import_error(self, tmp_path):
        import importlib
        import app.loaders.docx_loader as docx_mod

        saved = sys.modules.pop("docx", None)
        try:
            with patch.dict(sys.modules, {"docx": None}):
                importlib.reload(docx_mod)
                text, meta = docx_mod.load_docx(tmp_path / "test.docx")
            assert text == ""
            assert meta == []
        finally:
            if saved is not None:
                sys.modules["docx"] = saved
            importlib.reload(docx_mod)

        assert text == ""
        assert meta == []

    def test_docx_open_exception(self, tmp_path):
        from app.loaders.docx_loader import load_docx

        with patch("docx.Document", side_effect=Exception("corrupt docx")):
            text, meta = load_docx(tmp_path / "test.docx")

        assert text == ""
        assert meta == []

    def test_text_already_ends_with_newline(self, tmp_path):
        from app.loaders.docx_loader import load_docx

        para = MagicMock()
        para.text = "Already has newline\n"
        para.style = MagicMock()
        para.style.name = "Normal"

        fake_doc = MagicMock()
        fake_doc.paragraphs = [para]

        with patch("docx.Document", return_value=fake_doc):
            text, para_map = load_docx(tmp_path / "test.docx")

        assert text == "Already has newline\n"

    def test_no_style_paragraph(self, tmp_path):
        from app.loaders.docx_loader import load_docx

        para = MagicMock()
        para.text = "No style"
        para.style = None

        fake_doc = MagicMock()
        fake_doc.paragraphs = [para]

        with patch("docx.Document", return_value=fake_doc):
            text, para_map = load_docx(tmp_path / "test.docx")

        assert "No style" in text
