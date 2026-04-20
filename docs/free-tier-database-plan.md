# Free-Tier Database Plan

The project keeps the full product schema, but the free-tier deployment should not retain unlimited historical source data.

## Keep Forever

These tables are core product state and should remain intact:

- `games`
- `users`
- `oauth_states`
- `user_connections`
- `user_steam_stats`
- `user_profiles`

## Keep With Retention

These tables are useful, but they should be pruned regularly on a free-tier database:

- `steamdb_chart_snapshots`
  - keep 90 days
- `reddit_posts`
  - keep 60 days
- `reddit_comments`
  - keep 60 days, tied to retained posts
- `steam_reviews`
  - keep only the most recent 5 reviews per game
- `youtube_videos`
  - keep only 1 best video per game
- `recommendation_snapshots`
  - keep 30 days
- `feedback_events`
  - keep 180 days

## Maintenance Script

Use:

- [001_free_tier_retention.sql](D:\secret\steamweb\database\maintenance\001_free_tier_retention.sql)

This script preserves the schema and product behavior while shrinking the tables that grow fastest.

## Why This Is The Right Tradeoff

- The website and Discord bot need compact game metadata, user preference state, and the latest trend signals.
- They do not need unlimited raw review/comment history.
- Free-tier Postgres works best when raw-source history is summarized or pruned.

## Suggested Operating Mode

1. Ingest only a compact game set, not the entire Steam catalog.
2. Refresh only current discovery signals.
3. Run retention after daily/weekly refresh.
4. Prefer summary fields on `games` over long-term storage of raw source rows.
