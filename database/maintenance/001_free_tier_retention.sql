-- Free-tier retention maintenance
-- Run this manually on Supabase/Postgres after a backup if you want to shrink
-- the live database without removing any product tables.
--
-- Strategy:
-- - Keep the full schema.
-- - Keep compact game metadata and user/runtime tables intact.
-- - Prune high-volume source rows that are not required indefinitely.

BEGIN;

-- 1) Keep only the most recent 90 days of SteamDB chart snapshots.
DELETE FROM steamdb_chart_snapshots
WHERE snapshot_at < NOW() - INTERVAL '90 days';

-- 2) Keep Reddit comments only for posts created in the last 60 days.
DELETE FROM reddit_comments rc
USING reddit_posts rp
WHERE rc.post_id = rp.id
  AND COALESCE(rp.created_utc, rp.scraped_at, NOW()) < NOW() - INTERVAL '60 days';

-- 3) Keep Reddit posts only for the last 60 days.
DELETE FROM reddit_posts
WHERE COALESCE(created_utc, scraped_at, NOW()) < NOW() - INTERVAL '60 days';

-- 4) Keep only the most recent 5 Steam reviews per game.
WITH ranked_reviews AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY app_id
      ORDER BY COALESCE(created_at, scraped_at) DESC, id DESC
    ) AS row_num
  FROM steam_reviews
)
DELETE FROM steam_reviews sr
USING ranked_reviews rr
WHERE sr.id = rr.id
  AND rr.row_num > 5;

-- 5) Keep at most one YouTube video per game: the most viewed, newest tie-break.
WITH ranked_videos AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY app_id
      ORDER BY COALESCE(view_count, 0) DESC, COALESCE(published_at, scraped_at) DESC, id DESC
    ) AS row_num
  FROM youtube_videos
)
DELETE FROM youtube_videos yv
USING ranked_videos rv
WHERE yv.id = rv.id
  AND rv.row_num > 1;

-- 6) Remove recommendation snapshots older than 30 days.
DELETE FROM recommendation_snapshots
WHERE created_at < NOW() - INTERVAL '30 days';

-- 7) Remove feedback events older than 180 days.
DELETE FROM feedback_events
WHERE created_at < NOW() - INTERVAL '180 days';

COMMIT;

VACUUM ANALYZE steamdb_chart_snapshots;
VACUUM ANALYZE reddit_comments;
VACUUM ANALYZE reddit_posts;
VACUUM ANALYZE steam_reviews;
VACUUM ANALYZE youtube_videos;
VACUUM ANALYZE recommendation_snapshots;
VACUUM ANALYZE feedback_events;
