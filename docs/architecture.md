# Architecture

SteamWeb is organized as a discovery system with four layers:

- product surfaces
- application services
- data platform
- ingestion and enrichment

## 1. Product Surfaces

### Website

Path:

- `apps/web`

Responsibilities:

- show discovery home sections
- present trending, hot, and new-release games
- surface personalized recommendations
- host game detail views

Current state:

- design shell is present
- full live-data integration is still incomplete

### Discord

Path:

- `backend/bot`

Responsibilities:

- handle `/login`
- handle `/nenchoigi`
- post daily Steam digest
- expose admin-triggered digest posting

Current state:

- the Discord workflow is the most complete product surface in the repo

## 2. Application Services

### API Service

Path:

- `backend/api`

Primary responsibilities:

- auth and Steam connect flow
- user profile and connection state
- recommendation generation
- reports and digest payload generation
- search, feedback, and review summary APIs

Main entrypoint:

- [main.py](D:\secret\steamweb\backend\api\app\main.py)

### Current Architectural Constraint

The API works, but too much logic is concentrated inside:

- [store.py](D:\secret\steamweb\backend\api\app\services\store.py)

That module currently mixes:

- persistence
- profile handling
- recommendation ranking
- fallback data sourcing
- snapshot storage
- feedback recording

This is acceptable for MVP velocity, but it is the main backend refactor target.

## 3. Data Platform

### Database

Path:

- `database`

The database layer now includes:

- bootstrap schema
- historical migrations
- runtime product tables
- free-tier retention maintenance

Core content tables:

- `games`
- `steam_reviews`
- `youtube_videos`
- `reddit_posts`
- `reddit_comments`
- `steamdb_chart_snapshots`

Core runtime tables:

- `oauth_states`
- `user_connections`
- `user_steam_stats`
- `user_profiles`
- `recommendation_snapshots`
- `feedback_events`

### Database Strategy

- keep full product schema
- aggressively retain only compact, recent raw-source history on free tier
- preserve user and product-state tables indefinitely

See:

- [database/README.md](D:\secret\steamweb\database\README.md)
- [free-tier-database-plan.md](D:\secret\steamweb\docs\free-tier-database-plan.md)

## 4. Ingestion and Enrichment

Path:

- `data-pipeline`

Responsibilities:

- fetch Steam game metadata
- fetch Steam reviews
- scrape SteamDB charts
- fetch YouTube gameplay videos
- fetch Reddit discussions
- run daily update orchestration

Current state:

- pipeline is functional
- free-tier controls now exist to reduce data growth automatically

## Data Flow

### Discovery Data

1. Steam and SteamDB sources are ingested into Postgres
2. Reddit and YouTube add supporting context
3. normalized tags improve recommendation matching
4. API reads compact signals to serve reports and recommendations
5. website and Discord present those outputs

### Steam Connect Flow

1. Discord user calls `/login`
2. bot requests connect link from API
3. user completes Steam OpenID flow
4. API stores connection and summary stats
5. bot posts linked profile back to Discord

### Recommendation Flow

1. user provides genre, mood, session time, and budget
2. API builds candidate set from database and fallbacks
3. ranking logic scores and filters candidates
4. API returns reasons, links, and review context
5. bot or website renders the recommendation response

## Hosting Direction

### Current Hosted Model

- API on Cloud Run
- bot on Cloud Run
- ingest on Cloud Run Job + Scheduler

### Target Low-Cost Model

- website on Cloudflare Pages
- API and Discord interactions on Cloudflare Workers
- compact Postgres on Supabase
- bounded scheduled jobs with retention

## Architectural Priorities

The highest-value architectural improvements now are:

1. split ranking logic from storage logic
2. build clean web-facing discovery endpoints
3. complete the free-tier runtime path
4. connect the website to live data
