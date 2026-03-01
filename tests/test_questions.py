"""Tests for questions.py: text extraction and display formatting."""

import pytest
from questions import get_question_text, format_question_display


# ── get_question_text ────────────────────────────────────────────

class TestGetQuestionText:

    @pytest.mark.parametrize("fixture_name,expected_field", [
        ("open_ended_q", "question"),
        ("short_answer_q", "prompt"),
        ("fill_in_blank_q", "sentence"),
        ("true_false_q", "statement"),
        ("multiple_choice_q", "question"),
        ("put_in_order_q", "instruction"),
    ])
    def test_extracts_correct_field(self, fixture_name, expected_field, request):
        q = request.getfixturevalue(fixture_name)
        result = get_question_text(q)
        assert result == q[expected_field]


# ── format_question_display ──────────────────────────────────────

class TestFormatQuestionDisplay:

    def test_open_ended_has_badge_and_notes_prompt(self, open_ended_q):
        result = format_question_display(open_ended_q)
        assert "[Open-ended]" in result
        assert open_ended_q["notes_prompt"] in result

    def test_true_false_has_badge_and_radio_options(self, true_false_q):
        result = format_question_display(true_false_q)
        assert "[True/False]" in result
        assert "True" in result and "False" in result

    def test_put_in_order_has_badge_and_correct_order(self, put_in_order_q):
        result = format_question_display(put_in_order_q)
        assert "[Put in order]" in result
        assert "Prophase" in result
        # Correct order string should contain arrow separator
        assert "Correct order:" in result
