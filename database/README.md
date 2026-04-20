# Database Layout

The `database` folder now contains the complete persisted schema used by the project.

## Files

- `init/001_extensions.sql`
  - Postgres extensions required for a fresh database.
- `init/002_schema.sql`
  - Full bootstrap schema for a fresh deployment.
  - Use this for a clean Supabase/Postgres setup.
- `migrations/001_*.sql` ... `migrations/009_*.sql`
  - Historical incremental changes.
  - Use these when upgrading an existing database.
- `maintenance/001_free_tier_retention.sql`
  - Optional cleanup script for running the full schema on a free-tier database.
  - Prunes high-volume history while keeping all product tables.

## Current Table Coverage

Content and discovery tables:

- `games`
- `users`
- `steam_reviews`
- `youtube_videos`
- `reddit_posts`
- `reddit_comments`
- `steamdb_chart_snapshots`

Runtime product tables:

- `oauth_states`
- `user_connections`
- `user_steam_stats`
- `user_profiles`
- `recommendation_snapshots`
- `feedback_events`

## Notes

- The API previously relied on ORM auto-create for several runtime tables. Those tables are now explicitly defined in SQL under `database/`.
- `init/002_schema.sql` is the authoritative bootstrap file for a new Postgres deployment.
- The historical migrations are retained for compatibility and auditability.
- If you are deploying on Supabase free tier, use the maintenance script to keep the database under size limits instead of deleting product tables.
