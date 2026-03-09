########################################################################
# Deploy Alert Call Service to Azure Container Instance
# Run this script once to set everything up
# Prerequisites: Azure CLI installed and logged in (az login)
########################################################################

# --- CONFIGURATION (edit these) ---
$RESOURCE_GROUP = "alert-call-rg"
$LOCATION = "israelcentral"         # Israel region - required for Oref API access
$CONTAINER_NAME = "alert-call"
$REGISTRY_NAME = "alertcallregistry"  # Must be globally unique, lowercase, no dashes

# Your .env values (same as local) - FILL THESE IN!
$TWILIO_ACCOUNT_SID = "YOUR_TWILIO_ACCOUNT_SID"
$TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
$TWILIO_PHONE_NUMBER = "+1XXXXXXXXXX"       # Your Twilio phone number
$MY_PHONE_NUMBER = "+972XXXXXXXXX"          # Your personal phone number
$MONITORED_AREAS = "תל אביב"               # Areas to monitor (Hebrew)

# --- STEP 1: Create Resource Group ---
Write-Host "📦 Creating resource group..." -ForegroundColor Cyan
az group create --name $RESOURCE_GROUP --location $LOCATION

# --- STEP 2: Create Azure Container Registry ---
Write-Host "🏗️ Creating container registry..." -ForegroundColor Cyan
az acr create --resource-group $RESOURCE_GROUP --name $REGISTRY_NAME --sku Basic --admin-enabled true

# --- STEP 3: Build and push Docker image ---
Write-Host "🐳 Building and pushing Docker image..." -ForegroundColor Cyan
az acr build --registry $REGISTRY_NAME --image alert-call:latest .

# --- STEP 4: Get registry credentials ---
$ACR_SERVER = az acr show --name $REGISTRY_NAME --query loginServer --output tsv
$ACR_USERNAME = az acr credential show --name $REGISTRY_NAME --query username --output tsv
$ACR_PASSWORD = az acr credential show --name $REGISTRY_NAME --query "passwords[0].value" --output tsv

# --- STEP 5: Deploy to Azure Container Instance ---
Write-Host "🚀 Deploying container..." -ForegroundColor Cyan
az container create `
    --resource-group $RESOURCE_GROUP `
    --name $CONTAINER_NAME `
    --image "${ACR_SERVER}/alert-call:latest" `
    --registry-login-server $ACR_SERVER `
    --registry-username $ACR_USERNAME `
    --registry-password $ACR_PASSWORD `
    --cpu 0.25 `
    --memory 0.5 `
    --os-type Linux `
    --restart-policy Always `
    --ports 8080 `
    --dns-name-label $CONTAINER_NAME `
    --environment-variables `
        TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID `
        TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN `
        TWILIO_PHONE_NUMBER=$TWILIO_PHONE_NUMBER `
        MY_PHONE_NUMBER=$MY_PHONE_NUMBER `
        MONITORED_AREAS=$MONITORED_AREAS `
        POLL_INTERVAL_SECONDS=2 `
        ALERT_COOLDOWN_SECONDS=60 `
        WEB_PORT=8080

# --- Get the public URL ---
$FQDN = az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.fqdn --output tsv
$IP = az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.ip --output tsv

Write-Host ""
Write-Host "✅ Deployed! The service is now running on Azure 24/7" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Web Interface: http://${FQDN}:8080" -ForegroundColor Cyan
Write-Host "   (or http://${IP}:8080)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  View logs:     az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --follow"
Write-Host "  Check status:  az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query instanceView.state"
Write-Host "  Stop:          az container stop --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
Write-Host "  Start:         az container start --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
Write-Host "  Delete all:    az group delete --name $RESOURCE_GROUP --yes"
