# Slide Guide Generator

Convert PDF slide decks into AI-generated student study guides using Claude or Mistral AI.

Upload a PDF, configure which slides are intro/content/conclusion, and the app generates structured questions (open-ended, short answer, fill-in-the-blank, true/false, multiple choice, ordering). An advanced AI model reviews and selects the best questions for a ~2 page guide. Export as Word, PDF, HTML, teacher answer key, or Canvas LMS quiz.

## Setup

### 1. Install Python

- **Windows:** Download from [python.org](https://www.python.org/downloads/). During install, check **"Add Python to PATH"**.
- **macOS:** `brew install python` or download from python.org.
- **Linux:** Usually pre-installed. If not: `sudo apt install python3 python3-venv`

### 2. Clone and install

```bash
git clone https://github.com/bethanychamberlain/slides-generator.git
cd slides-generator
python -m venv venv
```

Activate the virtual environment:
- **Windows:** `venv\Scripts\activate`
- **macOS/Linux:** `source venv/bin/activate`

Then install dependencies:
```bash
pip install -r requirements.txt
```

### 3. API keys

**Option A: Faculty profiles (recommended for shared setups)**

Create a `users.json` file in the project root:

```json
[
  {
    "name": "Your Name",
    "password": "simple-password",
    "keys": {
      "anthropic": "sk-ant-...",
      "mistral": "optional-mistral-key"
    }
  }
]
```

Faculty select their name, enter their password, and choose a provider. Omit the `"mistral"` key if not needed.

**Option B: Manual entry**

Each user enters their own API key on the login screen. Choose a provider:

- **Anthropic (Claude)** — smartest models (Sonnet + Opus). Get a key at https://console.anthropic.com/settings/keys
- **Mistral AI** — data stays in the EU. Get a key at https://console.mistral.ai/api-keys

If a `users.json` file exists, manual entry is still available via the "Other" option in the dropdown.

### 4. Run

**Option A: Tray icon (local use)**

Double-click `Slide Guide Generator.desktop` on Linux, or run:
```bash
python tray.py
```
This starts a system tray icon that manages the server. Right-click for Start/Stop/Open/Quit.

**Option B: Beta server (share with colleagues via dev tunnel)**

```bash
./start-beta.sh
```
Starts Streamlit + Azure Dev Tunnel together, prints the shareable URL, and shows activity in the terminal. Close the terminal to stop everything. There is also a desktop shortcut ("Slide Guide Beta Server") for this.

**Option C: Command line**
```bash
streamlit run app.py
```

The app opens at http://localhost:8501.

## Usage

1. **Log in** — select your name (or enter an API key manually)
2. **Upload a PDF** slide deck
3. **Preview slides** and configure intro/outro slide counts
4. Optionally add course context or special instructions
5. Click **Analyze Slides** — the AI generates questions for each content slide
6. **Review, edit, select/deselect** questions — use "Let AI select questions" to auto-pick the best mix
7. **Export** student and teacher versions:

### Export Formats

| Format | Student Version | Teacher Version |
|--------|----------------|-----------------|
| **Word (.docx)** | Blank answer spaces | Answers in green |
| **PDF (.pdf)** | Blank answer spaces | Answers in green |
| **HTML (.html)** | Write spaces, name/date fields | Green answers, no write spaces |
| **Canvas Quiz (.zip)** | QTI for Canvas LMS import | — |

Student downloads are always available instantly. Teacher downloads require clicking **"Generate Teacher Guide"** first (this generates example answers for open-ended questions via AI).

## Windows Desktop Shortcut

To create a shortcut on Windows:

1. Right-click on the Desktop and select **New > Shortcut**
2. For the location, enter:
   ```
   C:\path\to\slides-generator\venv\Scripts\pythonw.exe C:\path\to\slides-generator\tray.py
   ```
   (Replace `C:\path\to\slides-generator` with the actual path)
3. Name it "Slide Guide Generator"
4. Right-click the shortcut > Properties > Change Icon > Browse to `icon.png` in the project folder

Use `pythonw.exe` (not `python.exe`) so no console window appears.

## Project Structure

```
app.py              Streamlit UI (main application)
ai.py               AI API calls, prompts, JSON parsing
cache.py            File-hash and slide-image caching
questions.py        Question types, formatting, CSV history
export_docx.py      Word document generation
export_pdf.py       PDF generation
export_html.py      HTML generation (embedded CSS, DIS theme)
export_qti.py       Canvas LMS QTI export
tray.py             System tray icon (desktop mode)
start-beta.sh       Beta server launcher (Streamlit + dev tunnel)
users.json          Faculty profiles and API keys (gitignored)
```

## Deployment

See [docs/beta-testing-guide.md](docs/beta-testing-guide.md) for the full beta setup and [DEPLOY_AZURE.md](DEPLOY_AZURE.md) for Azure App Service deployment.
