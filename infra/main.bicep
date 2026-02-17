// Slide Guide Generator — Azure Container Apps deployment
// Deploy with: az deployment group create -g <resource-group> -f main.bicep

@description('Name prefix for all resources')
param appName string = 'slideguide'

@description('Azure region')
param location string = resourceGroup().location

@description('Anthropic API key')
@secure()
param anthropicApiKey string

@description('Mistral API key (optional — for EU data residency)')
@secure()
param mistralApiKey string = ''

@description('Entra ID application (client) ID')
param azureClientId string

@description('Entra ID client secret')
@secure()
param azureClientSecret string

@description('Entra ID tenant ID')
param azureTenantId string

@description('Public URL for the app (used as OAuth redirect URI)')
param redirectUri string = ''

@description('Container image (from Docker Hub or ACR)')
param containerImage string = 'ghcr.io/bethanychamberlain/slide-guide:latest'

// --- Log Analytics Workspace (required by Container Apps) ---
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${appName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// --- Container Apps Environment ---
resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${appName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// --- Azure Files storage for persistent data ---
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${appName}data'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'slideguide-data'
  properties: {
    shareQuota: 5
  }
}

resource storageLink 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: containerAppEnv
  name: 'datavolume'
  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: fileShare.name
      accessMode: 'ReadWrite'
    }
  }
}

// --- Container App ---
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8501
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['*']
        }
      }
      secrets: [
        { name: 'anthropic-key', value: anthropicApiKey }
        { name: 'mistral-key', value: mistralApiKey }
        { name: 'azure-client-secret', value: azureClientSecret }
      ]
    }
    template: {
      containers: [
        {
          name: 'slide-guide'
          image: containerImage
          resources: {
            cpu: json('2.0')
            memory: '4Gi'
          }
          env: [
            { name: 'ANTHROPIC_API_KEY', secretRef: 'anthropic-key' }
            { name: 'MISTRAL_API_KEY', secretRef: 'mistral-key' }
            { name: 'AZURE_CLIENT_ID', value: azureClientId }
            { name: 'AZURE_CLIENT_SECRET', secretRef: 'azure-client-secret' }
            { name: 'AZURE_TENANT_ID', value: azureTenantId }
            { name: 'AZURE_REDIRECT_URI', value: redirectUri }
            { name: 'DATA_DIR', value: '/data' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                port: 8501
                path: '/_stcore/health'
              }
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
          volumeMounts: [
            {
              volumeName: 'data'
              mountPath: '/data'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'data'
          storageName: 'datavolume'
          storageType: 'AzureFile'
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

output appUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output resourceGroup string = resourceGroup().name
