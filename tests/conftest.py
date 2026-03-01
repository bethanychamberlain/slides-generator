"""Shared fixtures for the Slide Guide Generator test suite."""

import sys
from pathlib import Path

# Allow bare imports (e.g. `import ai`) the same way src/ code does.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest


# ── Question fixtures (one per type) ──────────────────────────────

@pytest.fixture
def open_ended_q():
    return {
        "type": "open_ended",
        "question": "What is the main purpose of photosynthesis?",
        "notes_prompt": "Write your thoughts here:",
        "example_answer": "To convert light energy into chemical energy.",
    }


@pytest.fixture
def short_answer_q():
    return {
        "type": "short_answer",
        "prompt": "Name the organelle responsible for photosynthesis.",
        "answer": "Chloroplast",
    }


@pytest.fixture
def fill_in_blank_q():
    return {
        "type": "fill_in_blank",
        "sentence": "The process of _____ converts CO2 into glucose.",
        "answer": "photosynthesis",
    }


@pytest.fixture
def true_false_q():
    return {
        "type": "true_false",
        "statement": "Mitochondria are the powerhouse of the cell.",
        "answer": True,
    }


@pytest.fixture
def multiple_choice_q():
    return {
        "type": "multiple_choice",
        "question": "Which gas do plants absorb?",
        "options": ["A) Oxygen", "B) Carbon dioxide", "C) Nitrogen", "D) Helium"],
        "answer": "B",
    }


@pytest.fixture
def put_in_order_q():
    return {
        "type": "put_in_order",
        "instruction": "Order the stages of mitosis:",
        "items": ["Prophase", "Metaphase", "Anaphase", "Telophase"],
        "correct_order": [0, 1, 2, 3],
    }


@pytest.fixture
def all_question_types(
    open_ended_q, short_answer_q, fill_in_blank_q,
    true_false_q, multiple_choice_q, put_in_order_q,
):
    return [
        open_ended_q, short_answer_q, fill_in_blank_q,
        true_false_q, multiple_choice_q, put_in_order_q,
    ]


@pytest.fixture
def sample_questions_by_slide(open_ended_q, true_false_q, multiple_choice_q):
    """Non-sequential slide numbers to mimic real data."""
    return {
        3: [open_ended_q, true_false_q],
        5: [multiple_choice_q],
    }
