"""Tests for export modules: pure helpers and format integration."""

import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO

from export_html import _esc, _format_question_html, create_html
from export_pdf import _safe, create_pdf
from export_docx import create_docx
from export_qti import create_canvas_qti


# ── _esc (HTML escaping) ────────────────────────────────────────

class TestEsc:

    def test_none_returns_empty(self):
        assert _esc(None) == ""

    def test_escapes_html_tags(self):
        assert "&lt;" in _esc("<tag>")
        assert "&gt;" in _esc("<tag>")


# ── _safe (PDF latin-1 safety) ──────────────────────────────────

class TestSafe:

    def test_none_returns_empty(self):
        assert _safe(None) == ""

    def test_curly_quotes_become_straight(self):
        result = _safe("\u201cHello\u201d")
        assert result == '"Hello"'

    def test_en_dash_becomes_hyphen(self):
        assert _safe("\u2013") == "-"


# ── _format_question_html ───────────────────────────────────────

class TestFormatQuestionHtml:

    def test_student_version_has_write_space(self, open_ended_q):
        html = _format_question_html(open_ended_q, num=1, show_answers=False)
        assert "write-space" in html
        assert "Example answer" not in html

    def test_teacher_version_has_example_answer(self, open_ended_q):
        html = _format_question_html(open_ended_q, num=1, show_answers=True)
        assert "Example answer" in html
        assert "write-space" not in html


# ── Integration: HTML export ────────────────────────────────────

class TestCreateHtml:

    def test_produces_valid_html_document(self, sample_questions_by_slide):
        buf = create_html("Overview text", sample_questions_by_slide, "Takeaway text")
        html = buf.getvalue().decode("utf-8")
        assert html.startswith("<!DOCTYPE html>")
        assert "Overview text" in html
        assert "Takeaway text" in html


# ── Integration: PDF export ─────────────────────────────────────

class TestCreatePdf:

    def test_produces_valid_pdf(self, sample_questions_by_slide):
        buf = create_pdf("Intro", sample_questions_by_slide, "Outro")
        data = buf.getvalue()
        assert data[:5] == b"%PDF-"


# ── Integration: DOCX export ────────────────────────────────────

class TestCreateDocx:

    def test_produces_valid_docx_zip(self, sample_questions_by_slide):
        buf = create_docx("Intro", sample_questions_by_slide, "Outro")
        with zipfile.ZipFile(buf) as zf:
            assert "[Content_Types].xml" in zf.namelist()


# ── Integration: QTI export ─────────────────────────────────────

class TestCreateCanvasQti:

    def test_produces_valid_qti_zip(self, sample_questions_by_slide):
        buf = create_canvas_qti(sample_questions_by_slide)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert "imsmanifest.xml" in names
            # Find and parse the assessment XML
            xml_files = [n for n in names if n.endswith(".xml") and n != "imsmanifest.xml"]
            assert len(xml_files) == 1
            assessment_xml = zf.read(xml_files[0]).decode("utf-8")
            ET.fromstring(assessment_xml)  # raises on invalid XML
