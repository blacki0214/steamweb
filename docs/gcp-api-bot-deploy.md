# GCP Deploy API + Discord Bot (24/24)

This guide deploys both API and Discord bot to Cloud Run so the bot can run continuously without your local machine.

## What It Deploys

1. `steamweb-api` as Cloud Run Service.
2. `steamweb-bot` as Cloud Run Service with:
- `min-instances=1`
- `max-instances=1`
- `--no-cpu-throttling`

This keeps a bot instance alive 24/24.

## Prerequisites

1. Install and authenticate `gcloud` CLI.
2. Have a reachable Postgres `DATABASE_URL`.
3. Have Discord bot credentials ready:
- `DISCORD_BOT_TOKEN`
- `DISCORD_CLIENT_ID`
- `BOT_SERVICE_TOKEN`
4. Run DB migrations before production deploy.

## One-Command Deployment

From repo root:

```powershell
./infra/scripts/deploy_gcp_api_bot.ps1 `
  -ProjectId "YOUR_GCP_PROJECT" `
  -Region "asia-southeast1" `
  -DatabaseUrl "postgresql://..." `
  -BotServiceToken "YOUR_BOT_SERVICE_TOKEN" `
  -DiscordBotToken "YOUR_DISCORD_BOT_TOKEN" `
  -DiscordClientId "YOUR_DISCORD_CLIENT_ID" `
  -DailyDigestChannelId "YOUR_DISCORD_CHANNEL_ID" `
  -DailyDigestHourUtc "8" `
  -DailyDigestMinuteUtc "0" `
  -DailyDigestEnabled "true"
```

Optional:

```powershell
  -DiscordGuildId "YOUR_TEST_GUILD_ID" `
  -SteamRedirectUri "https://your-web-domain/auth/steam/callback" `
  -SteamWebApiKey "YOUR_STEAM_WEB_API_KEY"
```

## Verify

1. API health:

```powershell
gcloud run services describe steamweb-api --region asia-southeast1 --format "value(status.url)"
```

Open `<API_URL>/health` and expect `{ "status": "ok" }`.

2. Bot health:

```powershell
gcloud run services describe steamweb-bot --region asia-southeast1 --format "value(status.url)"
```

Open `<BOT_URL>/health` and expect `{ "status": "ok" }`.

3. Check bot logs:

```powershell
gcloud run services logs read steamweb-bot --region asia-southeast1 --limit 100
```

## Security Notes

1. Deployment script stores credentials in Secret Manager and injects them via `--set-secrets`.
2. Rotate Discord tokens immediately if they were ever committed to local `.env` or shared logs.

## Daily Ingestion

This deploy does not include the scheduled data pipeline job.
For that, also run:

- [docs/gcp-daily-ingest.md](./gcp-daily-ingest.md)
