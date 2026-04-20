# Product Roadmap

This roadmap reflects the current state of the repository and the direction required to make the product sustainable on lower-cost infrastructure.

## Product Thesis

SteamWeb should become a practical discovery assistant for players who:

- want to see what is trending right now
- want a smaller, more curated view than the full Steam store
- want recommendations that reflect mood, time, and budget
- want discovery available both on the website and inside Discord

## Phase 1: Data Foundation

Status: Completed

- [x] Bootstrap PostgreSQL schema and migrations
- [x] Ingest Steam game metadata
- [x] Ingest Steam reviews
- [x] Ingest YouTube gameplay context
- [x] Ingest Reddit discussion context
- [x] Ingest SteamDB chart snapshots
- [x] Add normalized gameplay tags to support better recommendation matching

## Phase 2: Discord Discovery Workflow

Status: Completed

- [x] `/login` Steam account connection flow
- [x] `/nenchoigi` recommendation command
- [x] daily digest generation
- [x] admin-only `/digestnow`
- [x] bot-side embed formatting and command sync handling

## Phase 3: Operational Baseline

Status: Completed / Partial

- [x] API deployment path
- [x] bot deployment path
- [x] scheduled ingest deployment path
- [x] GitHub CI/CD support for hosted deployments
- [ ] post-deploy smoke test automation
- [ ] runtime alerting and failure notifications

## Phase 4: Free-Tier Sustainability

Status: In Progress

- [x] full SQL schema represented inside `database/`
- [x] retention policy for large raw-source tables
- [x] free-tier ingest defaults to reduce growth
- [x] Supabase retention cleanup tested against live database
- [ ] document full Cloudflare deployment path
- [ ] replace always-on bot dependency with interactions-first runtime
- [ ] reduce long-running pipeline behavior into short, bounded jobs

## Phase 5: Website Product Completion

Status: Next

- [ ] replace static homepage sections with live API-backed discovery data
- [ ] build real hero/trending/hot/new-release sections
- [ ] implement game detail pages backed by database data
- [ ] expose recommendation generation on the website
- [ ] add loading, empty, and error states across the discovery UI

## Phase 6: Recommendation Quality

Status: Next

- [ ] move ranking logic out of `store.py` into a dedicated service layer
- [ ] use stronger preference modeling from user profile + Steam-linked signals
- [ ] improve freshness and diversity balancing
- [ ] make recommendation reasons more useful and user-facing
- [ ] add feedback loop usage from `feedback_events`

## Phase 7: Discovery UX Expansion

Status: Future

- [ ] advanced search and filters
- [ ] richer game detail context from Steam, Reddit, and YouTube
- [ ] saved lists and preference editing
- [ ] explainable recommendation cards on the homepage
- [ ] better navigation for trending versus personalized exploration

## Phase 8: Reliability, Security, and Governance

Status: Future

- [ ] stronger secrets management and key rotation
- [ ] rate limiting and abuse controls
- [ ] dependency and container scanning in CI
- [ ] incident response runbooks
- [ ] schema migration discipline and release checklists

## Near-Term Execution Priority

If only a small amount of work can be funded, the highest-value order is:

1. finish the free-tier architecture migration
2. make the website genuinely data-driven
3. refactor recommendation logic into a dedicated service
4. stabilize deployment and testing

## Success Criteria

The product is in a strong state when:

- discovery data is refreshed automatically without local runtime
- the site shows live trending/hot/new-release data
- Discord commands work without requiring an always-on costly host
- recommendation quality is explainable and stable
- the database remains small enough to operate on low-cost hosting
