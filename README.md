# Slide Guide Generator

Convert PDF slide decks into AI-generated student study guides using Claude or Mistral AI.

Upload a PDF, configure which slides are intro/content/conclusion, and the app generates structured questions (open-ended, short answer, fill-in-the-blank, true/false, multiple choice, ordering). An advanced AI model reviews and selects the best questions for a ~2 page guide. Export as student DOCX, teacher answer key, or Canvas LMS quiz.

## Setup

### 1. Install Python

- **Windows:** Download from [python.org](https://www.python.org/downloads/). During install, check **"Add Python to PATH"**.
- **macOS:** `brew install python` or download from python.org.
- **Linux:** Usually pre-installed. If not: `sudo apt install python3 python3-venv`

### 2. Install Poppler (required for PDF conversion)

- **Windows:**
  1. Download the latest release from https://github.com/oschwartz10612/poppler-windows/releases
  2. Extract to `C:\poppler`
  3. Add `C:\poppler\Library\bin` to your system PATH:
     - Search "Environment Variables" in Start menu
     - Edit the `Path` variable under System variables
     - Add `C:\poppler\Library\bin`
     - Click OK and restart your terminal
- **macOS:** `brew install poppler`
- **Linux:** `sudo apt install poppler-utils`

### 3. Clone and install

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

### 4. API key

Each user enters their own API key on the login screen. Choose a provider:

- **Anthropic (Claude)** — smartest models. Get a key at https://console.anthropic.com/settings/keys
- **Mistral AI** — data stays in the EU. Get a key at https://console.mistral.ai/api-keys

### 5. Run

**Option A: Tray icon (recommended)**

Double-click `Slide Guide Generator.desktop` on Linux, or run:
```bash
python tray.py
```
This starts a system tray icon that manages the server. Right-click for Start/Stop/Open/Quit.

**Option B: Command line**
```bash
streamlit run app.py
```

The app opens at http://localhost:8501.

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

## Usage

1. Upload a PDF slide deck
2. Preview the slides and configure intro/outro slide counts
3. Optionally add course context or special instructions
4. Click **Analyze Slides** — the AI generates questions for each content slide
5. Review, edit, select/deselect questions
6. Export:
   - **Student Version** — DOCX with blank answer spaces
   - **Teacher Answer Key** — DOCX with answers in green
   - **Canvas Quiz** — QTI ZIP for importing into Canvas LMS

## Project Structure

```
app.py           Streamlit UI
ai.py            AI API calls and prompts (Anthropic + Mistral)
cache.py         File and slide caching
questions.py     Question types, formatting, CSV
export_docx.py   Word document generation
export_qti.py    Canvas QTI export
tray.py          System tray icon
```
