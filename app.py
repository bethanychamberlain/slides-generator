import streamlit as st
import pypdfium2 as pdfium
try:
    from pdf2image import convert_from_bytes
    _HAS_PDF2IMAGE = True
except ImportError:
    _HAS_PDF2IMAGE = False
from PIL import Image
from pathlib import Path
import json
import shutil
import uuid

from cache import (
    get_file_hash, get_image_hash, get_cached_questions_for_image,
    save_questions_for_image, load_from_cache, save_to_cache, clear_cache,
)
from ai import (
    image_to_base64, analyze_slide_intro, analyze_slide_outro,
    analyze_slide_content, generate_example_answers,
    review_and_select_questions, regenerate_questions,
    set_provider, set_current_user,
)
from auth import require_login, logout
from export_docx import create_docx
from export_pdf import create_pdf
from export_html import create_html
from export_qti import create_canvas_qti
from questions import (
    QUESTION_TYPES, QUESTION_TYPE_LABELS, format_question_display,
    get_question_text, save_questions_to_csv, QUESTIONS_CSV_PATH,
)

# --- Constants ---
IMAGE_DPI = 300
THUMBNAIL_WIDTH = 200
SLIDES_PER_PAGE = 10
DEFAULT_INTRO_SLIDES = 3
DEFAULT_OUTRO_SLIDES = 3
MAX_FILE_SIZE_MB = 50

# Working directory for full-size images (parent; each session gets a subdirectory)
WORKING_IMAGES_BASE = Path(__file__).parent / "working_images"


def _session_working_dir():
    """Return the per-session working directory (created lazily)."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex[:12]
    return WORKING_IMAGES_BASE / st.session_state.session_id


def convert_pdf_to_images(file_bytes, dpi=IMAGE_DPI):
    """Convert PDF bytes to a list of PIL Images. Uses pypdfium2 (no system deps)."""
    pdf = pdfium.PdfDocument(file_bytes)
    images = []
    for i in range(len(pdf)):
        img = pdf[i].render(scale=dpi / 72).to_pil()
        if img.mode == "RGBA":
            img = img.convert("RGB")
        images.append(img)
    return images


def ensure_working_dir():
    """Create the per-session working images directory if it doesn't exist."""
    _session_working_dir().mkdir(parents=True, exist_ok=True)


def cleanup_working_dir():
    """Remove all images from the current session's working directory."""
    d = _session_working_dir()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)


def save_slide_image(image, slide_num):
    """Save a slide image to the session's working directory."""
    ensure_working_dir()
    filename = _session_working_dir() / f"slide_{slide_num:03d}.jpg"
    image.save(filename, format="JPEG", quality=95)
    return filename


def get_slide_image_path(slide_num):
    """Get the path to a saved slide image in the current session."""
    return _session_working_dir() / f"slide_{slide_num:03d}.jpg"


def load_slide_image(slide_num):
    """Load a slide image from disk. Returns PIL Image or None."""
    path = get_slide_image_path(slide_num)
    if path.exists():
        return Image.open(path)
    return None


def get_base64_for_slide(slide_num):
    """Load a slide from disk and return its base64 encoding, or None."""
    img = load_slide_image(slide_num)
    if img is None:
        return None
    return image_to_base64(img)


def toggle_slide_selection(slide_num, select_all):
    """Toggle all questions for a specific slide."""
    qs = st.session_state.questions.get(slide_num, [])
    for qi in range(len(qs)):
        st.session_state[f"slide_{slide_num}_q_{qi}"] = select_all
    st.session_state.user_modified_selection = True
    st.session_state.teacher_questions = None


def on_checkbox_change():
    """Callback when user manually changes a checkbox."""
    st.session_state.user_modified_selection = True
    st.session_state.teacher_questions = None


def toggle_all_selection(select_all):
    """Toggle all questions across all slides."""
    for sn in st.session_state.questions:
        for qi in range(len(st.session_state.questions[sn])):
            st.session_state[f"slide_{sn}_q_{qi}"] = select_all
    st.session_state.user_modified_selection = True
    st.session_state.teacher_questions = None


def clean_slide_question_keys(slide_num, old_count):
    """Remove stale session state keys when question count changes for a slide."""
    for qi in range(old_count):
        key = f"slide_{slide_num}_q_{qi}"
        if key in st.session_state:
            del st.session_state[key]


# --- STREAMLIT UI ---

st.set_page_config(page_title="Slide Guide Generator", layout="wide")
st.title("Slide Guide Generator")

# --- Authentication ---
user = require_login()
set_provider("anthropic")
set_current_user(user["email"])

# Show user info + logout in sidebar
with st.sidebar:
    st.write(f"Signed in as **{user['name']}**")
    st.caption(user["email"])
    if st.button("Sign out"):
        logout()

st.write("Upload a presentation PDF to generate a student note-taking guide.")

# Initialize session state
if "analyzed" not in st.session_state:
    st.session_state.analyzed = False
if "slides" not in st.session_state:
    st.session_state.slides = []
if "questions" not in st.session_state:
    st.session_state.questions = {}
if "include_intro" not in st.session_state:
    st.session_state.include_intro = True
if "include_outro" not in st.session_state:
    st.session_state.include_outro = True
if "current_page" not in st.session_state:
    st.session_state.current_page = 0
if "custom_instructions" not in st.session_state:
    st.session_state.custom_instructions = ""

# File upload
uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file and not st.session_state.analyzed:
    # File size validation
    file_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    file_size_mb = len(file_bytes) / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        st.error(f"File is too large ({file_size_mb:.1f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB.")
    else:
        st.caption(f"File size: {file_size_mb:.1f} MB")
        file_hash = get_file_hash(file_bytes)

        # Check for cached results
        cached_data = load_from_cache(file_hash)

        if cached_data:
            st.info(f"Found cached analysis for this file! (Hash: {file_hash[:8]}...)")
            use_cache_col1, use_cache_col2 = st.columns(2)
            with use_cache_col1:
                if st.button("Use Cached Results"):
                    with st.spinner("Loading cached results..."):
                        cleanup_working_dir()
                        try:
                            images = convert_pdf_to_images(file_bytes)
                        except Exception as e:
                            st.error(f"Failed to convert PDF: {e}. The file may be corrupted or password-protected.")
                            st.stop()
                        for idx, img in enumerate(images):
                            save_slide_image(img, idx + 1)
                        st.session_state.slides = list(range(1, len(images) + 1))
                        st.session_state.source_filename = uploaded_file.name
                        st.session_state.intro_summary = cached_data.get("intro_summary")
                        st.session_state.outro_summary = cached_data.get("outro_summary")
                        st.session_state.questions = {int(k): v for k, v in cached_data.get("questions", {}).items()}
                        cached_selected = cached_data.get("selected", [])
                        selected_set = {(s, i) for s, i in cached_selected} if cached_selected else None
                        for slide_num, qs in st.session_state.questions.items():
                            for qi in range(len(qs)):
                                if selected_set is not None:
                                    st.session_state[f"slide_{slide_num}_q_{qi}"] = (slide_num, qi) in selected_set
                                else:
                                    st.session_state[f"slide_{slide_num}_q_{qi}"] = True
                        st.session_state.analyzed = True
                        st.session_state.ai_already_selected = True
                        st.session_state.user_modified_selection = False
                        st.rerun()
            with use_cache_col2:
                if st.button("Re-analyze (ignore cache)"):
                    clear_cache()
                    st.session_state["force_reanalyze"] = True
                    st.rerun()

        if not cached_data or st.session_state.get("force_reanalyze", False):
            # PDF preview before analysis
            with st.spinner("Converting PDF for preview..."):
                try:
                    preview_images = convert_pdf_to_images(file_bytes)
                except Exception as e:
                    st.error(f"Failed to convert PDF: {e}. The file may be corrupted or password-protected.")
                    st.stop()

                cleanup_working_dir()
                for idx, img in enumerate(preview_images):
                    save_slide_image(img, idx + 1)

            total = len(preview_images)
            st.write(f"**{total} slides** found in this PDF")

            # Thumbnail grid (4 per row)
            st.subheader("Slide Preview")
            cols_per_row = 4
            for row_start in range(0, total, cols_per_row):
                cols = st.columns(cols_per_row)
                for col_idx, slide_idx in enumerate(range(row_start, min(row_start + cols_per_row, total))):
                    with cols[col_idx]:
                        path = get_slide_image_path(slide_idx + 1)
                        if path.exists():
                            st.image(str(path), width=THUMBNAIL_WIDTH, caption=f"Slide {slide_idx + 1}")

            # Analysis options
            st.subheader("Analysis Options")
            col1, col2 = st.columns(2)
            with col1:
                generate_intro = st.checkbox("Generate introduction summary", value=True, key="gen_intro")
            with col2:
                generate_outro = st.checkbox("Generate conclusion summary", value=True, key="gen_outro")

            # Configurable slide ranges
            range_col1, range_col2 = st.columns(2)
            with range_col1:
                intro_count = st.number_input(
                    "Number of intro slides to skip (questions)",
                    min_value=0, max_value=total,
                    value=min(DEFAULT_INTRO_SLIDES, total),
                    key="intro_slide_count"
                )
            with range_col2:
                outro_count = st.number_input(
                    "Number of outro slides to skip (questions)",
                    min_value=0, max_value=total,
                    value=min(DEFAULT_OUTRO_SLIDES, total),
                    key="outro_slide_count"
                )

            # Show slide range preview
            content_start = min(intro_count, total)
            content_end = max(content_start, total - outro_count)
            if content_end <= content_start:
                # For small decks, treat all slides as content
                content_start = 0
                content_end = total

            if intro_count > 0 and content_start > 0:
                intro_label = f"Slides 1-{content_start}: Intro"
            else:
                intro_label = ""
            content_label = f"Slides {content_start + 1}-{content_end}: Content (questions)"
            if outro_count > 0 and content_end < total:
                outro_label = f"Slides {content_end + 1}-{total}: Conclusion"
            else:
                outro_label = ""
            range_parts = [p for p in [intro_label, content_label, outro_label] if p]
            st.caption(" | ".join(range_parts))

            # Custom instructions
            custom_instructions = st.text_area(
                "Course context / special instructions (optional)",
                value=st.session_state.custom_instructions,
                key="custom_instructions_input",
                placeholder="e.g., 'This is a biology course for nursing students. Focus on clinical applications.'",
                help="This context will be included in all question generation prompts."
            )
            st.session_state.custom_instructions = custom_instructions

            if st.button("Analyze Slides"):
                st.session_state.pop("force_reanalyze", None)

                st.session_state.slides = list(range(1, total + 1))
                st.session_state.source_filename = uploaded_file.name

                # Analyze intro slides
                if generate_intro and content_start > 0:
                    with st.spinner("Analyzing introduction..."):
                        intro_texts = []
                        for idx in range(content_start):
                            b64 = get_base64_for_slide(idx + 1)
                            if b64:
                                try:
                                    intro_texts.append(analyze_slide_intro(b64))
                                except Exception as e:
                                    st.warning(f"Error on intro slide {idx + 1}: {e}")
                        st.session_state.intro_summary = "\n".join(intro_texts) if intro_texts else None
                else:
                    st.session_state.intro_summary = None

                # Analyze outro slides
                if generate_outro and content_end < total:
                    with st.spinner("Analyzing conclusion..."):
                        outro_texts = []
                        for idx in range(content_end, total):
                            b64 = get_base64_for_slide(idx + 1)
                            if b64:
                                try:
                                    outro_texts.append(analyze_slide_outro(b64))
                                except Exception as e:
                                    st.warning(f"Error on outro slide {idx + 1}: {e}")
                        st.session_state.outro_summary = "\n".join(outro_texts) if outro_texts else None
                else:
                    st.session_state.outro_summary = None

                # Analyze content slides
                cache_hits = 0
                api_calls = 0
                num_content = content_end - content_start

                if num_content > 0:
                    progress = st.progress(0)

                for idx, slide_idx in enumerate(range(content_start, content_end)):
                    slide_num = slide_idx + 1
                    image = load_slide_image(slide_num)
                    if image is None:
                        continue

                    # Check per-slide image cache
                    cached_qs, image_hash = get_cached_questions_for_image(image)

                    if cached_qs:
                        st.session_state.questions[slide_num] = cached_qs
                        for qi in range(len(cached_qs)):
                            st.session_state[f"slide_{slide_num}_q_{qi}"] = True
                        cache_hits += 1
                    else:
                        with st.spinner(f"Analyzing slide {slide_num}..."):
                            try:
                                b64 = image_to_base64(image)
                                result = analyze_slide_content(b64, custom_instructions=custom_instructions)
                                questions = result.get("questions", [])
                                st.session_state.questions[slide_num] = questions
                                for qi in range(len(questions)):
                                    st.session_state[f"slide_{slide_num}_q_{qi}"] = True
                                save_questions_for_image(image_hash, questions)
                                api_calls += 1
                            except Exception as e:
                                err = str(e).lower()
                                if "rate" in err and "limit" in err:
                                    st.error("Rate limited by the API. Please wait 60 seconds and try again.")
                                    break
                                elif "auth" in err or "unauthorized" in err or "invalid" in err and "key" in err:
                                    st.error("API key is invalid or expired. Please log out and re-enter your key.")
                                    break
                                else:
                                    st.warning(f"Error on slide {slide_num}, skipping: {e}")

                    if num_content > 0:
                        progress.progress((idx + 1) / num_content)

                # Report cache usage
                if cache_hits > 0:
                    st.toast(f"Reused {cache_hits} slides from cache, analyzed {api_calls} new slides")
                elif api_calls > 0:
                    st.toast(f"Analyzed {api_calls} slides")

                # Use Opus to review and pre-select the best questions
                if st.session_state.questions:
                    with st.spinner("Reviewing questions with advanced model..."):
                        try:
                            selected_set = review_and_select_questions(st.session_state.questions, total)
                            for slide_num, qs in st.session_state.questions.items():
                                for qi in range(len(qs)):
                                    is_selected = (slide_num, qi) in selected_set
                                    st.session_state[f"slide_{slide_num}_q_{qi}"] = is_selected

                            selected_count = len(selected_set)
                            st.toast(f"Pre-selected {selected_count} questions for ~2 page guide")
                        except Exception as e:
                            st.warning(f"Could not run AI selection: {e}. All questions selected by default.")
                            selected_set = {(sn, qi) for sn, qs in st.session_state.questions.items() for qi in range(len(qs))}

                    st.session_state.ai_already_selected = True
                    st.session_state.user_modified_selection = False

                    # Save questions to CSV
                    save_questions_to_csv(
                        st.session_state.questions,
                        uploaded_file.name,
                        selected_set
                    )

                    # Save full file to cache
                    selected_list = [[s, i] for s, i in selected_set]
                    cache_data = {
                        "intro_summary": st.session_state.intro_summary,
                        "outro_summary": st.session_state.outro_summary,
                        "questions": st.session_state.questions,
                        "selected": selected_list
                    }
                    save_to_cache(file_hash, cache_data)

                st.session_state.analyzed = True
                st.rerun()

# Show results and selection UI
if st.session_state.analyzed:
    # Top controls
    top_col1, top_col2, top_col3 = st.columns([4, 2, 1])
    with top_col1:
        st.success("Analysis complete! Select the questions you want to include:")
    with top_col2:
        ai_already = st.session_state.get("ai_already_selected", False)
        user_modified = st.session_state.get("user_modified_selection", False)
        button_disabled = ai_already and not user_modified

        if button_disabled:
            st.button("Let AI select questions", key="ai_select_top", disabled=True,
                      help="AI has already pre-selected questions. Modify your selection first to re-run AI selection.")
        else:
            if st.button("Let AI select questions", key="ai_select_top",
                         help="Use AI to select the best questions for a ~2 page guide"):
                with st.spinner("AI is selecting the best questions..."):
                    total_slides = len(st.session_state.slides)
                    try:
                        selected_set = review_and_select_questions(st.session_state.questions, total_slides)
                        for slide_num, qs in st.session_state.questions.items():
                            for qi in range(len(qs)):
                                is_selected = (slide_num, qi) in selected_set
                                st.session_state[f"slide_{slide_num}_q_{qi}"] = is_selected
                        st.toast(f"AI selected {len(selected_set)} questions for ~2 page guide")
                    except Exception as e:
                        st.error(f"AI selection failed: {e}")
                    st.session_state.ai_already_selected = True
                    st.session_state.user_modified_selection = False
                st.rerun()
    with top_col3:
        if st.button("Start Over", key="start_over_top"):
            cleanup_working_dir()
            api_key = st.session_state.api_key
            provider = st.session_state.provider
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.api_key = api_key
            st.session_state.provider = provider
            st.rerun()

    # Show intro summary
    if st.session_state.get("intro_summary"):
        with st.expander("Introduction Summary", expanded=False):
            st.write(st.session_state.intro_summary)

    # Question selection
    st.subheader("Select Questions")

    # Calculate global selection state
    total_questions = sum(len(qs) for qs in st.session_state.questions.values())
    selected_count = sum(
        1 for sn, qs in st.session_state.questions.items()
        for qi in range(len(qs))
        if st.session_state.get(f"slide_{sn}_q_{qi}", True)
    )

    # Global toggle
    global_col1, global_col2 = st.columns([1, 5])
    with global_col1:
        if selected_count == total_questions:
            st.button("All Selected", key="global_toggle", type="primary",
                     on_click=toggle_all_selection, args=(False,))
        elif selected_count == 0:
            st.button("None Selected", key="global_toggle",
                     on_click=toggle_all_selection, args=(True,))
        else:
            st.button(f"{selected_count}/{total_questions}", key="global_toggle",
                     on_click=toggle_all_selection, args=(True,))

    # Pagination
    slide_nums = sorted(st.session_state.questions.keys())
    total_pages = max(1, (len(slide_nums) + SLIDES_PER_PAGE - 1) // SLIDES_PER_PAGE)
    current_page = st.session_state.current_page
    if current_page >= total_pages:
        current_page = total_pages - 1
        st.session_state.current_page = current_page

    page_start = current_page * SLIDES_PER_PAGE
    page_end = min(page_start + SLIDES_PER_PAGE, len(slide_nums))
    page_slide_nums = slide_nums[page_start:page_end]

    if total_pages > 1:
        pag_col1, pag_col2, pag_col3 = st.columns([1, 3, 1])
        with pag_col1:
            if st.button("Previous", disabled=(current_page == 0), key="prev_page"):
                st.session_state.current_page = current_page - 1
                st.rerun()
        with pag_col2:
            st.caption(f"Page {current_page + 1} of {total_pages} (slides {page_slide_nums[0]}-{page_slide_nums[-1]})")
        with pag_col3:
            if st.button("Next", disabled=(current_page >= total_pages - 1), key="next_page"):
                st.session_state.current_page = current_page + 1
                st.rerun()

    for slide_num in page_slide_nums:
        qs = st.session_state.questions[slide_num]
        with st.expander(f"Slide {slide_num}", expanded=False):
            col1, col2 = st.columns([1, 3])
            with col1:
                path = get_slide_image_path(slide_num)
                if path.exists():
                    st.image(str(path), width=THUMBNAIL_WIDTH)

            with col2:
                # Per-slide selection state
                slide_selected = sum(1 for qi in range(len(qs)) if st.session_state.get(f"slide_{slide_num}_q_{qi}", True))
                slide_total = len(qs)

                slide_btn_col1, slide_btn_col2 = st.columns([1, 4])
                with slide_btn_col1:
                    if slide_selected == slide_total:
                        st.button("All", key=f"toggle_{slide_num}", help="All selected - click to deselect",
                                  on_click=toggle_slide_selection, args=(slide_num, False))
                    elif slide_selected == 0:
                        st.button("None", key=f"toggle_{slide_num}", help="None selected - click to select all",
                                  on_click=toggle_slide_selection, args=(slide_num, True))
                    else:
                        st.button(f"{slide_selected}/{slide_total}", key=f"toggle_{slide_num}", help="Some selected - click to select all",
                                  on_click=toggle_slide_selection, args=(slide_num, True))

                # Display each question
                for qi, q in enumerate(qs):
                    key = f"slide_{slide_num}_q_{qi}"
                    display_text = format_question_display(q)
                    if key not in st.session_state:
                        st.session_state[key] = True
                    st.checkbox(display_text, key=key, on_change=on_checkbox_change)

                    # Inline edit button
                    edit_key = f"edit_{slide_num}_{qi}"
                    if st.button("Edit", key=f"edit_btn_{slide_num}_{qi}"):
                        st.session_state[edit_key] = not st.session_state.get(edit_key, False)

                    if st.session_state.get(edit_key, False):
                        current_text = get_question_text(q)
                        new_text = st.text_area(
                            "Edit question text:",
                            value=current_text,
                            key=f"edit_area_{slide_num}_{qi}"
                        )
                        if st.button("Save", key=f"save_edit_{slide_num}_{qi}"):
                            qtype = q.get("type", "open_ended")
                            if qtype == "open_ended":
                                st.session_state.questions[slide_num][qi]["question"] = new_text
                            elif qtype == "short_answer":
                                st.session_state.questions[slide_num][qi]["prompt"] = new_text
                            elif qtype == "fill_in_blank":
                                st.session_state.questions[slide_num][qi]["sentence"] = new_text
                            elif qtype == "true_false":
                                st.session_state.questions[slide_num][qi]["statement"] = new_text
                            elif qtype == "multiple_choice":
                                st.session_state.questions[slide_num][qi]["question"] = new_text
                            elif qtype == "put_in_order":
                                st.session_state.questions[slide_num][qi]["instruction"] = new_text
                            st.session_state[edit_key] = False
                            st.rerun()

            # View full image
            with st.popover("View Full Size Slide"):
                image_path = get_slide_image_path(slide_num)
                if image_path.exists():
                    st.image(str(image_path), width="stretch")

            st.markdown("---")

            # Regeneration controls
            regen_key = f"regen_expand_{slide_num}"
            if st.button("Regenerate with...", key=f"regen_btn_{slide_num}"):
                st.session_state[regen_key] = not st.session_state.get(regen_key, False)

            if st.session_state.get(regen_key, False):
                st.write("Select question types to generate:")
                regen_types = []
                type_cols = st.columns(6)
                for type_idx, (qtype, label) in enumerate(QUESTION_TYPE_LABELS.items()):
                    with type_cols[type_idx]:
                        if st.checkbox(label, key=f"regen_type_{slide_num}_{qtype}"):
                            regen_types.append(qtype)

                use_opus = st.checkbox("Use advanced model (Opus)", key=f"use_opus_{slide_num}",
                                       help="Use Claude Opus for higher quality questions (slower, more expensive)")

                if st.button("Generate", key=f"do_regen_{slide_num}"):
                    if regen_types:
                        model_name = "Opus" if use_opus else "Sonnet"
                        with st.spinner(f"Regenerating questions with {model_name}..."):
                            b64 = get_base64_for_slide(slide_num)
                            if b64:
                                try:
                                    old_count = len(st.session_state.questions.get(slide_num, []))
                                    clean_slide_question_keys(slide_num, old_count)

                                    result = regenerate_questions(
                                        b64, slide_num, regen_types,
                                        use_advanced_model=use_opus,
                                        custom_instructions=st.session_state.custom_instructions
                                    )
                                    new_questions = result.get("questions", [])
                                    st.session_state.questions[slide_num] = new_questions
                                    for qi in range(len(new_questions)):
                                        st.session_state[f"slide_{slide_num}_q_{qi}"] = True
                                    st.session_state[regen_key] = False
                                    st.session_state.teacher_questions = None

                                    save_questions_to_csv(
                                        {slide_num: new_questions},
                                        st.session_state.get("source_filename", "unknown"),
                                        None
                                    )
                                except Exception as e:
                                    st.error(f"Regeneration failed: {e}")
                            else:
                                st.error("Could not load slide image from disk.")
                        st.rerun()
                    else:
                        st.warning("Please select at least one question type.")

    # Pagination at bottom too
    if total_pages > 1:
        pag_col1b, pag_col2b, pag_col3b = st.columns([1, 3, 1])
        with pag_col1b:
            if st.button("Previous", disabled=(current_page == 0), key="prev_page_bottom"):
                st.session_state.current_page = current_page - 1
                st.rerun()
        with pag_col2b:
            st.caption(f"Page {current_page + 1} of {total_pages}")
        with pag_col3b:
            if st.button("Next", disabled=(current_page >= total_pages - 1), key="next_page_bottom"):
                st.session_state.current_page = current_page + 1
                st.rerun()

    # Show outro summary
    if st.session_state.get("outro_summary"):
        with st.expander("Conclusion Summary", expanded=False):
            st.write(st.session_state.outro_summary)

    # Download options
    st.subheader("Export Options")

    export_col1, export_col2, export_col3 = st.columns(3)
    with export_col1:
        if st.session_state.get("intro_summary"):
            st.session_state.include_intro = st.checkbox(
                "Include introduction summary",
                value=st.session_state.include_intro,
                key="export_include_intro"
            )
    with export_col2:
        if st.session_state.get("outro_summary"):
            st.session_state.include_outro = st.checkbox(
                "Include conclusion summary",
                value=st.session_state.include_outro,
                key="export_include_outro"
            )
    with export_col3:
        export_canvas = st.checkbox(
            "Export for Canvas LMS",
            value=False,
            key="export_canvas",
            help="Generate a QTI file for importing into Canvas quizzes"
        )

    # Collect selected questions
    final_questions = {}
    for slide_num, qs in st.session_state.questions.items():
        selected_qs = [q for qi, q in enumerate(qs) if st.session_state.get(f"slide_{slide_num}_q_{qi}", True)]
        if selected_qs:
            final_questions[slide_num] = selected_qs

    export_intro = st.session_state.get("intro_summary") if st.session_state.include_intro else None
    export_outro = st.session_state.get("outro_summary") if st.session_state.include_outro else None

    fmt_col, spacer_col = st.columns([1, 3])
    with fmt_col:
        export_format = st.selectbox(
            "Export format",
            ["Word (.docx)", "PDF (.pdf)", "HTML (.html)"],
            key="export_format",
        )

    # --- Student downloads (always available — no AI calls) ---
    st.markdown("**Student Version**")
    stu_col1, stu_col2, stu_col3 = st.columns(3)
    with stu_col1:
        student_docx = create_docx(export_intro, final_questions, export_outro, show_answers=False)
        st.download_button(
            "Student (.docx)", student_docx,
            "note_guide_student.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    with stu_col2:
        student_pdf = create_pdf(export_intro, final_questions, export_outro, show_answers=False)
        st.download_button(
            "Student (.pdf)", student_pdf,
            "note_guide_student.pdf", "application/pdf",
        )
    with stu_col3:
        student_html = create_html(export_intro, final_questions, export_outro, show_answers=False)
        st.download_button(
            "Student (.html)", student_html,
            "note_guide_student.html", "text/html",
        )

    # --- Teacher guide (on-demand) ---
    st.markdown("**Teacher Answer Key**")

    # Initialize teacher_questions in session state
    if "teacher_questions" not in st.session_state:
        st.session_state.teacher_questions = None

    # Check if example answers are already present for all open-ended questions
    needs_examples = any(
        q.get("type") == "open_ended" and not q.get("example_answer")
        for qs in final_questions.values()
        for q in qs
    )

    if needs_examples and st.session_state.teacher_questions is None:
        if st.button("Generate Teacher Guide", help="Generates example answers for open-ended questions (requires AI calls)"):
            with st.spinner("Generating example answers for teacher guide..."):
                teacher_questions = generate_example_answers(
                    final_questions,
                    get_base64_for_slide
                )
                save_questions_to_csv(
                    teacher_questions,
                    st.session_state.get("source_filename", "unknown"),
                    None
                )
                st.session_state.teacher_questions = teacher_questions
            st.rerun()
        else:
            st.caption("Click the button above to generate example answers before downloading the teacher version.")
    else:
        # Either all answers exist already, or we generated them previously
        teacher_questions = st.session_state.teacher_questions if st.session_state.teacher_questions is not None else final_questions

        tea_col1, tea_col2, tea_col3 = st.columns(3)
        with tea_col1:
            teacher_docx = create_docx(export_intro, teacher_questions, export_outro, show_answers=True)
            st.download_button(
                "Teacher (.docx)", teacher_docx,
                "note_guide_teacher.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        with tea_col2:
            teacher_pdf = create_pdf(export_intro, teacher_questions, export_outro, show_answers=True)
            st.download_button(
                "Teacher (.pdf)", teacher_pdf,
                "note_guide_teacher.pdf", "application/pdf",
            )
        with tea_col3:
            teacher_html = create_html(export_intro, teacher_questions, export_outro, show_answers=True)
            st.download_button(
                "Teacher (.html)", teacher_html,
                "note_guide_teacher.html", "text/html",
            )

    # Utility buttons
    util_col1, util_col2 = st.columns(2)
    with util_col1:
        if st.button("Clean up images"):
            cleanup_working_dir()
            st.success("Working images cleaned up!")
    with util_col2:
        if st.button("Clear analysis cache"):
            clear_cache()
            st.session_state.analyzed = False
            st.session_state.questions = {}
            st.session_state.teacher_questions = None
            st.success("Analysis cache cleared! Please re-analyze to use updated question generation.")
            st.rerun()

    # Canvas LMS export
    if st.session_state.get("export_canvas", False):
        st.markdown("---")
        st.markdown("**Canvas LMS Export**")
        canvas_col1, canvas_col2 = st.columns([1, 3])
        with canvas_col1:
            canvas_qti = create_canvas_qti(final_questions, "Note-Taking Quiz")
            st.download_button(
                "Download Canvas Quiz (.zip)",
                canvas_qti,
                "canvas_quiz.zip",
                "application/zip",
                help="Import this ZIP file into Canvas: Quizzes > ... > Import"
            )
        with canvas_col2:
            st.caption(
                "To import: In Canvas, go to **Quizzes** > click **...** (kebab menu) > "
                "**Import** > select the ZIP file. Question types: Multiple Choice, "
                "True/False, Fill in Blank > Short Answer, Open-ended/Ordering > Essay."
            )

    # Questions history section
    if QUESTIONS_CSV_PATH.exists():
        st.markdown("---")
        st.markdown("**Questions History**")
        hist_col1, hist_col2 = st.columns([1, 3])
        with hist_col1:
            with open(QUESTIONS_CSV_PATH, 'rb') as f:
                st.download_button(
                    "Download Questions History (CSV)",
                    f,
                    "questions_history.csv",
                    "text/csv",
                    help="All generated questions across all sessions"
                )
        with hist_col2:
            st.caption(
                "This CSV contains all questions generated across sessions, including question type, "
                "slide number, answers, and whether each question was selected. Import into Excel or "
                "Google Sheets for analysis."
            )

    # Reset buttons
    reset_col1, reset_col2 = st.columns([1, 1])
    with reset_col1:
        if st.button("Start Over"):
            cleanup_working_dir()
            api_key = st.session_state.api_key
            provider = st.session_state.provider
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.api_key = api_key
            st.session_state.provider = provider
            st.rerun()
    with reset_col2:
        if st.button("Log Out"):
            cleanup_working_dir()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
