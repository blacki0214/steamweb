# Indie Game Discovery Platform

Data-driven discovery platform for indie games powered by Steam, SteamDB, Reddit, and YouTube signals.

## Executive Summary

Players often discover games from fragmented sources and miss relevant indie titles.
This project centralizes discovery data, builds recommendation logic, and exposes the experience through:

- a React web application,
- a FastAPI backend,
- a Discord bot workflow.

## Core Capabilities

- Steam account connection via Discord `/login`.
- Personalized recommendations via `/nenchoigi` with multi-source context.
- Automated daily Steam digest plus admin-triggered `/digestnow`.
- Cloud-native runtime with API, bot, and ingestion jobs on GCP.

## Current Production Status

- API service deployed to Cloud Run.
- Discord bot deployed to Cloud Run (always-on configuration).
- Ingestion pipeline deployed as Cloud Run Job + Cloud Scheduler.
- GitHub Actions CI/CD configured for deploy on push to `main`.

## System Architecture

- Data Layer: Steam, SteamDB, Reddit, YouTube -> PostgreSQL.
- Processing Layer: ingestion, normalization, sentiment, ranking, semantic search.
- Experience Layer: React web app + Discord command flow.

See details in `docs/architecture.md`.

## Repository Structure

| Path | Description |
| --- | --- |
| `apps/web` | React frontend (Vite + TypeScript) |
| `backend/api` | FastAPI services and endpoints |
| `backend/bot` | Discord bot commands and schedulers |
| `data-pipeline` | Ingestion and NLP processing jobs |
| `database` | SQL init scripts, migrations, seed data |
| `ml` | Recommendation and semantic search modules |
| `infra` | Docker, compose, deployment scripts |
| `shared` | Shared contracts and constants |
| `docs` | Architecture, roadmap, deployment guides |

## Local Development

1. Configure environment values from `.env.example` files.
2. Set `DATABASE_URL` (Supabase Postgres is recommended).
3. Start services with Docker Compose.
4. Run ingest jobs to seed and refresh data.

### Docker Compose (Supabase)

```bash
cd infra/compose
docker compose up -d --build
```

### Docker Compose (Optional Local DB)

```bash
cd infra/compose
docker compose --profile local-db up -d --build
```

## Product Roadmap

### Phase 1: MVP Foundation
- [x] Steam metadata ingestion into Postgres.
- [x] Reddit + YouTube context ingestion.
- [x] FastAPI contracts and base recommendation logic.
- [x] Web application foundation.

### Phase 2: Discord Discovery Workflow
- [x] `/login` Steam account flow.
- [x] `/nenchoigi` recommendation flow.
- [x] Daily digest scheduler and `/digestnow` trigger.
- [x] Admin-only permission guard for `/digestnow`.

### Phase 3: Reliability and Operations
- [x] API and bot deployment on Cloud Run.
- [x] Ingestion deployment via Cloud Run Job + Scheduler.
- [x] GitHub CI/CD for build and deployment.
- [ ] End-to-end post-deploy smoke tests.
- [ ] Alerting for ingest and bot runtime failures.

### Phase 4: Recommendation Quality
- [ ] Stronger preference modeling and feedback loops.
- [ ] Metrics dashboard (CTR, save rate, replay rate).
- [ ] Multilingual and locale-aware recommendation support.

## Deployment Documentation

- Daily ingestion on GCP: `docs/gcp-daily-ingest.md`
- API and bot deployment: `docs/gcp-api-bot-deploy.md`
- GitHub Actions CI/CD setup: `docs/github-cicd-cloudrun.md`

---

Copyright © 2026 blacki (NguyenVanQuoc). All rights reserved.
