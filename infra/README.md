# Infrastructure — For Humans

This folder contains Azure infrastructure-as-code (Bicep) to deploy Slide Guide Generator to Azure Container Apps.

## What This Creates

When you run the deployment command, Azure will create:

1. **Container Apps Environment**
2. **Container App** (the running instance)
3. **Storage Account + File Share** (persistent cache and usage logs)
4. **Log Analytics Workspace** (container logs)

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- An Azure subscription
- The Entra ID app registration completed (see [deployment guide](../docs/deployment-guide.md))
- An Anthropic API key

## Step-by-Step Deployment

### 1. Log in to Azure

```bash
az login
```

Sign in with your admin account when the browser opens.

### 2. Create a Resource Group

```bash
az group create --name slide-guide-rg --location eastus
```

(Change `eastus` to whatever region is closest to your users.)

### 3. Deploy

```bash
az deployment group create \
  --resource-group slide-guide-rg \
  --template-file main.bicep \
  --parameters \
    anthropicApiKey='sk-ant-your-key-here' \
    azureClientId='your-client-id' \
    azureClientSecret='your-client-secret' \
    azureTenantId='your-tenant-id'
```

This takes 2-5 minutes. When it finishes, it prints the app URL.

### 4. Set the Redirect URI

Copy the app URL from the output (something like `https://slideguide.bluewater-abc123.eastus.azurecontainerapps.io`).

Go to Azure Portal → Entra ID → App registrations → Slide Guide Generator → Authentication → Add the URL as a **Redirect URI**.

Then re-deploy with the redirect URI set:

```bash
az deployment group create \
  --resource-group slide-guide-rg \
  --template-file main.bicep \
  --parameters \
    anthropicApiKey='sk-ant-your-key-here' \
    azureClientId='your-client-id' \
    azureClientSecret='your-client-secret' \
    azureTenantId='your-tenant-id' \
    redirectUri='https://slideguide.bluewater-abc123.eastus.azurecontainerapps.io'
```

### 5. Test It

Open the URL in a browser. You should see the Microsoft sign-in button. Sign in with a university account and try uploading a PDF.

## Custom Domain

To use a nice URL like `slideguide.university.edu`:

1. In Azure Portal, go to your Container App → Custom domains
2. Add your domain and follow the DNS verification steps
3. Azure handles the TLS certificate automatically
4. Update `AZURE_REDIRECT_URI` to match the new domain

## Viewing Logs

```bash
# Stream live logs
az containerapp logs show \
  --name slideguide \
  --resource-group slide-guide-rg \
  --follow

# View usage logs (from inside the container)
az containerapp exec \
  --name slideguide \
  --resource-group slide-guide-rg \
  --command "cat /data/usage_logs/usage-$(date +%Y-%m).jsonl"
```

## Updating the App

When new code is pushed:

```bash
# Update the deployed image:
az containerapp update \
  --name slideguide \
  --resource-group slide-guide-rg \
  --image ghcr.io/bethanychamberlain/slide-guide:latest
```

## Tearing Down

To remove everything (this deletes all data!):

```bash
az group delete --name slide-guide-rg --yes
```
