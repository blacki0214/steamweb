# Data Pipeline

This directory contains the source-ingestion and refresh jobs that feed SteamWeb's discovery and recommendation data.

## Responsibilities

The pipeline currently ingests and refreshes:

- Steam game metadata
- Steam reviews
- SteamDB chart snapshots
- YouTube gameplay video references
- Reddit discussion context

## Main Components

### Ingestors

Path:

- `data-pipeline/ingestors`

Included ingestors:

- `steam_ingestor.py`
- `steamdb_ingestor.py`
- `youtube_ingestor.py`
- `reddit_ingestor.py`

### Jobs

Path:

- `data-pipeline/jobs`

Included orchestration jobs:

- `run_ingest_all.py`
- `run_daily_update.py`

## Current Operating Modes

### Standard Mode

Designed for fuller ingestion and richer historical context.

### Free-Tier Mode

Now supported via:

- `FREE_TIER_MODE=true`

When enabled, the pipeline:

- ingests fewer games
- stores fewer Steam reviews
- stores fewer Reddit posts and comments
- leaves more YouTube quota buffer
- applies retention cleanup automatically in the daily job

This is the recommended mode for Supabase free-tier operation.

## Key Environment Controls

- `FREE_TIER_MODE`
- `DAILY_INCLUDE_STEAM`
- `DAILY_STEAM_MODE`
- `DAILY_RUN_RETENTION`
- `STEAM_REVIEWS_PER_GAME`
- `STEAM_HOT_GAMES_LIMIT`
- `STEAM_INDIE_LIMIT`
- `REDDIT_POSTS_PER_GAME`
- `REDDIT_COMMENTS_PER_POST`
- `YOUTUBE_DAILY_QUOTA_BUFFER`

## Common Commands

Run the full pipeline:

```bash
python -m jobs.run_ingest_all
```

Run compact daily refresh:

```bash
python -m jobs.run_daily_update
```

Run dry mode:

```bash
python -m jobs.run_ingest_all --dry-run
```

## Database Discipline

The pipeline writes into the product schema defined under:

- [database/init/002_schema.sql](D:\secret\steamweb\database\init\002_schema.sql)

To keep the database compact on low-cost hosting, retention cleanup is available at:

- [database/maintenance/001_free_tier_retention.sql](D:\secret\steamweb\database\maintenance\001_free_tier_retention.sql)

Related doc:

- [docs/free-tier-database-plan.md](D:\secret\steamweb\docs\free-tier-database-plan.md)

## Operational Direction

The pipeline is moving toward:

- smaller bounded refresh jobs
- compact retained data
- low-cost scheduled execution

That direction is necessary to support the project's free-tier hosting strategy without losing the core discovery experience.
