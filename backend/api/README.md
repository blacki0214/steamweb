# Backend API

This service is the application core of SteamWeb.

It exposes the routes used by the website, the Discord bot, and operational workflows such as the Steam connect flow and daily digest generation.

## Responsibilities

The API currently handles:

- Steam auth and account connect flow
- user profile state
- recommendation generation
- digest/report generation
- game search and detail lookup
- review summary endpoints
- feedback recording

## Main Entrypoint

- [app/main.py](D:\secret\steamweb\backend\api\app\main.py)

## Current Route Groups

- `/api/v1/auth`
- `/api/v1/users`
- `/api/v1/games`
- `/api/v1/search`
- `/api/v1/reviews`
- `/api/v1/recommendations`
- `/api/v1/feedback`
- `/api/v1/reports`

See:

- [docs/api-spec.md](D:\secret\steamweb\docs\api-spec.md)

## Architectural Note

The API is functional, but it still carries MVP-era consolidation in:

- [store.py](D:\secret\steamweb\backend\api\app\services\store.py)

That file currently mixes:

- persistence
- recommendation ranking
- fallback sourcing
- snapshot management
- feedback storage
- profile handling

This works, but it is the main backend refactor target.

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL or Supabase connection recommended

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Database Behavior

The API supports:

- local SQLite for zero-config development
- Postgres / Supabase for real runtime use

Relevant file:

- [session.py](D:\secret\steamweb\backend\api\app\db\session.py)

For production-like usage, prefer `DATABASE_URL` pointing to Postgres/Supabase.

## Product State Stored By The API

The API relies on these runtime tables:

- `oauth_states`
- `user_connections`
- `user_steam_stats`
- `user_profiles`
- `recommendation_snapshots`
- `feedback_events`

Those tables are now explicitly included in the SQL schema under:

- [database/init/002_schema.sql](D:\secret\steamweb\database\init\002_schema.sql)
- [database/migrations/009_app_runtime_tables.sql](D:\secret\steamweb\database\migrations\009_app_runtime_tables.sql)

## Current Gaps

The API still needs:

- stronger web-facing discovery endpoints
- cleaner recommendation-service separation
- richer game-detail support from DB-backed data
- tighter testing and smoke-check coverage

## Deployment Notes

### Current Hosted Model

- Cloud Run service

### Lower-Cost Direction

The target low-cost model is to move the most essential HTTP functionality toward:

- Cloudflare Workers for web/API and Discord interaction handling
- Supabase as compact persistent storage

The backend route design should evolve toward smaller, discovery-focused HTTP contracts that map cleanly onto serverless execution.
