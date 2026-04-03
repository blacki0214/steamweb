# Indie Game Discovery Platform

Personalized web platform for indie game discovery using Steam, YouTube, and Reddit data.

## Workspace Layout

- apps/web: React frontend (Vite + TypeScript)
- backend/api: FastAPI backend services
- backend/bot: Discord bot client for API contracts
- data-pipeline: ingestion and NLP processing jobs
- database: SQL init scripts, migrations, seeds
- ml: recommendation and semantic search modules
- infra: docker/compose and deployment scripts
- shared: shared contracts and constants
- docs: architecture and delivery docs

## Quick Start

1. Configure environment variables from `.env.example`.
2. Configure `DATABASE_URL` to your Supabase Postgres connection string.
3. Run backend API and web app via Docker Compose.
4. Run data ingestion jobs to populate tables.

### Docker Compose (Supabase)

- Default stack expects external Postgres (Supabase) via `DATABASE_URL` in `infra/compose/.env`.
- Start stack:
	- `cd infra/compose`
	- `docker compose up -d --build`

### Optional Local Postgres (for development)

- To run built-in `db` service instead of Supabase:
	- `cd infra/compose`
	- `docker compose --profile local-db up -d --build`

## Cloud Daily Ingestion

- GCP Cloud Run Job + Cloud Scheduler setup guide:
	- `docs/gcp-daily-ingest.md`

## Cloud API + Bot (24/24)

- GCP Cloud Run deployment guide for API and always-on Discord bot:
	- `docs/gcp-api-bot-deploy.md`
