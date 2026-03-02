"""PDF generation for study guides using fpdf2."""

from io import BytesIO
from fpdf import FPDF

# Common Unicode -> ASCII replacements for latin-1 safe output
_UNICODE_MAP = str.maketrans({
    "\u2013": "-",    # en dash
    "\u2014": "--",   # em dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u2022": "*",    # bullet
    "\u25cb": "( )",  # white circle
    "\u25cf": "(X)",  # black circle
    "\u2192": "->",   # right arrow
    "\u2190": "<-",   # left arrow
    "\u2264": "<=",   # less than or equal
    "\u2265": ">=",   # greater than or equal
    "\u00a0": " ",    # non-breaking space
})


def _safe(text):
    """Make text safe for fpdf2 core fonts (latin-1 only)."""
    if not text:
        return ""
    text = text.translate(_UNICODE_MAP)
    # Strip any remaining non-latin-1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _GuidePDF(FPDF):
    """Thin FPDF subclass with Times New Roman defaults and narrow margins."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=12)
        self.set_margins(left=13, top=13, right=13)
        self.add_page()
        self.set_font("Times", size=10)

    def normalize_text(self, text):
        """Sanitize Unicode before fpdf2 encodes to latin-1."""
        return super().normalize_text(_safe(text))

    # Helpers ---------------------------------------------------------------

    def _bold(self, text, size=10):
        self.set_font("Times", "B", size)
        self.write(4, text)
        self.set_font("Times", "", size)

    def _green(self, text, bold=False):
        self.set_text_color(0, 100, 0)
        style = "B" if bold else ""
        self.set_font("Times", style, 10)
        self.write(4, text)
        self.set_text_color(0, 0, 0)
        self.set_font("Times", "", 10)

    def _italic(self, text):
        self.set_font("Times", "I", 10)
        self.write(4, text)
        self.set_font("Times", "", 10)

    def _blank_line(self, w=120):
        self.ln(3)
        x = self.get_x() + 8
        y = self.get_y() + 2
        self.line(x, y, x + w, y)
        self.ln(5)

    def _spacer(self, h=4):
        self.ln(h)


def _format_question(pdf, q, num, show_answers):
    """Render one question into the PDF."""
    qtype = q.get("type", "open_ended")
    indent = 8  # mm from left margin

    if qtype == "open_ended":
        pdf._bold(f"Question {num}. ")
        pdf.write(4, q.get("question", ""))
        pdf.ln(5)
        if show_answers:
            pdf.set_x(pdf.l_margin + indent)
            example = q.get("example_answer", "")
            if example:
                pdf._green("Example answer: ", bold=True)
                pdf._green(example)
            else:
                pdf.set_text_color(0, 100, 0)
                pdf._italic("[Open-ended response]")
                pdf.set_text_color(0, 0, 0)
            pdf.ln(5)
        else:
            for _ in range(2):
                pdf.set_x(pdf.l_margin + indent)
                pdf._blank_line()
        pdf._spacer(3)

    elif qtype == "short_answer":
        pdf._bold(f"Question {num}. ")
        pdf.write(4, q.get("prompt", ""))
        pdf.ln(5)
        if show_answers:
            pdf.set_x(pdf.l_margin + indent)
            pdf._green(f"Answer: {q.get('answer', '')}", bold=True)
            pdf.ln(5)
        else:
            pdf.set_x(pdf.l_margin + indent)
            pdf._blank_line()
        pdf._spacer(3)

    elif qtype == "fill_in_blank":
        pdf._bold(f"Question {num}. ")
        answer = q.get("answer", "")
        if show_answers:
            sentence = q.get("sentence", "").replace("_____", f"[{answer}]")
            pdf.write(4, sentence)
            pdf.ln(5)
            pdf.set_x(pdf.l_margin + indent)
            pdf._green(f"Answer: {answer}", bold=True)
            pdf.ln(5)
        else:
            sentence = q.get("sentence", "").replace("_____", "__________________")
            pdf.write(4, sentence)
            pdf.ln(5)
        pdf._spacer(3)

    elif qtype == "true_false":
        pdf._bold(f"Question {num}. ")
        pdf.write(4, q.get("statement", ""))
        pdf.ln(5)
        answer = q.get("answer", True)
        pdf.set_x(pdf.l_margin + indent)
        if show_answers:
            if answer:
                pdf._green("(X) True", bold=True)
                pdf.write(4, "                    ")
                pdf.write(4, "( ) False")
            else:
                pdf.write(4, "( ) True                    ")
                pdf._green("(X) False", bold=True)
        else:
            pdf.write(4, "( )  True                    ( )  False")
        pdf.ln(5)
        pdf._spacer(3)

    elif qtype == "multiple_choice":
        pdf._bold(f"Question {num}. ")
        pdf.write(4, q.get("question", ""))
        pdf.ln(5)
        options = q.get("options", [])
        correct = q.get("answer", "")
        pdf.set_x(pdf.l_margin + indent)
        for i, opt in enumerate(options):
            is_correct = opt.startswith(correct) if correct else False
            if show_answers and is_correct:
                pdf._green(opt, bold=True)
            else:
                pdf.write(4, opt)
            if i < len(options) - 1:
                pdf.write(4, "    ")
        pdf.ln(5)
        if show_answers:
            pdf.set_x(pdf.l_margin + indent)
            pdf._green(f"Answer: {correct}", bold=True)
            pdf.ln(5)
        pdf._spacer(3)

    elif qtype == "put_in_order":
        instruction = q.get("instruction", "Arrange in order:")
        items = q.get("items", [])
        items_text = ", ".join(items)
        pdf._bold(f"Question {num}. ")
        pdf.write(4, f"{instruction} {items_text}")
        pdf.ln(5)
        if show_answers:
            correct_order = q.get("correct_order", [])
            if correct_order and items:
                ordered = [items[oi] for oi in correct_order if oi < len(items)]
                correct_text = " -> ".join(ordered)
            else:
                correct_text = ", ".join(items)
            pdf.set_x(pdf.l_margin + indent)
            pdf._green(f"Correct order: {correct_text}", bold=True)
            pdf.ln(5)
        else:
            pdf.set_x(pdf.l_margin + indent)
            pdf.write(4, "Order: " + "_" * 45)
            pdf.ln(5)
        pdf._spacer(3)

    else:
        pdf._bold(f"Question {num}. ")
        pdf.write(4, str(q))
        pdf.ln(5)
        pdf._spacer(3)


def create_pdf(intro_summary, questions_by_slide, outro_summary, show_answers=False):
    """Generate a compact PDF study guide. Returns a BytesIO buffer."""
    pdf = _GuidePDF()

    if intro_summary:
        pdf._bold("Overview: ")
        pdf.write(4, intro_summary)
        pdf._spacer(6)

    question_num = 1
    for slide_num, questions in questions_by_slide.items():
        for q in questions:
            _format_question(pdf, q, question_num, show_answers)
            question_num += 1

    if outro_summary:
        pdf._bold("Key Takeaways: ")
        pdf.write(4, outro_summary)
        pdf.ln(5)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer
