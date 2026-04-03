# GitHub CI/CD To Cloud Run

This workflow auto-deploys API, Bot, and Daily Ingest image updates when code is pushed to `main`.

Workflow file:
- `.github/workflows/deploy-cloudrun.yml`

## 1. GitHub Repository Variables

Add these Repository Variables (`Settings` -> `Secrets and variables` -> `Actions` -> `Variables`):

- `GCP_PROJECT_ID` (example: `steam-491906`)
- `GCP_REGION` (example: `asia-southeast1`)
- `AR_REPOSITORY` (example: `steamweb`)
- `API_SERVICE_NAME` (example: `steamweb-api`)
- `BOT_SERVICE_NAME` (example: `steamweb-bot`)
- `INGEST_JOB_NAME` (example: `steamweb-daily-ingest`)

## 2. GitHub Repository Secrets

Add these Repository Secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT_EMAIL`

## 3. GCP IAM Requirements (for the GitHub deploy service account)

Grant these roles to the service account in `GCP_SERVICE_ACCOUNT_EMAIL`:

- `roles/run.admin`
- `roles/artifactregistry.writer`
- `roles/iam.serviceAccountUser`

If this account also needs to read/modify scheduler or secrets in future steps, add:

- `roles/cloudscheduler.admin` (optional)
- `roles/secretmanager.admin` (optional)

## 4. Artifact Registry Prerequisite

Ensure Docker repository already exists:

- `${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${AR_REPOSITORY}`

## 5. How It Works

On every push to `main`, GitHub Actions will:

1. Authenticate to GCP via Workload Identity Federation.
2. Build and push 3 images tagged by commit SHA:
- API image from `infra/docker/api.Dockerfile`
- Bot image from `infra/docker/bot.Dockerfile`
- Ingest image from `infra/docker/ingestor.Dockerfile`
3. Deploy Cloud Run services:
- `${API_SERVICE_NAME}`
- `${BOT_SERVICE_NAME}`
4. Update Cloud Run Job image:
- `${INGEST_JOB_NAME}`

The workflow keeps existing service/job env vars and secrets intact because deploy/update only changes image.

## 6. Manual Trigger

You can run deployment manually from GitHub:

- `Actions` -> `Deploy To Cloud Run` -> `Run workflow`
