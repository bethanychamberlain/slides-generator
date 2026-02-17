# Enhanced Note-Taking Guide Generator - Design

## Overview

Enhance the slide guide generator with categorized question types, regeneration controls, full-size image viewing, and summary toggles.

## Features

### 1. Question Types

| Type | Badge | Output Format |
|------|-------|---------------|
| Open-ended | `[Open-ended]` | Question + "[Your notes:]" prompt |
| Fill-in-blank | `[Fill in blank]` | Sentence with `_____` gap |
| True/False | `[True/False]` | Statement + T/F options + correct answer |
| Multiple Choice | `[Multiple Choice]` | Question + 4 options (A-D) + correct answer |
| Put in Order | `[Put in order]` | 3-5 items to sequence + correct order |

### 2. Question Generation

**Initial generation per slide:**
- 1 open-ended question (always)
- 2 additional questions (Claude selects most appropriate types for content)

**Regeneration:**
- Per-slide "Regenerate with..." button
- Opens checkboxes for each question type
- Generates new questions using only selected types

### 3. Question Data Structure

```python
{
    "type": "multiple_choice",  # or open_ended, fill_in_blank, true_false, put_in_order
    "question": "What is the primary function of...",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],  # for MC
    "answer": "B",  # for MC, TF, order
    "statement": "...",  # for TF
    "items": ["...", "..."],  # for put_in_order
    "correct_order": [2, 0, 1, 3],  # for put_in_order
    "notes_prompt": "[Your notes:]"  # for open_ended
}
```

### 4. Summary Toggles

**Pre-analysis (before Analyze button):**
- Checkbox: "Generate introduction summary" (default: checked)
- Checkbox: "Generate conclusion summary" (default: checked)
- Unchecking skips API calls for those sections

**Post-analysis (in export section):**
- Checkbox: "Include introduction summary" (default: checked)
- Checkbox: "Include conclusion summary" (default: checked)
- Controls what appears in downloaded document

### 5. Image Storage

**Location:** `./working_images/`

**Workflow:**
1. Convert PDF at 300 DPI (up from 150)
2. Save as `slide_001.jpg`, `slide_002.jpg`, etc.
3. Display 200px thumbnails in UI
4. "View Full Image" button shows full-res in expander/modal

**Cleanup:**
- "Clean up images" button deletes `./working_images/` contents
- "Start Over" also triggers cleanup

### 6. UI Layout

**Pre-analysis:**
```
☑ Generate introduction summary
☑ Generate conclusion summary
[🔍 Analyze Slides]
```

**Slide card:**
```
┌─ Slide N ─────────────────────────────────────────────┐
│ [📷 View Full Image]                                  │
│                                                       │
│ ☑ [Open-ended] Full question text...                 │
│   [Your notes:]                                       │
│                                                       │
│ ☑ [Multiple Choice] Full question text...            │
│   A) Option  B) Option  C) Option  D) Option         │
│   Answer: C                                           │
│                                                       │
│ [🔄 Regenerate with...]                              │
│   ☐ Open-ended  ☐ Fill in blank  ☐ True/False       │
│   ☐ Multiple choice  ☐ Put in order                  │
│   [Generate]                                          │
└───────────────────────────────────────────────────────┘
```

**Export section:**
```
☑ Include introduction summary
☑ Include conclusion summary
[📄 Download .docx]  [🗑️ Clean up images]
```

## Implementation Notes

- Use JSON mode for Claude responses to ensure parseable question structures
- Store images on disk to avoid memory issues with large presentations
- Session state keys: `questions`, `selected`, `slides`, `intro_summary`, `outro_summary`, `include_intro`, `include_outro`, `generate_intro`, `generate_outro`
