# SteamWeb

SteamWeb is a game discovery platform built to help players find what to play faster.
It combines Steam catalog data, SteamDB trend signals, Reddit discussion, YouTube gameplay context, and lightweight personalization into two product surfaces:

- a discovery website
- a Discord recommendation workflow

The project started as a cloud-hosted API + Discord bot + ingestion pipeline stack and is now being reshaped toward a more cost-efficient deployment model that can run on free-tier infrastructure.

## Product Vision

Players often discover games through fragmented, noisy channels:

- Steam charts show what is popular, but not why
- social platforms show opinions, but not a clean recommendation path
- trailers are useful, but disconnected from gameplay fit
- many players know the mood they want, but not the title

SteamWeb solves this by turning raw discovery signals into a focused recommendation experience:

- show trending, hot, and new-release games clearly
- help users filter by genre, mood, budget, and session length
- explain recommendations with review and trend context
- make discovery available both on the web and inside Discord

## Core Capabilities

### Discovery Feed

- trending Steam titles
- hot releases and popular releases
- releases today and recent releases
- compact game metadata with store links and supporting context

### Personalized Recommendation

- genre and mood-driven recommendations
- session-length and budget-aware filtering
- explainable recommendation reasons and scores
- freshness handling to avoid showing the same titles repeatedly

### Discord Workflow

- `/login` to connect a Steam account
- `/nenchoigi` to request game recommendations
- automated daily digest posting
- admin-triggered digest posting via `/digestnow`

### Data Foundation

- Steam metadata and review ingestion
- SteamDB chart snapshots
- Reddit post and comment ingestion
- YouTube gameplay video ingestion
- normalized gameplay tags for stronger matching

## Current State

### Working Today

- FastAPI backend
- Discord bot workflow
- Steam connect flow
- recommendation generation endpoint
- daily Steam digest generation
- data ingestion pipeline
- Supabase/Postgres-compatible schema

### In Progress

- free-tier operating mode for the ingestion pipeline
- database retention controls for low-cost hosting
- migration path toward Cloudflare-style serverless deployment

### Not Yet Finished

- fully data-driven website homepage
- production-grade game detail pages
- stronger web-facing discovery API contracts
- cleaner separation of ranking logic from storage logic

## Repository Structure

| Path | Purpose |
| --- | --- |
| `apps/web` | React + Vite frontend |
| `backend/api` | FastAPI application and routers |
| `backend/bot` | Discord bot runtime and command handlers |
| `data-pipeline` | Steam, SteamDB, Reddit, and YouTube ingestion jobs |
| `database` | Bootstrap schema, migrations, maintenance SQL |
| `docs` | Product, architecture, roadmap, and deployment docs |
| `infra` | Docker, compose, and deployment scripts |
| `ml` | Recommendation and semantic-search experiments |
| `shared` | Shared constants and contracts |

## Architecture Summary

### Experience Layer

- React web application
- Discord command workflow

### Application Layer

- FastAPI endpoints for auth, discovery, recommendations, reviews, reports, and feedback
- bot-side API client and scheduled digest flow

### Data Layer

- PostgreSQL / Supabase
- game metadata
- trend snapshots
- user profile state
- recommendation snapshots and feedback events

### Ingestion Layer

- Steam public APIs
- SteamDB chart scraping with fallback sources
- Reddit collection
- YouTube gameplay lookup

See [docs/architecture.md](D:\secret\steamweb\docs\architecture.md) for the fuller system view.

## Database Strategy

The repository now includes the full product schema, not just the early bootstrap tables.

### Fresh Deployment

For a brand-new Postgres or Supabase database:

1. Run [001_extensions.sql](D:\secret\steamweb\database\init\001_extensions.sql)
2. Run [002_schema.sql](D:\secret\steamweb\database\init\002_schema.sql)

### Existing Deployment

For an existing database:

1. Apply pending migrations from `database/migrations`
2. Use [009_app_runtime_tables.sql](D:\secret\steamweb\database\migrations\009_app_runtime_tables.sql) if runtime tables were previously ORM-only

### Free-Tier Operation

For low-cost hosting, use the retention policy documented in [docs/free-tier-database-plan.md](D:\secret\steamweb\docs\free-tier-database-plan.md) and the cleanup SQL at [001_free_tier_retention.sql](D:\secret\steamweb\database\maintenance\001_free_tier_retention.sql).

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL or Supabase connection

### Environment

Copy or adapt:

- `.env.example`

Required core variables:

- `DATABASE_URL`
- `BOT_SERVICE_TOKEN`
- `DISCORD_BOT_TOKEN`
- `DISCORD_CLIENT_ID`
- `PUBLIC_API_BASE_URL`

Optional free-tier controls:

- `FREE_TIER_MODE=true`
- `DAILY_RUN_RETENTION=true`
- `STEAM_REVIEWS_PER_GAME=5`
- `STEAM_HOT_GAMES_LIMIT=25`
- `STEAM_INDIE_LIMIT=25`
- `REDDIT_POSTS_PER_GAME=3`
- `REDDIT_COMMENTS_PER_POST=3`
- `YOUTUBE_DAILY_QUOTA_BUFFER=1000`

### Run With Docker Compose

Supabase/external Postgres:

```bash
cd infra/compose
docker compose up -d --build
```

Optional local Postgres profile:

```bash
cd infra/compose
docker compose --profile local-db up -d --build
```

### Run Key Services Manually

Backend API:

```bash
cd backend/api
python -m uvicorn app.main:app --reload --port 8000
```

Discord bot:

```bash
cd backend/bot
python bot.py
```

Daily compact ingest:

```bash
cd data-pipeline
python -m jobs.run_daily_update
```

## Deployment Direction

### Current Hosted Model

- backend API on Cloud Run
- Discord bot on Cloud Run
- data jobs on Cloud Run Job + Scheduler

### Target Cost-Efficient Model

- website on Cloudflare Pages
- API and Discord interactions on Cloudflare Workers
- Supabase free-tier Postgres with retention
- scheduled refresh with short, bounded jobs

This direction reduces the need for always-on infrastructure while preserving the core product experience.

## Product Roadmap

See the maintained roadmap in [docs/mvp-roadmap.md](D:\secret\steamweb\docs\mvp-roadmap.md).

Top priorities now:

1. finish the free-tier migration path
2. make the website data-driven
3. cleanly separate recommendation ranking from storage
4. keep the database compact through retention and smaller ingestion defaults

## Documentation Index

- [Architecture](D:\secret\steamweb\docs\architecture.md)
- [Roadmap](D:\secret\steamweb\docs\mvp-roadmap.md)
- [API Spec](D:\secret\steamweb\docs\api-spec.md)
- [Free-Tier Database Plan](D:\secret\steamweb\docs\free-tier-database-plan.md)
- [Database README](D:\secret\steamweb\database\README.md)
- [GCP Daily Ingest Deployment](D:\secret\steamweb\docs\gcp-daily-ingest.md)
- [GCP API/Bot Deployment](D:\secret\steamweb\docs\gcp-api-bot-deploy.md)
- [GitHub CI/CD on Cloud Run](D:\secret\steamweb\docs\github-cicd-cloudrun.md)

---

Copyright © 2026 blacki (NguyenVanQuoc). All rights reserved.
