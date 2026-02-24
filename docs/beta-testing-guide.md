# Slide Guide Generator — Beta Testing & Technical Overview

## What This Program Does

The Slide Guide Generator converts PDF lecture slides into AI-generated student study guides. Faculty upload a slide deck, and the app:

1. Converts each slide to an image
2. Uses AI (Claude or Mistral) to analyze content slides and generate structured questions
3. Uses an advanced AI model to review all questions and pre-select the best ~15-20 for a 2-page guide
4. Lets the instructor review, edit, select/deselect, and regenerate questions
5. Exports in multiple formats: Word (.docx), PDF, HTML, and Canvas LMS quiz (QTI)

### Question Types

The AI generates six types of questions, prioritizing deeper engagement:

| Type | Example | Student Version | Teacher Version |
|------|---------|-----------------|-----------------|
| Open-ended | "How does X contribute to Y?" | Write space (blank lines) | Green example answer |
| Short answer | "What does PAMP stand for?" | Blank line | Green answer |
| Fill in blank | "The _____ is the powerhouse..." | Blank in sentence | Answer filled in green |
| True/False | "Water boils at 100C at sea level" | Empty radio buttons | Correct answer highlighted |
| Multiple choice | "Which is the largest planet?" | Options listed | Correct option in green |
| Put in order | "Arrange these steps..." | Items shown, blank order line | Correct order in green |

### Export Formats

- **Word (.docx)** — Times New Roman, compact layout, works offline
- **PDF** — Same layout, fixed formatting, good for printing
- **HTML** — Clean web-native design with Merriweather headings, teal accents, Google Fonts; prints well with Ctrl+P
- **Canvas QTI (.zip)** — Import directly into Canvas LMS as a quiz

Student versions have blank answer spaces. Teacher versions show all answers in green.

---

## How It's Running Right Now (Beta Setup)

The app is running on Bethany's desktop computer and shared with colleagues via an Azure Dev Tunnel.

### Architecture

```
Faculty browser  --->  Azure Dev Tunnel  --->  Bethany's PC (port 8501)
                       (encrypted proxy)        └── Streamlit server
                                                    └── AI API calls
                                                        (Anthropic / Mistral)
```

- **Streamlit** serves the web UI on port 8501
- **Azure Dev Tunnel** creates a secure HTTPS URL (`https://...devtunnels.ms`) that proxies traffic to the local port
- **AI calls** go directly from the server to Anthropic or Mistral's API — slide images are sent to the AI, questions come back
- **Each faculty member** has their own profile in `users.json` with pre-configured API keys for both providers
- **Session isolation** — each browser session gets its own working directory for slide images, so concurrent users don't collide

### Starting the Beta Server

Double-click **"Slide Guide Beta Server"** on the desktop. This opens a terminal that:

1. Frees port 8501 if something else is using it
2. Starts Streamlit
3. Starts the dev tunnel
4. Prints the shareable URL
5. Shows a log of activity (you can see when colleagues connect)

Close the terminal window to stop everything.

### Faculty Login

Faculty select their name from a dropdown, enter their simple password, and choose their AI provider (Anthropic or Mistral). API keys are stored in `users.json` on the server — faculty never see or handle keys directly.

### Limitations of This Setup

- **Depends on Bethany's computer being on** — if the PC sleeps, shuts down, or loses internet, the app goes down
- **Performance limited to one machine** — PDF conversion and AI calls share Bethany's CPU/RAM
- **Dev tunnel URL may change** — if the tunnel is recreated, faculty get a new URL
- **No automatic backups** — analysis cache and question history live only on local disk

---

## What We Fixed for Beta (February 2025)

### 1. JSON Parsing Bug (questions showing as raw JSON blobs)

**Problem:** AI models return JSON with literal unescaped newlines inside string values. Python's `json.loads` rejects these per the JSON spec, so the parser returned `None` and the app fell back to displaying the raw AI text — showing messy JSON blobs instead of formatted questions.

**Fix:** Added a `_repair_json_string()` function that walks character-by-character, tracking whether it's inside a JSON string value, and escapes literal newlines/tabs. Also removes trailing commas (another common AI JSON quirk). The repair runs as a fallback only when standard parsing fails, so well-formed JSON has zero overhead.

### 2. Teacher Guide Auto-Generation Causing Slowness

**Problem:** The export section automatically called the AI to generate example answers for every open-ended question on every page render. In Streamlit, any user interaction (clicking a checkbox, scrolling) triggers a full re-execution of the script — so this meant repeated, expensive API calls before the user had even chosen to export.

**Fix:** Student download buttons are now always available with no AI calls. Teacher guide generation is behind an explicit "Generate Teacher Guide" button. Teacher downloads only appear after generation completes. The cached teacher data is invalidated when the user changes their question selection.

### 3. HTML Export

**New feature:** Added a self-contained HTML export option with embedded CSS adapted from the DIS Scholarly theme — Merriweather serif headings, Source Sans 3 body text, teal accents (#008ab0), cyan highlights, and print-optimized styles. The HTML file works standalone with no external dependencies (fonts load from Google Fonts when online, fall back to system fonts offline).

### 4. PDF Unicode Crash

**Problem:** AI-generated text containing Unicode characters like curly quotes (') crashed the PDF export because fpdf2's internal validator rejected them before our sanitizer could run.

**Fix:** Moved the Unicode sanitization to `normalize_text()` — the lowest level in fpdf2's text pipeline — so characters are cleaned before any validation occurs.

### 5. Per-Session Isolation

**Problem:** All users shared a single `working_images/` directory. If two people uploaded PDFs at the same time, their slide images would overwrite each other.

**Fix:** Each Streamlit session now gets a UUID-based subdirectory under `working_images/`, so concurrent users are fully isolated.

### 6. Faculty Profile Login

**New feature:** Added a `users.json` configuration file mapping faculty names to their API keys (both Anthropic and Mistral). Faculty pick their name, enter a simple password, choose their provider, and click Start — no key management needed. Manual key entry is still available via the "Other" option.

---

## Project Structure

```
app.py              Streamlit UI (main application)
ai.py               AI API calls, prompts, JSON parsing
cache.py            File-hash and slide-image caching
questions.py        Question types, formatting, CSV history
export_docx.py      Word document generation
export_pdf.py       PDF generation (fpdf2, Times New Roman)
export_html.py      HTML generation (embedded CSS, DIS theme)
export_qti.py       Canvas LMS QTI export
tray.py             System tray icon (desktop mode)
start-beta.sh       Beta server launcher (Streamlit + dev tunnel)
users.json          Faculty profiles and API keys (gitignored)
```

---

## Future Directions: Permanent Hosting

The current setup (running on Bethany's PC via dev tunnel) works for a small beta, but isn't sustainable long-term. Here are the options for permanent hosting, in order of what to ask IT for.

### Option A: Azure App Service (Recommended)

This is the most straightforward path. The app is already configured for Azure deployment (see `DEPLOY_AZURE.md` and `startup.sh`).

**What to ask IT:**

> "I have a Python web application (Streamlit) that I need hosted on Azure App Service. I need:
>
> 1. **An Azure subscription** with permission to create resources (or an existing resource group I can deploy to)
> 2. **An App Service plan** — B1 tier ($13/month) is sufficient for a small team. The free tier (F1) doesn't work because it lacks enough memory for PDF processing and has a 60-minute daily CPU limit.
> 3. **Python 3.11+ runtime** on Linux
> 4. **Permission to run a custom startup script** that installs `poppler-utils` (a system library for PDF-to-image conversion)
> 5. Optionally: **Azure AD authentication** enabled so only people with institutional accounts can access it
>
> The app itself doesn't store sensitive data server-side. Faculty enter their own AI API keys (Anthropic or Mistral) in the browser. The keys are only used during the session and aren't persisted on the server.
>
> Deployment is a single command: `az webapp up --name <app-name> --resource-group <group> --runtime 'PYTHON:3.11'`
>
> The code is on GitHub: https://github.com/bethanychamberlain/slides-generator"

**Why the free tier didn't work:** Azure's F1 (free) tier has only 1 GB RAM and a 60-minute daily compute limit. Converting a 30-slide PDF at 300 DPI uses ~500 MB of memory, and each AI analysis takes compute time. The B1 tier ($13/month) has 1.75 GB RAM and no daily limits — enough for a small faculty team.

**Cost estimate:** B1 plan = ~$13/month. AI API costs are borne by each faculty member's own key (or a shared departmental key if preferred). A typical 30-slide deck costs roughly $0.50-1.00 in API calls to analyze.

### Option B: IT Hosts a Linux VM

If Azure App Service isn't available, a basic Linux VM works too.

**What to ask IT:**

> "I need a small Linux server (Ubuntu 22.04+) with:
> - 2 GB RAM, 1-2 CPU cores
> - Python 3.11+ installed
> - Ports 80/443 open for web traffic (or behind a reverse proxy)
> - A domain name or stable URL for faculty to bookmark
>
> I can provide the deployment instructions — it's a standard Python/Streamlit app."

IT would set up nginx as a reverse proxy in front of Streamlit, add an SSL certificate (Let's Encrypt), and optionally configure institutional SSO.

### Option C: Docker Container (Most Portable)

If IT prefers containerized deployments (Kubernetes, Docker Compose, etc.):

> "I can provide a Dockerfile. The app needs Python 3.11, poppler-utils, and about 1.5 GB RAM. It listens on port 8501. It's stateless — no database required."

This works on any container platform: Azure Container Apps, AWS ECS, Google Cloud Run, or IT's own Kubernetes cluster.

### What's Needed Regardless of Hosting

- **A stable URL** — so faculty can bookmark it (e.g., `slides.department.edu`)
- **HTTPS** — already handled by Azure App Service and most reverse proxies
- **At least 1.5 GB RAM** — for PDF-to-image conversion
- **No database required** — the app is stateless; all data lives in the browser session
- **AI API keys** — either each faculty member uses their own, or the department provides a shared key
