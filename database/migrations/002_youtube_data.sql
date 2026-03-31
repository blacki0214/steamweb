-- Migration 002: YouTube videos table

CREATE TABLE IF NOT EXISTS youtube_videos (
  id            BIGSERIAL    PRIMARY KEY,
  app_id        BIGINT       NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  video_id      TEXT         NOT NULL UNIQUE,
  title         TEXT,
  channel_title TEXT,
  thumbnail_url TEXT,
  embed_url     TEXT GENERATED ALWAYS AS ('https://www.youtube.com/embed/' || video_id) STORED,
  published_at  TIMESTAMPTZ,
  view_count    BIGINT       DEFAULT 0,
  like_count    BIGINT       DEFAULT 0,
  scraped_at    TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_youtube_videos_app_id ON youtube_videos(app_id);
