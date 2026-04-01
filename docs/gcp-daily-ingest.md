# GCP Daily Steam Crawl (Cloud Run Job)

This guide runs the data pipeline daily on GCP without keeping any VM alive.

## Architecture

1. Build container with [infra/docker/ingestor.Dockerfile](../infra/docker/ingestor.Dockerfile).
2. Deploy Cloud Run Job that runs `python -m jobs.run_daily_update`.
3. Cloud Scheduler triggers the job once per day.

## Prerequisites

1. Install and login to `gcloud` CLI.
2. Ensure your database is reachable from Cloud Run (Supabase works directly via `DATABASE_URL`).
3. Run migration [database/migrations/004_steamdb_data.sql](../database/migrations/004_steamdb_data.sql) first.

## One-command Deployment

From repo root, run PowerShell:

```powershell
./infra/scripts/deploy_gcp_daily_ingest.ps1 `
  -ProjectId "YOUR_GCP_PROJECT" `
  -Region "asia-southeast1" `
  -DatabaseUrl "postgresql://..." `
  -YoutubeApiKey "YOUR_YOUTUBE_KEY" `
  -RedditUserAgent "steamweb-bot/1.0" `
  -Schedule "0 2 * * *" `
  -Timezone "Etc/UTC"
```

## Verify

1. Manual run:

```powershell
gcloud run jobs execute steamweb-daily-ingest --region asia-southeast1 --wait
```

2. Check execution logs:

```powershell
gcloud run jobs executions list --job steamweb-daily-ingest --region asia-southeast1
```

## Notes

1. Current SteamDB HTML scraping may return 403. The ingestor automatically falls back to official Steam endpoints and still stores trending/hot snapshots.
2. If you use secret manager later, replace `--set-env-vars` with `--set-secrets` in [infra/scripts/deploy_gcp_daily_ingest.ps1](../infra/scripts/deploy_gcp_daily_ingest.ps1).
