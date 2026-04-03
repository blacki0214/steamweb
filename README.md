# Indie Game Discovery Platform

> Discover indie games faster with Steam + Reddit + YouTube intelligence.

Indie Game Discovery is a data-driven recommendation platform that combines Steam store data, SteamDB trends, Reddit discussion signals, and YouTube gameplay context.

It includes a web app, a FastAPI backend, and a Discord bot designed for discovery workflows such as Steam account linking and personalized recommendations.

## 🎯 Overview

### Problem
Players discover many games through fragmented sources (store pages, social posts, and videos) and often miss high-fit indie titles.

### Solution
This project builds a unified pipeline and recommendation layer that:
- ingests game metadata and social/review signals,
- normalizes and scores data for discovery,
- serves recommendations through API + Discord bot,
- provides a web dashboard for browsing and analysis.

### Current Product Flow (Discord)
- `/login`: connect Steam account and auto-announce linked profile details.
- `/nenchoigi`: recommendation command with reason + score + Steam/Reddit/YouTube context.
- `/digestnow`: admin-only manual trigger for Steam daily digest embed.
- scheduled daily digest: SteamDB-style sections posted automatically.

## ✅ Status

- API deployed on Cloud Run.
- Bot deployed on Cloud Run as always-on (24/7 style runtime via min instance).
- Ingest pipeline deployed as Cloud Run Job with Cloud Scheduler trigger.
- GitHub Actions workflow added for auto-deploy on push to `main`.

## 📁 Repository Layout

- `apps/web`: React frontend (Vite + TypeScript)
- `backend/api`: FastAPI backend services
- `backend/bot`: Discord bot client
- `data-pipeline`: ingestion and NLP processing jobs
- `database`: SQL init scripts, migrations, seeds
- `ml`: recommendation and semantic search modules
- `infra`: Docker, compose, and deployment scripts
- `shared`: shared contracts and constants
- `docs`: architecture, roadmap, and deployment guides

## 🛠️ Quick Start (Local)

1. Configure environment variables from `.env.example`.
2. Set `DATABASE_URL` (Supabase Postgres recommended).
3. Start services via Docker Compose.
4. Run ingestion jobs to populate and refresh data.

### Docker Compose (Supabase)

- Stack uses external Postgres via `DATABASE_URL` in `infra/compose/.env`.
- Start:
  - `cd infra/compose`
  - `docker compose up -d --build`

### Optional Local Postgres (Dev)

- Start with local DB profile:
  - `cd infra/compose`
  - `docker compose --profile local-db up -d --build`

## 🗺️ Roadmap

### Phase 1 - MVP Foundation
- [x] Ingest Steam game metadata into Postgres.
- [x] Ingest YouTube + Reddit context for discovery signals.
- [x] Build FastAPI contract endpoints and base recommendation logic.
- [x] Build React web app skeleton and key pages.

### Phase 2 - Discord Discovery Workflow
- [x] `/login` Steam connect flow.
- [x] `/nenchoigi` recommendation flow with multi-source context.
- [x] Daily Steam digest scheduler and manual trigger (`/digestnow`).
- [x] Admin-only permission gate for manual digest command.

### Phase 3 - Reliability and Operations
- [x] Deploy API and bot to Cloud Run.
- [x] Deploy ingest pipeline as Cloud Run Job + Scheduler.
- [x] Add GitHub CI/CD workflow for image build and deploy.
- [ ] Add end-to-end smoke tests after deploy.
- [ ] Add alerting for failed ingest or bot auth/runtime errors.

### Phase 4 - Recommendation Quality
- [ ] Improve ranking with stronger preference modeling and feedback loops.
- [ ] Add evaluation metrics dashboard (CTR, save rate, replay rate).
- [ ] Expand multilingual support and locale-aware recommendations.

## 🧩 Architecture

- Data Layer: Steam, YouTube, Reddit, SteamDB to PostgreSQL + vector-ready schema.
- Logic Layer: ingestion, normalization, sentiment, ranking, semantic search.
- Experience Layer: web dashboard + Discord command flow.

For details, see `docs/architecture.md`.

## 🚀 Deployment Guides

- Cloud daily ingestion (Cloud Run Job + Scheduler): `docs/gcp-daily-ingest.md`
- Cloud API + always-on bot: `docs/gcp-api-bot-deploy.md`
- GitHub Actions CI/CD to Cloud Run: `docs/github-cicd-cloudrun.md`

---

2026 Author: blacki (NguyenVanQuoc)
