param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [Parameter(Mandatory = $false)]
    [string]$Region = "asia-southeast1",

    [Parameter(Mandatory = $false)]
    [string]$JobName = "steamweb-daily-ingest",

    [Parameter(Mandatory = $false)]
    [string]$Repository = "steamweb",

    [Parameter(Mandatory = $false)]
    [string]$ImageName = "daily-ingest",

    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,

    [Parameter(Mandatory = $false)]
    [string]$YoutubeApiKey = "",

    [Parameter(Mandatory = $false)]
    [string]$RedditUserAgent = "steamweb-bot/1.0",

    [Parameter(Mandatory = $false)]
    [string]$SteamDbUserAgent = "steamweb-bot/1.0",

    [Parameter(Mandatory = $false)]
    [string]$Schedule = "0 2 * * *",

    [Parameter(Mandatory = $false)]
    [string]$SchedulerLocation = "asia-southeast1",

    [Parameter(Mandatory = $false)]
    [string]$SchedulerSaName = "steamweb-scheduler",

    [Parameter(Mandatory = $false)]
    [string]$Timezone = "Etc/UTC"

    ,
    [Parameter(Mandatory = $false)]
    [string]$DatabaseUrlSecret = "steamweb-database-url"

    [Parameter(Mandatory = $false)]
    [string]$YoutubeApiKeySecret = "steamweb-youtube-api-key"

    [Parameter(Mandatory = $false)]
    [string]$RedditUserAgentSecret = "steamweb-reddit-user-agent"

    [Parameter(Mandatory = $false)]
    [string]$SteamDbUserAgentSecret = "steamweb-steamdb-user-agent"
)

$ErrorActionPreference = "Stop"

$ImageUri = "$Region-docker.pkg.dev/$ProjectId/$Repository/$ImageName:latest"
$SchedulerSaEmail = "$SchedulerSaName@$ProjectId.iam.gserviceaccount.com"
$SchedulerJobName = "$JobName-trigger"
$RunJobUri = "https://run.googleapis.com/v2/projects/$ProjectId/locations/$Region/jobs/$JobName:run"
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

    $exists = gcloud secrets describe $Name --project $ProjectId --format "value(name)" 2>$null
    if (-not $exists) {
        gcloud secrets create $Name --replication-policy=automatic --project $ProjectId | Out-Null
    }

    $Value | gcloud secrets versions add $Name --data-file=- --project $ProjectId | Out-Null
}

Write-Host "[1/8] Configure gcloud project"
gcloud config set project $ProjectId | Out-Null

Write-Host "[2/8] Enable required APIs"
gcloud services enable run.googleapis.com cloudscheduler.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com iam.googleapis.com secretmanager.googleapis.com | Out-Null

Write-Host "[3/8] Ensure Artifact Registry repository exists"
$repoCheck = gcloud artifacts repositories list --location $Region --filter "name~$Repository" --format "value(name)"
if (-not $repoCheck) {
    gcloud artifacts repositories create $Repository --repository-format docker --location $Region --description "Steamweb container images"
}

Write-Host "[4/8] Build and push daily-ingest image"
$CloudBuildConfigPath = "infra/cloudbuild.ingestor.generated.yaml"
@"
steps:
- name: gcr.io/cloud-builders/docker
  args:
  - build
  - -f
  - infra/docker/ingestor.Dockerfile
  - -t
  - $ImageUri
  - .
images:
- $ImageUri
"@ | Set-Content -Path $CloudBuildConfigPath

gcloud builds submit . --config $CloudBuildConfigPath

Write-Host "[5/8] Deploy/Update Cloud Run Job"
# Upsert secret values from provided parameters.
Set-SecretValue -Name $DatabaseUrlSecret -Value $DatabaseUrl
Set-SecretValue -Name $YoutubeApiKeySecret -Value $YoutubeApiKey
Set-SecretValue -Name $RedditUserAgentSecret -Value $RedditUserAgent
Set-SecretValue -Name $SteamDbUserAgentSecret -Value $SteamDbUserAgent

# Ensure runtime identity can read secrets.
gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$RuntimeServiceAccount" --role "roles/secretmanager.secretAccessor" | Out-Null

$secretMappings = @(
    "DATABASE_URL=$DatabaseUrlSecret:latest",
    "REDDIT_USER_AGENT=$RedditUserAgentSecret:latest",
    "STEAMDB_USER_AGENT=$SteamDbUserAgentSecret:latest"
)
if (-not [string]::IsNullOrWhiteSpace($YoutubeApiKey)) {
    $secretMappings += "YOUTUBE_API_KEY=$YoutubeApiKeySecret:latest"
}

$setSecretsArg = $secretMappings -join ","

$jobExists = gcloud run jobs list --region $Region --format "value(name)" --filter "name~$JobName"
if (-not $jobExists) {
    gcloud run jobs create $JobName --region $Region --image $ImageUri --max-retries 1 --task-timeout 1800 --memory 1Gi --cpu 1 --set-secrets $setSecretsArg
} else {
    gcloud run jobs update $JobName --region $Region --image $ImageUri --max-retries 1 --task-timeout 1800 --memory 1Gi --cpu 1 --clear-env-vars --set-secrets $setSecretsArg
}

Write-Host "[6/8] Create scheduler service account if missing"
$saExists = gcloud iam service-accounts list --filter "email:$SchedulerSaEmail" --format "value(email)"
if (-not $saExists) {
    gcloud iam service-accounts create $SchedulerSaName --display-name "Steamweb scheduler invoker"
}

Write-Host "[7/8] Grant permissions to run Cloud Run Job"
gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$SchedulerSaEmail" --role "roles/run.developer" | Out-Null

Write-Host "[8/8] Create or update Cloud Scheduler trigger"
$existingScheduler = gcloud scheduler jobs list --location $SchedulerLocation --filter "name~$SchedulerJobName" --format "value(name)"
if (-not $existingScheduler) {
    gcloud scheduler jobs create http $SchedulerJobName --location $SchedulerLocation --schedule $Schedule --time-zone $Timezone --uri $RunJobUri --http-method POST --oauth-service-account-email $SchedulerSaEmail --oauth-token-scope "https://www.googleapis.com/auth/cloud-platform"
} else {
    gcloud scheduler jobs update http $SchedulerJobName --location $SchedulerLocation --schedule $Schedule --time-zone $Timezone --uri $RunJobUri --http-method POST --oauth-service-account-email $SchedulerSaEmail --oauth-token-scope "https://www.googleapis.com/auth/cloud-platform"
}

Write-Host "Done. Daily Cloud Scheduler trigger is configured."
Write-Host "Manual test command: gcloud run jobs execute $JobName --region $Region --wait"
