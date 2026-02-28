# Slide Guide Generator — Deployment Guide

## Overview

Slide Guide Generator is a Streamlit web application that converts PDF lecture slides into AI-generated student study guides. Faculty authenticate via Microsoft Entra ID (Azure AD), upload PDFs, and receive structured question sets they can export as Word, PDF, HTML, or Canvas LMS formats.

## Architecture

```
  Faculty Browser
       │
       │ HTTPS (TLS terminated by reverse proxy or Azure ingress)
       │
  ┌────▼──────────────────────────────────────────────────┐
  │              Docker Container (:8501)                   │
  │                                                         │
  │  Streamlit App ──► Entra ID (MSAL) ──► Microsoft SSO   │
  │       │                                                 │
  │       ▼                                                 │
  │  Anthropic API (outbound HTTPS to api.anthropic.com)   │
  │                                                         │
  │  Persistent Volume (/data):                            │
  │    ├── analysis_cache/   (AI response cache)           │
  │    ├── usage_logs/       (token counts per user)       │
  │    └── questions_history.csv                           │
  └────────────────────────────────────────────────────────┘
```

### Data Flow

| Data | Direction | Destination | Retention |
|------|-----------|-------------|-----------|
| Slide images (JPEG) | Outbound | Anthropic API | Not retained (per API terms) |
| AI-generated questions | Inbound | Cached in `/data/analysis_cache/` | Until cache cleared |
| Usage logs | Internal | `/data/usage_logs/` | Monthly files, indefinite |
| Exported guides | Outbound | Faculty browser download | Not stored on server |

### Privacy

- Usage logs record **who** and **how many tokens** — never **what** was processed
- Slide content is sent to Anthropic's API but not retained beyond the request
- No student data is processed; only faculty lecture slides

## Prerequisites

1. **Docker** and **docker compose** (v2+)
2. **Azure Entra ID app registration** (see below)
3. **Anthropic API key** with sufficient quota

## Step 1: Azure Entra ID App Registration

This allows faculty to sign in with their university Microsoft accounts.

1. Go to [Azure Portal → Entra ID → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**
   - Name: `Slide Guide Generator`
   - Supported account types: **Single tenant** (this org only)
   - Redirect URI: **Web** → `https://your-domain.example.com` (or `http://localhost:8501` for testing)
3. After creation, note:
   - **Application (client) ID** → `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → `AZURE_TENANT_ID`
4. Go to **Certificates & secrets** → **New client secret**
   - Description: `slide-guide-prod`
   - Expiry: 24 months (set a calendar reminder to rotate)
   - Copy the **Value** → `AZURE_CLIENT_SECRET`
5. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated** → `User.Read`
   - Click **Grant admin consent** (requires admin role)

## Step 2: Configure Environment

Create a `.env` file on the server (never commit this):

```bash
# AI Provider
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Azure Entra ID
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_REDIRECT_URI=https://slideguide.youruniversity.edu
```

## Step 3: Deploy

```bash
git clone https://github.com/bethanychamberlain/slides-generator.git
cd slides-generator
# Place your .env file in this directory
docker compose up -d
```

The app will be available at `http://localhost:8501`.

## Step 4: HTTPS / Reverse Proxy

The container serves HTTP on port 8501. For production, place a TLS-terminating reverse proxy in front. Options:

- **Azure Container Apps**: Built-in HTTPS with custom domain
- **Azure App Service (container)**: Built-in HTTPS with custom domain
- **nginx / Caddy**: If hosting on a VM

Streamlit requires WebSocket support. Ensure your proxy passes `Upgrade` and `Connection` headers.

Example nginx snippet:

```nginx
location / {
    proxy_pass http://localhost:8501;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Step 5: Verify

1. Open the app URL in a browser
2. Click "Sign in with Microsoft"
3. Authenticate with an org account
4. Upload a test PDF and generate questions
5. Check usage logs: `docker compose exec slide-guide cat /data/usage_logs/usage-$(date +%Y-%m).jsonl`

## Resource Sizing

| Spec | Minimum (10 users) | Recommended (100 users) |
|------|---------------------|-------------------------|
| RAM | 512 MB | 2 GB |
| CPU | 1 core | 2 cores |
| Disk | 1 GB | 5 GB (with caching) |

PDF rendering at 300 DPI is CPU-bound and memory-intensive for large files (50+ pages). The container limits in `docker-compose.yml` are set to 2 GB / 2 cores.

## Updating

```bash
cd slides-generator
git pull
docker compose build
docker compose up -d
```

Persistent data in `/data` survives container rebuilds.

## Monitoring Usage

Usage logs are in `/data/usage_logs/` as monthly JSON Lines files:

```bash
# View current month's usage
docker compose exec slide-guide cat /data/usage_logs/usage-$(date +%Y-%m).jsonl

# Count tokens per user this month
docker compose exec slide-guide python -c "
import json
from collections import defaultdict
totals = defaultdict(int)
for line in open('/data/usage_logs/usage-$(date +%Y-%m).jsonl'):
    e = json.loads(line)
    totals[e['user']] += e['input_tokens'] + e['output_tokens']
for user, tokens in sorted(totals.items(), key=lambda x: -x[1]):
    print(f'{user}: {tokens:,} tokens')
"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Authentication failed" | Verify `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET` are correct. Check the redirect URI matches exactly. |
| "Sign in with Microsoft" button doesn't appear | Entra ID is not configured. Check all `AZURE_*` env vars are set. |
| Container exits immediately | Check logs: `docker compose logs slide-guide` |
| PDF upload fails | Large PDFs need more RAM. Increase memory limit in `docker-compose.yml`. |
| "API key not valid" | Verify `ANTHROPIC_API_KEY` in `.env`. |
