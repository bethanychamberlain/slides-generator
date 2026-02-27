# Dockerization Notes — Slide Guide Generator

**Date:** 2026-02-27

## Current Setup

The app currently runs via `start-beta.sh`, which launches Streamlit + an Azure Dev Tunnel from Bethany's machine. The goal is to hand hosting to IT using Docker so the app runs on org infrastructure.

## Application Profile

| Layer | Details |
|-------|---------|
| **Framework** | Streamlit (Python 3.11+) |
| **System dependency** | `poppler-utils` (PDF-to-image conversion) |
| **Python packages** | `requirements.txt` — streamlit, anthropic, mistralai, pdf2image, pypdfium2, python-docx, fpdf2, pillow, python-dotenv |
| **External API calls** | `api.anthropic.com` and/or `api.mistral.ai` (outbound HTTPS only) |
| **Database** | None |
| **Persistent storage required** | None (optional for caching) |

## API Key Management

### Recommended: Environment variable

Pass `ANTHROPIC_API_KEY` as a container environment variable. The key is loaded by `python-dotenv` and held in process memory only — never written to disk.

```bash
docker run -e ANTHROPIC_API_KEY=sk-ant-... slide-guide
```

Or via `.env` file on the server with `docker-compose.yml`.

### Alternative: Azure Key Vault

Only needed if:
- Multiple apps share the same secret and IT wants single-point rotation
- Compliance/audit policy requires it
- IT already uses Key Vault and prefers to manage all secrets there

**Not a technical requirement from the app.** Environment variable works with zero code changes.

### Faculty profiles (`users.json`)

Contains faculty names, simple passwords, and per-user API keys. Should be mounted at runtime, not baked into the image:

```bash
docker run -v /path/to/users.json:/app/users.json:ro slide-guide
```

## Data Flow and Storage

### Data on the server (inside the Docker container)

| Data | Path in container | Lifetime | User content? |
|------|--------------------|----------|---------------|
| Rendered slide images | `/app/working_images/<session_id>/` | **Temporary** — cleaned up when user uploads new PDF or clears cache | Yes |
| Analysis cache (AI-generated questions by image hash) | `/app/analysis_cache/` | Persistent within container, **lost on restart** unless volume-mounted | Yes |
| Questions history CSV | `/app/questions_history.csv` | Append-only log, **lost on restart** unless volume-mounted | Yes (questions + source filenames) |
| `users.json` | `/app/users.json` | Persistent if volume-mounted | Yes (names, passwords, API keys) |

### Data sent to third-party AI providers

| What | Destination | Retention |
|------|-------------|-----------|
| Slide images (base64 JPEG) | Anthropic or Mistral API | Not retained — API terms state no training on inputs, no retention beyond request |
| AI-generated questions | Response from API, cached locally | N/A |

### Data on the user's machine (browser only)

| What | How |
|------|-----|
| Streamlit session state (selections, UI choices) | In-memory, lost when tab closes |
| Downloaded exports (DOCX, PDF, HTML, QTI zip) | Standard browser download to local filesystem |

### Privacy consideration

Uploaded PDFs are rendered as images and sent to Anthropic/Mistral. Faculty should know slide content leaves the org network. Mistral's EU data residency option is available in the app if this matters.

## Dockerfile

```dockerfile
FROM python:3.11-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends poppler-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ai.py cache.py questions.py \
     export_docx.py export_pdf.py export_html.py export_qti.py \
     icon.png ./

ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8501

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
```

**Why `python:3.11-slim-bookworm`:** Matches the devcontainer base (Debian Bookworm, Python 3.11) at ~150MB vs ~1GB for full image. Baking in `poppler-utils` eliminates the reinstall-on-restart issue noted in `DEPLOY_AZURE.md`.

## .dockerignore

```
venv/
__pycache__/
*.pyc
.env
users.json
working_images/
analysis_cache/
questions_history.csv
.git/
.claude/
.serena/
.devcontainer/
docs/
Testing logs from bethany/
*.txt
!requirements.txt
!packages.txt
```

## docker-compose.yml

```yaml
services:
  slide-guide:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./users.json:/app/users.json:ro  # optional — faculty profiles
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}  # from .env or host env
    restart: unless-stopped
```

## Options / Decisions for IT

### 1. Persistent caching (optional)

If analysis cache and question history should survive container restarts:

```yaml
volumes:
  - slide-guide-cache:/app/analysis_cache
  - ./questions_history.csv:/app/questions_history.csv
```

Pro: Repeat uploads skip AI calls (saves time and API cost).
Con: Cached data accumulates indefinitely; needs occasional cleanup.

### 2. HTTPS / reverse proxy

Streamlit serves on port 8501 over HTTP. For production, IT should put a reverse proxy (nginx, Caddy, or Traefik) in front for TLS termination. If the server is internal-only behind a VPN, plain HTTP may be acceptable per org policy.

### 3. Resource sizing

| Spec | Minimum | Recommended |
|------|---------|-------------|
| RAM | 512 MB | 1–2 GB (large PDFs at 300 DPI spike memory) |
| CPU | 1 core | 2 cores (PDF rendering is CPU-bound) |
| Disk | Minimal | A few GB if caching is enabled |

### 4. Access control

The app has its own login screen (faculty profiles or manual API key entry). For org-level access control, IT can:
- Restrict network access (VPN / firewall rules)
- Add an auth proxy (e.g., OAuth2 Proxy with org SSO) in front of the container
- Use Azure AD authentication if deploying to Azure (as described in `DEPLOY_AZURE.md`)

### 5. Updates

```bash
git pull && docker compose build && docker compose up -d
```

No zero-downtime setup needed for an internal tool — the rebuild takes ~30 seconds.

## No Code Changes Required

The app already:
- Listens on `0.0.0.0` (via `--server.address`)
- Runs headless (via `--server.headless`)
- Handles API keys via environment variables (`python-dotenv`)
- Uses relative paths (`Path(__file__).parent`)
