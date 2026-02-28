"""Question types, formatting, CSV persistence, and text extraction."""

import csv
import json
import os
from datetime import datetime
from pathlib import Path

# Questions history CSV for future retrieval
_DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent))
QUESTIONS_CSV_PATH = _DATA_DIR / "questions_history.csv"

CSV_COLUMNS = [
    "timestamp", "source_file", "slide_num", "question_type", "question_text",
    "answer", "example_answer", "options", "items", "correct_order", "selected"
]

QUESTION_TYPES = [
    "open_ended", "short_answer", "fill_in_blank",
    "true_false", "multiple_choice", "put_in_order"
]

QUESTION_TYPE_LABELS = {
    "open_ended": "Open-ended",
    "short_answer": "Short Answer",
    "fill_in_blank": "Fill in blank",
    "true_false": "True/False",
    "multiple_choice": "Multiple Choice",
    "put_in_order": "Put in order"
}


def get_question_text(q):
    """Extract the main display text from a question dict, regardless of type."""
    qtype = q.get("type", "unknown")
    if qtype == "open_ended":
        return q.get("question", "")
    elif qtype == "short_answer":
        return q.get("prompt", "")
    elif qtype == "fill_in_blank":
        return q.get("sentence", "")
    elif qtype == "true_false":
        return q.get("statement", "")
    elif qtype == "multiple_choice":
        return q.get("question", "")
    elif qtype == "put_in_order":
        return q.get("instruction", "")
    else:
        return str(q)


def format_question_display(q):
    """Format a structured question for display in the UI."""
    qtype = q.get("type", "open_ended")
    badge = f"[{QUESTION_TYPE_LABELS.get(qtype, qtype)}]"

    if qtype == "open_ended":
        return f"{badge} {q.get('question', '')}\n{q.get('notes_prompt', '[Your notes:]')}"

    elif qtype == "short_answer":
        return f"{badge} {q.get('prompt', '')}\n*Answer: {q.get('answer', '')}*"

    elif qtype == "fill_in_blank":
        return f"{badge} {q.get('sentence', '')}\n*Answer: {q.get('answer', '')}*"

    elif qtype == "true_false":
        answer = "True" if q.get("answer", False) else "False"
        return f"{badge} {q.get('statement', '')}\n○ True  ○ False\n*Answer: {answer}*"

    elif qtype == "multiple_choice":
        options = q.get("options", [])
        options_str = "  ".join(options)
        return f"{badge} {q.get('question', '')}\n{options_str}\n*Answer: {q.get('answer', '')}*"

    elif qtype == "put_in_order":
        items = q.get("items", [])
        items_str = " → ".join([f"[ {item} ]" for item in items])
        correct = q.get("correct_order", [])
        if correct and items:
            ordered = [items[i] for i in correct if i < len(items)]
            correct_str = " → ".join(ordered)
        else:
            correct_str = "N/A"
        return f"{badge} {q.get('instruction', 'Arrange in order:')}\n{items_str}\n*Correct order: {correct_str}*"

    return f"{badge} {str(q)}"


def save_questions_to_csv(questions_by_slide, source_filename, selected_set=None):
    """Save all generated questions to CSV for future retrieval."""
    file_exists = QUESTIONS_CSV_PATH.exists()
    timestamp = datetime.now().isoformat()

    with open(QUESTIONS_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()

        for slide_num, questions in questions_by_slide.items():
            for i, q in enumerate(questions):
                qtype = q.get("type", "unknown")
                text = get_question_text(q)

                # Get answer based on type
                answer = ""
                if qtype in ["short_answer", "fill_in_blank"]:
                    answer = q.get("answer", "")
                elif qtype == "true_false":
                    answer = str(q.get("answer", ""))
                elif qtype == "multiple_choice":
                    answer = q.get("answer", "")

                is_selected = selected_set is None or (slide_num, i) in selected_set

                row = {
                    "timestamp": timestamp,
                    "source_file": source_filename,
                    "slide_num": slide_num,
                    "question_type": qtype,
                    "question_text": text,
                    "answer": answer,
                    "example_answer": q.get("example_answer", ""),
                    "options": json.dumps(q.get("options", [])) if q.get("options") else "",
                    "items": json.dumps(q.get("items", [])) if q.get("items") else "",
                    "correct_order": json.dumps(q.get("correct_order", [])) if q.get("correct_order") else "",
                    "selected": "1" if is_selected else "0"
                }
                writer.writerow(row)


def load_questions_from_csv(source_filename=None):
    """Load questions from CSV, optionally filtered by source file."""
    if not QUESTIONS_CSV_PATH.exists():
        return []

    questions = []
    with open(QUESTIONS_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if source_filename and row["source_file"] != source_filename:
                continue
            questions.append(row)

    return questions
