# Deploying Slide Guide Generator to Azure App Service

## Prerequisites

- An Azure account (your organization likely has one — check with IT)
- Azure CLI installed: `winget install Microsoft.AzureCLI` (Windows) or `brew install azure-cli` (macOS)
- Logged in: `az login`

## Quick Start (5 minutes)

### 1. Create the Azure resources

Replace `slide-guide` with your preferred name. The app name must be globally
unique — your URL will be `https://<name>.azurewebsites.net`.

```bash
# Create a resource group (skip if you already have one)
az group create --name SlideGuide --location eastus

# Create an App Service plan (B1 is ~$13/month, plenty for a small team)
az appservice plan create \
  --name slide-guide-plan \
  --resource-group SlideGuide \
  --sku B1 \
  --is-linux

# Create the web app (Python 3.11 — matches the devcontainer)
az webapp create \
  --name slide-guide \
  --resource-group SlideGuide \
  --plan slide-guide-plan \
  --runtime "PYTHON:3.11" \
  --startup-file "bash startup.sh"
```

> **Note:** We use Python 3.11 because that's what the devcontainer uses and
> what the dependencies are tested against. Python 3.12+ also works.

### 2. Set environment variables (optional)

This app does **not** require server-side API keys — users enter their own
Anthropic or Mistral key in the login screen. However, you can set a default
key so users don't have to:

Go to [Azure Portal](https://portal.azure.com) > your App Service >
**Configuration** > **Application settings**, and add:

| Name | Value | Required? |
|------|-------|-----------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Optional — only if you want a default key |

If set, the app can fall back to this key when no user key is provided (requires
a small code change to `ai.py` — see "Optional: Server-Side Default Key" below).

### 3. Deploy the code

From the **slide-guide-generator** project directory:

```bash
az webapp up \
  --name slide-guide \
  --resource-group SlideGuide \
  --runtime "PYTHON:3.11"
```

Or use zip deploy:

```bash
az webapp deploy \
  --resource-group SlideGuide \
  --name slide-guide \
  --src-path . \
  --type zip
```

The startup script (`startup.sh`) automatically installs `poppler-utils`
(the system library needed to convert PDFs to images) and launches Streamlit.

### 4. Restrict access to your organization (optional but recommended)

In the Azure Portal:

1. Go to your App Service > **Authentication**
2. Click **Add identity provider**
3. Choose **Microsoft**
4. Set "Restrict access" to **Require authentication**
5. Under "Tenant type," select **Workforce** (current tenant)
6. Save

This makes it so only people with your org's Microsoft accounts can access
the app. No code changes required.

## Updating After Code Changes

```bash
az webapp up \
  --name slide-guide \
  --resource-group SlideGuide \
  --runtime "PYTHON:3.11"
```

## How It Works

- Users visit the app and enter their own Anthropic or Mistral API key
- They upload a PDF presentation, the app converts slides to images using
  `poppler-utils` / `pdf2image`
- AI analyzes each slide and generates study guide questions
- Users select and export questions as DOCX or Canvas QTI

Because users provide their own API keys, there's no server-side key
management needed (unlike the Syllabi Trawl app).

## Troubleshooting

**View logs:**
```bash
az webapp log tail --name slide-guide --resource-group SlideGuide
```

**SSH into the container:**
```bash
az webapp ssh --name slide-guide --resource-group SlideGuide
```

**Common issues:**

- **"poppler not installed" error:** The startup script installs it, but if the
  container restarts, it reinstalls each time. This is normal for B1 plans. If it
  takes too long, consider using a custom Docker container with poppler pre-installed.
- **App won't start:** Check logs. Most common cause is a missing dependency or
  a startup timeout. The default timeout is 230 seconds — poppler install +
  Streamlit boot should fit within that.
- **Large PDFs fail:** High-DPI conversion is memory-intensive. B1 has 1.75 GB RAM.
  For very large PDFs (50+ slides at 300 DPI), you may need a B2 or B3 plan.
- **`pystray` import error:** This shouldn't happen — `tray.py` is only used for
  desktop deployments and isn't imported by `app.py`. If you see this error,
  something changed; check that `app.py` doesn't import `tray`.
