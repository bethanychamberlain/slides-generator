# Slide Guide Generator

Convert PDF lecture slides into AI-generated student study guides with structured questions and multiple export formats.

## Features

- **AI-powered analysis** — Upload a PDF slide deck and get 6 types of study questions (open-ended, short answer, fill-in-blank, true/false, multiple choice, put-in-order)
- **AI-assisted curation** — Automatically selects the best questions for a ~2-page guide
- **Multiple export formats** — Word (.docx), PDF, HTML, Canvas LMS (QTI)
- **Student + Teacher versions** — Student guides have blank spaces; teacher guides include answers in green
- **Smart caching** — Re-uploading the same PDF skips AI analysis, saving time and API cost
- **Microsoft SSO** — Faculty sign in with their existing university Microsoft account

## Quick Start (Docker)

```bash
# Clone the repo
git clone https://github.com/bethanychamberlain/slides-generator.git
cd slides-generator

# Create .env from template
cp .env.example .env
# Edit .env with your API key and Azure Entra ID settings

# Run
docker compose up -d

# Open in browser
open http://localhost:8501
```

See [docs/deployment-guide.md](docs/deployment-guide.md) for full deployment instructions.

## Infrastructure as Code

For Azure Container Apps deployment, see [infra/README.md](infra/README.md).

## Local Development

For development without Docker:

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run (no Entra ID config = dev mode with simple name entry)
streamlit run src/app.py
```

Without `AZURE_CLIENT_ID`, the app runs in dev mode (no SSO required).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `AZURE_CLIENT_ID` | For SSO | Entra ID app registration client ID |
| `AZURE_CLIENT_SECRET` | For SSO | Entra ID app registration client secret |
| `AZURE_TENANT_ID` | For SSO | Azure AD tenant ID |
| `AZURE_REDIRECT_URI` | For SSO | App URL (e.g., `https://slideguide.university.edu`) |

## Export Formats

| Format | Use Case |
|--------|----------|
| Word (.docx) | Print-ready handouts |
| PDF | Digital distribution |
| HTML | Web viewing, email |
| Canvas QTI (.zip) | Import into Canvas LMS as a quiz |

## Project Structure

```
src/                Application code
  app.py              Main Streamlit UI
  ai.py               AI API calls and prompt logic
  auth.py             Azure Entra ID authentication
  cache.py            File and slide caching
  questions.py        Question types and CSV persistence
  usage_logger.py     Privacy-respecting usage logging
  export_*.py         Word, PDF, HTML, Canvas QTI export
Dockerfile          Production container image
docker-compose.yml  One-command deployment
docs/               Deployment guide and design docs
infra/              Azure Bicep infrastructure-as-code
```

---

## Development Transparency

This project was built with AI pair programming tools:

- **[Anthropic Claude Code](https://claude.com/claude-code)** (Claude Opus 4.6) — Primary development assistant for architecture planning, code generation, Docker/Azure configuration, and documentation. Plugins used:
  - *superpowers* — Structured workflows for planning, test-driven development, and code review
  - *pr-review-toolkit* — Automated code review and quality checks
  - *serena* — Codebase-aware code intelligence
  - *security-guidance* — Security vulnerability scanning
  - *code-simplifier* — Post-implementation cleanup and refactoring
  - *commit-commands* — Git workflow automation

- **[Mistral Vibe Code](https://docs.mistral.ai/capabilities/vibe-coding/)** — Used as a second pair of eyes to review and sanity-check Claude's output, not as a primary development tool

All AI-generated code was reviewed, tested, and approved by a human before being committed. Additional review and support from my husband, an actual programmer/computer scientist — who remains skeptical of "vibe coding" but serves as the project's de facto code reviewer and patient, live-in programming teacher.
