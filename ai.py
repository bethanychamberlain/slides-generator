"""All Claude API calls and prompt logic."""

import json
import base64
from io import BytesIO

import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv

from questions import get_question_text

# Load environment variables from .env file
load_dotenv(override=True)

# Module-level client — initialized via set_api_key() or from env
client = None


def set_api_key(api_key):
    """Set the API key and create the client. Called from the UI login screen."""
    global client
    client = Anthropic(api_key=api_key)


def _ensure_client():
    """Ensure client is initialized, falling back to env var."""
    global client
    if client is None:
        client = Anthropic()
    return client

# Model configuration
MODEL_FAST = "claude-sonnet-4-6"
MODEL_ADVANCED = "claude-opus-4-6"


def image_to_base64(image):
    """Convert PIL image to base64 string."""
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def parse_json_response(text):
    """Parse a JSON response from Claude, handling markdown fences and common issues.

    Returns parsed dict/list, or None on failure.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def analyze_slide_intro(base64_image):
    """Analyze an introductory slide and return a summary string."""
    response = _ensure_client().messages.create(
        model=MODEL_FAST,
        max_tokens=1000,
        system="You are an expert at analyzing lecture slides and extracting key information concisely.",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image}},
                {"type": "text", "text": "Analyze this introductory slide and write a 1-2 sentence overview. "
                 "Include the topic/title and main learning objectives. "
                 "Write in plain text only - no markdown, no bullets, no special formatting. "
                 "Be concise and direct."}
            ]
        }]
    )
    return response.content[0].text


def analyze_slide_outro(base64_image):
    """Analyze a concluding slide and return a summary string."""
    response = _ensure_client().messages.create(
        model=MODEL_FAST,
        max_tokens=1000,
        system="You are an expert at analyzing lecture slides and extracting key information concisely.",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image}},
                {"type": "text", "text": "Analyze this concluding slide and write a 1-2 sentence summary of the key takeaways. "
                 "Write in plain text only - no markdown, no bullets, no special formatting. "
                 "Be concise and direct."}
            ]
        }]
    )
    return response.content[0].text


def analyze_slide_content(base64_image, custom_instructions=""):
    """Analyze a content slide and return structured questions as a dict."""
    prompt = """Analyze this lecture slide carefully, including any charts, graphs, or diagrams.

Generate exactly 3 questions for a student note-taking guide:
1. One OPEN-ENDED question (REQUIRED) - encouraging critical thinking about the content
2. Two additional questions - choose from the types below

PRIORITY ORDER (use higher priority types when appropriate for the content):
1. OPEN_ENDED (already required) - Critical thinking, synthesis, analysis questions
2. SHORT_ANSWER - For acronyms, definitions, key terms (e.g., "What does PAMP stand for?")
3. FILL_IN_BLANK - Key terms in context (e.g., "The _____ is the powerhouse of the cell")
4. TRUE_FALSE - Correct common misconceptions or verify understanding of facts
5. MULTIPLE_CHOICE - ONLY when there are meaningfully different conceptual alternatives (NOT for acronyms or simple definitions)
6. PUT_IN_ORDER - Processes, sequences, or steps

IMPORTANT RULES:
- NEVER use multiple choice for acronyms - use short_answer instead
- NEVER use multiple choice for simple definitions - use short_answer or fill_in_blank
- Prefer short_answer and fill_in_blank over multiple_choice when possible

Return ONLY valid JSON in this exact format (no other text):
{
  "questions": [
    {
      "type": "open_ended",
      "question": "Your open-ended question here?",
      "example_answer": "A model answer showing what a good response would include (2-3 sentences)",
      "notes_prompt": "[Your notes:]"
    },
    {
      "type": "short_answer",
      "prompt": "What does PAMP stand for?",
      "answer": "Pathogen-Associated Molecular Patterns"
    },
    {
      "type": "fill_in_blank",
      "sentence": "The _____ is responsible for energy production.",
      "answer": "mitochondria"
    }
  ]
}

Other valid question formats:
- true_false: {"type": "true_false", "statement": "...", "answer": true}
- multiple_choice: {"type": "multiple_choice", "question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "B"}
- put_in_order: {"type": "put_in_order", "instruction": "Arrange these steps in order:", "items": ["Step A", "Step B", "Step C"], "correct_order": [2, 0, 1]}

IMPORTANT: For open_ended questions, always include an "example_answer" field with a model answer based on the slide content."""

    if custom_instructions:
        prompt += f"\n\nAdditional context from instructor: {custom_instructions}"

    response = _ensure_client().messages.create(
        model=MODEL_FAST,
        max_tokens=2500,
        system="You are an expert educator creating study guide questions from lecture slides. "
               "Generate questions that promote active learning and deep engagement with the material.",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image}},
                {"type": "text", "text": prompt}
            ]
        }]
    )

    result = parse_json_response(response.content[0].text)
    if result is None:
        return {"questions": [{"type": "open_ended", "question": response.content[0].text.strip(), "notes_prompt": "[Your notes:]"}]}
    return result


def generate_example_answers(questions_by_slide, get_base64_for_slide):
    """Generate example answers for open-ended questions that don't have them.

    Args:
        questions_by_slide: Dict of {slide_num: [questions]}
        get_base64_for_slide: Callable(slide_num) -> base64_image_string or None
    """
    updated_questions = {}

    for slide_num, questions in questions_by_slide.items():
        updated_qs = []
        needs_generation = []

        for i, q in enumerate(questions):
            if q.get("type") == "open_ended" and not q.get("example_answer"):
                needs_generation.append((i, q))
            updated_qs.append(q.copy())

        if needs_generation:
            base64_image = get_base64_for_slide(slide_num)
            if base64_image:
                for idx, q in needs_generation:
                    prompt = f"""Look at this slide and provide a model answer (2-3 sentences) for this open-ended question:

Question: {q.get('question', '')}

Write a clear, concise example answer that a student might give based on the slide content.
Return ONLY the answer text, no additional formatting or explanation."""

                    try:
                        response = _ensure_client().messages.create(
                            model=MODEL_FAST,
                            max_tokens=500,
                            system="You are an expert educator providing model answers for study guide questions.",
                            messages=[{
                                "role": "user",
                                "content": [
                                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image}},
                                    {"type": "text", "text": prompt}
                                ]
                            }]
                        )
                        updated_qs[idx]["example_answer"] = response.content[0].text.strip()
                    except Exception:
                        updated_qs[idx]["example_answer"] = "[Example answer not available]"

        updated_questions[slide_num] = updated_qs

    return updated_questions


def review_and_select_questions(all_questions, total_slides):
    """Use Opus to review all questions and select the best ones for a 2-page guide.

    Returns a set of (slide_num, question_index) tuples that are selected.
    """
    questions_summary = []
    for slide_num, qs in all_questions.items():
        for i, q in enumerate(qs):
            questions_summary.append({
                "slide": slide_num,
                "index": i,
                "type": q.get("type", "unknown"),
                "text": get_question_text(q)
            })

    prompt = f"""There are {total_slides} slides total. Not every slide needs a question - select the BEST questions that:
1. Cover the most important concepts
2. Have good variety (mix of question types)
3. Are clear and well-written
4. Would help students engage with the material

IMPORTANT REQUIREMENTS:
1. 50-75% of selected questions should be "open_ended" or "short_answer" types (deeper engagement)
2. At least 25% should be OTHER types (fill_in_blank, true_false, multiple_choice, put_in_order) for variety

Question type priority for selection:
1. open_ended (highest priority - always good to include)
2. short_answer (high priority - tests recall of key terms/definitions)
3. fill_in_blank (medium priority)
4. true_false (medium priority)
5. multiple_choice (lower priority - only if conceptually meaningful)
6. put_in_order (use when appropriate for processes/sequences)

Here are all the generated questions:
{json.dumps(questions_summary, indent=2)}

Select approximately 15-20 questions total (enough for ~2 pages).
Remember: At least 50% must be open_ended or short_answer!

Return ONLY valid JSON listing which questions to INCLUDE:
{{
  "selected": [
    {{"slide": 4, "index": 0}},
    {{"slide": 4, "index": 2}},
    {{"slide": 5, "index": 1}}
  ]
}}"""

    response = _ensure_client().messages.create(
        model=MODEL_ADVANCED,
        max_tokens=2000,
        system="You are reviewing questions for a student note-taking guide. "
               "The guide should be approximately 2 pages (maximum 3 pages). "
               "Select the best mix of questions for effective learning.",
        messages=[{
            "role": "user",
            "content": prompt
        }]
    )

    result = parse_json_response(response.content[0].text)
    if result is not None:
        selected = result.get("selected", [])
        return {(s["slide"], s["index"]) for s in selected}

    # Fallback: select first question from each slide (reasonable default)
    return {(slide, 0) for slide in all_questions}


def regenerate_questions(base64_image, slide_num, selected_types, use_advanced_model=False, custom_instructions=""):
    """Regenerate questions for a slide using only the selected question types."""
    model = MODEL_ADVANCED if use_advanced_model else MODEL_FAST

    type_instructions = []
    for qtype in selected_types:
        if qtype == "open_ended":
            type_instructions.append("- OPEN_ENDED: A thought-provoking question encouraging critical thinking")
        elif qtype == "short_answer":
            type_instructions.append("- SHORT_ANSWER: For acronyms, definitions, or terms (student writes brief answer)")
        elif qtype == "fill_in_blank":
            type_instructions.append("- FILL_IN_BLANK: A sentence with a key term blanked out with _____")
        elif qtype == "true_false":
            type_instructions.append("- TRUE_FALSE: A statement that is clearly true or false")
        elif qtype == "multiple_choice":
            type_instructions.append("- MULTIPLE_CHOICE: A question with 4 options (A-D), one correct")
        elif qtype == "put_in_order":
            type_instructions.append("- PUT_IN_ORDER: 3-5 items to arrange in correct sequence")

    types_str = "\n".join(type_instructions)
    num_questions = len(selected_types)

    prompt = f"""Analyze this lecture slide and generate exactly {num_questions} question(s) using ONLY these types:
{types_str}

Return ONLY valid JSON:
{{
  "questions": [
    // For open_ended (MUST include example_answer):
    {{"type": "open_ended", "question": "...", "example_answer": "A model answer (2-3 sentences)", "notes_prompt": "[Your notes:]"}},
    // For short_answer (for acronyms, definitions):
    {{"type": "short_answer", "prompt": "What does XYZ stand for?", "answer": "The full meaning"}},
    // For fill_in_blank:
    {{"type": "fill_in_blank", "sentence": "The _____ is...", "answer": "term"}},
    // For true_false:
    {{"type": "true_false", "statement": "...", "answer": true}},
    // For multiple_choice:
    {{"type": "multiple_choice", "question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "B"}},
    // For put_in_order:
    {{"type": "put_in_order", "instruction": "Arrange in order:", "items": ["...", "..."], "correct_order": [1, 0]}}
  ]
}}

IMPORTANT: For open_ended questions, always include an "example_answer" field with a model answer."""

    if custom_instructions:
        prompt += f"\n\nAdditional context from instructor: {custom_instructions}"

    response = _ensure_client().messages.create(
        model=model,
        max_tokens=2500,
        system="You are an expert educator creating study guide questions from lecture slides.",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image}},
                {"type": "text", "text": prompt}
            ]
        }]
    )

    result = parse_json_response(response.content[0].text)
    if result is None:
        return {"questions": [{"type": "open_ended", "question": response.content[0].text.strip(), "notes_prompt": "[Your notes:]"}]}
    return result
