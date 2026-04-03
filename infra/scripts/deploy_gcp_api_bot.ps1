param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [Parameter(Mandatory = $false)]
    [string]$Region = "asia-southeast1",

    [Parameter(Mandatory = $false)]
    [string]$Repository = "steamweb",

    [Parameter(Mandatory = $false)]
    [string]$ApiServiceName = "steamweb-api",

    [Parameter(Mandatory = $false)]
    [string]$BotServiceName = "steamweb-bot",

    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,

    [Parameter(Mandatory = $true)]
    [string]$BotServiceToken,

    [Parameter(Mandatory = $true)]
    [string]$DiscordBotToken,

    [Parameter(Mandatory = $true)]
    [string]$DiscordClientId,

    [Parameter(Mandatory = $false)]
    [string]$DailyDigestChannelId = "",

    [Parameter(Mandatory = $false)]
    [string]$DailyDigestHourUtc = "8",

    [Parameter(Mandatory = $false)]
    [string]$DailyDigestMinuteUtc = "0",

    [Parameter(Mandatory = $false)]
    [string]$DailyDigestEnabled = "true",

    [Parameter(Mandatory = $false)]
    [string]$DiscordGuildId = "",

    [Parameter(Mandatory = $false)]
    [string]$SteamRedirectUri = "",

    [Parameter(Mandatory = $false)]
    [string]$SteamWebApiKey = "",

    [Parameter(Mandatory = $false)]
    [string]$ApiMinInstances = "0",

    [Parameter(Mandatory = $false)]
    [string]$ApiMaxInstances = "5",

    [Parameter(Mandatory = $false)]
    [string]$BotMinInstances = "1",

    [Parameter(Mandatory = $false)]
    [string]$BotMaxInstances = "1",

    [Parameter(Mandatory = $false)]
    [string]$DatabaseUrlSecret = "steamweb-database-url",

    [Parameter(Mandatory = $false)]
    [string]$BotServiceTokenSecret = "steamweb-bot-service-token",

    [Parameter(Mandatory = $false)]
    [string]$DiscordBotTokenSecret = "steamweb-discord-bot-token",

    [Parameter(Mandatory = $false)]
    [string]$DiscordClientIdSecret = "steamweb-discord-client-id",

    [Parameter(Mandatory = $false)]
    [string]$SteamWebApiKeySecret = "steamweb-steam-web-api-key"
)

$ErrorActionPreference = "Stop"

$ApiImage = "$Region-docker.pkg.dev/$ProjectId/$Repository/api:latest"
$BotImage = "$Region-docker.pkg.dev/$ProjectId/$Repository/bot:latest"
$ProjectNumber = gcloud projects describe $ProjectId --format "value(projectNumber)"
$RuntimeServiceAccount = "$ProjectNumber-compute@developer.gserviceaccount.com"

function Set-SecretValue {
    param(
        [string]$Name,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }

    $exists = gcloud secrets list --project $ProjectId --filter "name:$Name" --format "value(name)"
    if (-not $exists) {
        gcloud secrets create $Name --replication-policy=automatic --project $ProjectId | Out-Null
    }

    $Value | gcloud secrets versions add $Name --data-file=- --project $ProjectId | Out-Null
}

Write-Host "[1/9] Configure project and required APIs"
gcloud config set project $ProjectId | Out-Null
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com iam.googleapis.com secretmanager.googleapis.com | Out-Null

Write-Host "[2/9] Ensure Artifact Registry repository exists"
$repoCheck = gcloud artifacts repositories list --location $Region --filter "name~$Repository" --format "value(name)"
if (-not $repoCheck) {
    gcloud artifacts repositories create $Repository --repository-format docker --location $Region --description "Steamweb container images"
}

Write-Host "[3/9] Build and push API/Bot images"
$CloudBuildConfigPath = "infra/cloudbuild.api-bot.generated.yaml"
@"
steps:
- name: gcr.io/cloud-builders/docker
  args:
  - build
  - -f
  - infra/docker/api.Dockerfile
  - -t
  - $ApiImage
  - .
- name: gcr.io/cloud-builders/docker
  args:
  - build
  - -f
  - infra/docker/bot.Dockerfile
  - -t
  - $BotImage
  - .
images:
- $ApiImage
- $BotImage
"@ | Set-Content -Path $CloudBuildConfigPath

gcloud builds submit . --config $CloudBuildConfigPath

Write-Host "[4/9] Upsert Secret Manager values"
Set-SecretValue -Name $DatabaseUrlSecret -Value $DatabaseUrl
Set-SecretValue -Name $BotServiceTokenSecret -Value $BotServiceToken
Set-SecretValue -Name $DiscordBotTokenSecret -Value $DiscordBotToken
Set-SecretValue -Name $DiscordClientIdSecret -Value $DiscordClientId
Set-SecretValue -Name $SteamWebApiKeySecret -Value $SteamWebApiKey

Write-Host "[5/9] Grant runtime secret access"
gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$RuntimeServiceAccount" --role "roles/secretmanager.secretAccessor" | Out-Null

Write-Host "[6/9] Deploy API service"
$apiSecretMappings = @(
    "DATABASE_URL=${DatabaseUrlSecret}:latest",
    "BOT_SERVICE_TOKEN=${BotServiceTokenSecret}:latest"
)
if (-not [string]::IsNullOrWhiteSpace($SteamWebApiKey)) {
    $apiSecretMappings += "STEAM_WEB_API_KEY=${SteamWebApiKeySecret}:latest"
}
$apiSetSecretsArg = $apiSecretMappings -join ","

gcloud run deploy $ApiServiceName `
  --region $Region `
  --image $ApiImage `
  --allow-unauthenticated `
  --min-instances $ApiMinInstances `
  --max-instances $ApiMaxInstances `
  --cpu 1 `
  --memory 1Gi `
  --set-secrets $apiSetSecretsArg `
  --set-env-vars "STEAM_VERIFY_OPENID=true"

$ApiUrl = (gcloud run services describe $ApiServiceName --region $Region --format "value(status.url)").TrimEnd('/')
if ([string]::IsNullOrWhiteSpace($ApiUrl)) {
        throw "API deployment failed or service URL is empty. Check Cloud Run revision logs."
}
Write-Host "API URL: $ApiUrl"

Write-Host "[7/9] Deploy Bot service (always-on)"
$resolvedSteamRedirect = $SteamRedirectUri
if ([string]::IsNullOrWhiteSpace($resolvedSteamRedirect)) {
    $resolvedSteamRedirect = "$ApiUrl/api/v1/auth/steam/callback"
}

$botSecretMappings = @(
    "DISCORD_BOT_TOKEN=${DiscordBotTokenSecret}:latest",
    "DISCORD_CLIENT_ID=${DiscordClientIdSecret}:latest",
    "BOT_SERVICE_TOKEN=${BotServiceTokenSecret}:latest"
)
$botSetSecretsArg = $botSecretMappings -join ","

$botEnvParts = @(
    "BACKEND_BASE_URL=$ApiUrl/api/v1",
    "PUBLIC_API_BASE_URL=$ApiUrl",
    "STEAM_REDIRECT_URI=$resolvedSteamRedirect",
    "DAILY_DIGEST_ENABLED=$DailyDigestEnabled",
    "DAILY_DIGEST_HOUR_UTC=$DailyDigestHourUtc",
    "DAILY_DIGEST_MINUTE_UTC=$DailyDigestMinuteUtc",
    "ENABLE_HEALTH_SERVER=true"
)
if (-not [string]::IsNullOrWhiteSpace($DailyDigestChannelId)) {
    $botEnvParts += "DAILY_DIGEST_CHANNEL_ID=$DailyDigestChannelId"
}
if (-not [string]::IsNullOrWhiteSpace($DiscordGuildId)) {
    $botEnvParts += "DISCORD_GUILD_ID=$DiscordGuildId"
}
$botSetEnvArg = $botEnvParts -join ","

gcloud run deploy $BotServiceName `
  --region $Region `
  --image $BotImage `
  --allow-unauthenticated `
  --min-instances $BotMinInstances `
  --max-instances $BotMaxInstances `
  --cpu 1 `
  --memory 1Gi `
  --concurrency 1 `
  --no-cpu-throttling `
  --set-secrets $botSetSecretsArg `
  --set-env-vars $botSetEnvArg

$BotUrl = (gcloud run services describe $BotServiceName --region $Region --format "value(status.url)").TrimEnd('/')
Write-Host "Bot URL: $BotUrl"

Write-Host "[8/9] Smoke checks"
Invoke-WebRequest -Uri "$ApiUrl/health" -UseBasicParsing | Out-Null
Invoke-WebRequest -Uri "$BotUrl/health" -UseBasicParsing | Out-Null

Write-Host "[9/9] Done"
Write-Host "API is running 24/7 based on incoming traffic and min instances setting."
Write-Host "Bot is pinned always-on with min-instances=$BotMinInstances and no CPU throttling."
Write-Host "If you need daily pipeline too, run infra/scripts/deploy_gcp_daily_ingest.ps1 separately."
