# Indie Game Discovery Platform

Personalized web platform for indie game discovery using Steam, YouTube, and Reddit data.

## Workspace Layout

- apps/web: React frontend (Vite + TypeScript)
- backend/api: FastAPI backend services
- data-pipeline: ingestion and NLP processing jobs
- database: SQL init scripts, migrations, seeds
- ml: recommendation and semantic search modules
- infra: docker/compose and deployment scripts
- shared: shared contracts and constants
- docs: architecture and delivery docs

## Quick Start

1. Configure environment variables from `.env.example`.
2. Start PostgreSQL + pgvector.
3. Run backend API.
4. Run web app.
5. Run data ingestion jobs.
