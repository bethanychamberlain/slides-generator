"""HTML generation for study guides — self-contained with embedded CSS."""

from io import BytesIO
import html as html_mod

# ---------------------------------------------------------------------------
# Embedded stylesheet adapted from DIS Scholarly theme
# ---------------------------------------------------------------------------
GUIDE_CSS = """\
@import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&family=Source+Sans+3:wght@300;400;600;700&display=swap');

:root {
  --dis-teal: #008ab0;
  --dis-cyan: #5dbee6;
  --fill-bg: #f0f7fa;
  --text-primary: #2d2d2d;
  --text-secondary: #5a5a5a;
  --green: #1a7a2e;
}

*, *::before, *::after { box-sizing: border-box; }

body {
  font-family: 'Source Sans 3', 'Source Sans Pro', -apple-system, sans-serif;
  font-size: 11pt;
  line-height: 1.55;
  color: var(--text-primary);
  max-width: 800px;
  margin: 0 auto;
  padding: 32px 24px 48px;
  background: #fff;
}

/* Header */
.guide-header {
  border-bottom: 3px solid var(--dis-teal);
  padding-bottom: 12px;
  margin-bottom: 20px;
}
.guide-header h1 {
  font-family: 'Merriweather', Georgia, serif;
  font-size: 1.5em;
  font-weight: 700;
  color: var(--dis-teal);
  margin: 0 0 4px;
}
.guide-header .subtitle {
  font-size: 0.95em;
  color: var(--text-secondary);
}

/* Student info fill-in fields */
.student-info {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
}
.student-info .field {
  flex: 1;
  border-bottom: 1px solid #999;
  padding: 4px 0;
  font-size: 0.95em;
  color: var(--text-secondary);
}

/* Summaries */
.summary {
  background: var(--fill-bg);
  border-left: 4px solid var(--dis-teal);
  padding: 10px 16px;
  margin-bottom: 18px;
  font-size: 0.95em;
}
.summary strong {
  color: var(--dis-teal);
}

/* Questions */
.question-block {
  border-left: 3px solid var(--dis-cyan);
  padding: 8px 0 8px 16px;
  margin-bottom: 14px;
  page-break-inside: avoid;
}
.question-block .q-number {
  font-weight: 700;
  color: var(--dis-teal);
}
.question-block .q-type {
  display: inline-block;
  font-size: 0.8em;
  font-weight: 600;
  color: var(--dis-teal);
  background: var(--fill-bg);
  padding: 1px 8px;
  border-radius: 3px;
  margin-left: 6px;
  vertical-align: middle;
}
.question-block .q-text {
  margin: 4px 0 6px;
}

/* Write space for students */
.write-space {
  border: 1px dashed #bbb;
  background: var(--fill-bg);
  min-height: 48px;
  margin: 6px 0 2px;
  border-radius: 3px;
}
.write-space.tall { min-height: 80px; }

/* Answer line */
.answer-line {
  border-bottom: 1px solid #ccc;
  padding: 2px 0;
  min-width: 200px;
  display: inline-block;
  margin: 4px 0;
}

/* Teacher answers */
.answer-text {
  color: var(--green);
  font-weight: 600;
}
.answer-label {
  color: var(--green);
  font-weight: 700;
  font-size: 0.9em;
}

/* Options (MC, T/F) */
.options-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  margin: 6px 0;
}
.option {
  padding: 2px 0;
}
.option.correct {
  color: var(--green);
  font-weight: 700;
}

/* Ordering */
.order-items {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 6px 0;
}
.order-item {
  background: var(--fill-bg);
  border: 1px solid #ccc;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 0.9em;
}

/* Print styles */
@media print {
  body { padding: 0; margin: 0 auto; font-size: 10pt; }
  .question-block { page-break-inside: avoid; }
  .write-space { min-height: 64px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .write-space.tall { min-height: 100px; }
  .summary { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .guide-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""

# ---------------------------------------------------------------------------
# Question type labels
# ---------------------------------------------------------------------------
_TYPE_LABELS = {
    "open_ended": "Open-ended",
    "short_answer": "Short Answer",
    "fill_in_blank": "Fill in Blank",
    "true_false": "True / False",
    "multiple_choice": "Multiple Choice",
    "put_in_order": "Put in Order",
}


def _esc(text):
    """HTML-escape a string, handling None gracefully."""
    if not text:
        return ""
    return html_mod.escape(str(text))


# ---------------------------------------------------------------------------
# Per-question HTML renderer
# ---------------------------------------------------------------------------

def _format_question_html(q, num, show_answers):
    """Render a single question as an HTML block."""
    qtype = q.get("type", "open_ended")
    label = _TYPE_LABELS.get(qtype, qtype)
    parts = [f'<div class="question-block">']
    parts.append(f'<span class="q-number">Question {num}.</span>')
    parts.append(f'<span class="q-type">{_esc(label)}</span>')

    if qtype == "open_ended":
        parts.append(f'<div class="q-text">{_esc(q.get("question", ""))}</div>')
        if show_answers:
            example = q.get("example_answer", "")
            if example:
                parts.append(f'<div><span class="answer-label">Example answer: </span>'
                             f'<span class="answer-text">{_esc(example)}</span></div>')
            else:
                parts.append('<div class="answer-text" style="font-style:italic;">[Open-ended response]</div>')
        else:
            parts.append('<div class="write-space tall"></div>')

    elif qtype == "short_answer":
        parts.append(f'<div class="q-text">{_esc(q.get("prompt", ""))}</div>')
        if show_answers:
            parts.append(f'<div><span class="answer-label">Answer: </span>'
                         f'<span class="answer-text">{_esc(q.get("answer", ""))}</span></div>')
        else:
            parts.append('<div class="answer-line">&nbsp;</div>')

    elif qtype == "fill_in_blank":
        sentence = q.get("sentence", "")
        answer = q.get("answer", "")
        if show_answers:
            display = _esc(sentence).replace("_____", f'<span class="answer-text">[{_esc(answer)}]</span>')
            parts.append(f'<div class="q-text">{display}</div>')
            parts.append(f'<div><span class="answer-label">Answer: </span>'
                         f'<span class="answer-text">{_esc(answer)}</span></div>')
        else:
            display = _esc(sentence).replace("_____", '<span class="answer-line">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>')
            parts.append(f'<div class="q-text">{display}</div>')

    elif qtype == "true_false":
        parts.append(f'<div class="q-text">{_esc(q.get("statement", ""))}</div>')
        answer = q.get("answer", True)
        parts.append('<div class="options-row">')
        if show_answers:
            t_cls = ' class="option correct"' if answer else ' class="option"'
            f_cls = ' class="option correct"' if not answer else ' class="option"'
            t_marker = "&#9679;" if answer else "&#9675;"
            f_marker = "&#9679;" if not answer else "&#9675;"
            parts.append(f'<span{t_cls}>{t_marker} True</span>')
            parts.append(f'<span{f_cls}>{f_marker} False</span>')
        else:
            parts.append('<span class="option">&#9675; True</span>')
            parts.append('<span class="option">&#9675; False</span>')
        parts.append('</div>')

    elif qtype == "multiple_choice":
        parts.append(f'<div class="q-text">{_esc(q.get("question", ""))}</div>')
        options = q.get("options", [])
        correct = q.get("answer", "")
        parts.append('<div class="options-row">')
        for opt in options:
            is_correct = opt.startswith(correct) if correct else False
            if show_answers and is_correct:
                parts.append(f'<span class="option correct">{_esc(opt)}</span>')
            else:
                parts.append(f'<span class="option">{_esc(opt)}</span>')
        parts.append('</div>')
        if show_answers:
            parts.append(f'<div><span class="answer-label">Answer: </span>'
                         f'<span class="answer-text">{_esc(correct)}</span></div>')

    elif qtype == "put_in_order":
        instruction = q.get("instruction", "Arrange in order:")
        items = q.get("items", [])
        parts.append(f'<div class="q-text">{_esc(instruction)}</div>')
        parts.append('<div class="order-items">')
        for item in items:
            parts.append(f'<span class="order-item">{_esc(item)}</span>')
        parts.append('</div>')
        if show_answers:
            correct_order = q.get("correct_order", [])
            if correct_order and items:
                ordered = [items[oi] for oi in correct_order if oi < len(items)]
                correct_text = " &#8594; ".join(_esc(o) for o in ordered)
            else:
                correct_text = ", ".join(_esc(o) for o in items)
            parts.append(f'<div><span class="answer-label">Correct order: </span>'
                         f'<span class="answer-text">{correct_text}</span></div>')
        else:
            parts.append('<div>Order: <span class="answer-line" style="min-width:300px;">&nbsp;</span></div>')

    else:
        parts.append(f'<div class="q-text">{_esc(str(q))}</div>')

    parts.append('</div>')
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def create_html(intro_summary, questions_by_slide, outro_summary, show_answers=False):
    """Generate a self-contained HTML study guide. Returns a BytesIO buffer."""
    guide_type = "Teacher Answer Key" if show_answers else "Student Note-Taking Guide"

    body_parts = []

    # Header
    body_parts.append('<div class="guide-header">')
    body_parts.append(f'  <h1>{_esc(guide_type)}</h1>')
    body_parts.append('</div>')

    # Student info fields (student version only)
    if not show_answers:
        body_parts.append('<div class="student-info">')
        body_parts.append('  <div class="field">Name:</div>')
        body_parts.append('  <div class="field">Date:</div>')
        body_parts.append('</div>')

    # Intro summary
    if intro_summary:
        body_parts.append('<div class="summary">')
        body_parts.append(f'  <strong>Overview:</strong> {_esc(intro_summary)}')
        body_parts.append('</div>')

    # Questions
    question_num = 1
    for slide_num in sorted(questions_by_slide.keys()):
        questions = questions_by_slide[slide_num]
        for q in questions:
            body_parts.append(_format_question_html(q, question_num, show_answers))
            question_num += 1

    # Outro summary
    if outro_summary:
        body_parts.append('<div class="summary">')
        body_parts.append(f'  <strong>Key Takeaways:</strong> {_esc(outro_summary)}')
        body_parts.append('</div>')

    body_html = '\n'.join(body_parts)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(guide_type)}</title>
  <style>
{GUIDE_CSS}
  </style>
</head>
<body>
{body_html}
</body>
</html>
"""

    buffer = BytesIO()
    buffer.write(full_html.encode("utf-8"))
    buffer.seek(0)
    return buffer
