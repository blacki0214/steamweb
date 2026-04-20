# Free-Tier Architecture

This document describes the target low-cost deployment model for SteamWeb.

## Goal

Preserve the core product experience without requiring:

- an always-on expensive bot host
- a full always-on API server
- heavy long-running jobs

## Target Platform Mapping

### Website

- Platform: Cloudflare Pages
- Source: `apps/web`

### API and Discord Interactions

- Platform: Cloudflare Workers
- Role:
  - web-facing API routes
  - Discord interaction endpoint
  - small scheduled tasks

### Database

- Platform: Supabase Postgres
- Strategy:
  - keep full schema
  - keep source-history retention strict

## Why This Direction

The original hosted model is operationally sound, but it is not ideal for a no-budget phase.

The free-tier direction works by:

- using static hosting where possible
- using event-driven HTTP handlers instead of always-on runtime
- keeping only compact useful data in the database
- pruning high-volume history automatically

## Architectural Consequences

### Discord

Instead of depending entirely on a persistent gateway bot, the long-term low-cost path should prefer:

- slash-command interactions
- webhook-style interaction handling
- short response lifecycles

### Data Pipeline

The pipeline should:

- ingest fewer titles
- keep fewer raw reviews and comments
- refresh smaller windows of source data
- run retention automatically

### Website

The site should become the main discovery surface for:

- trending games
- hot releases
- new releases
- recommendation UX

## Migration Priorities

1. complete the free-tier deployable runtime path
2. wire the website to live discovery data
3. reduce always-on Discord runtime dependency
4. keep Supabase under free-tier limits through bounded ingestion
