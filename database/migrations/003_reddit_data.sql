-- Migration 003: Reddit posts and comments tables

CREATE TABLE IF NOT EXISTS reddit_posts (
  id              TEXT         PRIMARY KEY,   -- Reddit post short ID (e.g. "abc123")
  app_id          BIGINT       NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  subreddit       TEXT,
  title           TEXT,
  selftext        TEXT,
  score           INTEGER      DEFAULT 0,
  upvote_ratio    NUMERIC(4,3),
  num_comments    INTEGER      DEFAULT 0,
  url             TEXT,
  created_utc     TIMESTAMPTZ,
  scraped_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reddit_comments (
  id              TEXT         PRIMARY KEY,   -- Reddit comment short ID
  post_id         TEXT         NOT NULL REFERENCES reddit_posts(id) ON DELETE CASCADE,
  app_id          BIGINT       NOT NULL,
  body            TEXT,
  score           INTEGER      DEFAULT 0,
  created_utc     TIMESTAMPTZ,
  scraped_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reddit_posts_app_id ON reddit_posts(app_id);
CREATE INDEX IF NOT EXISTS idx_reddit_comments_post_id ON reddit_comments(post_id);
CREATE INDEX IF NOT EXISTS idx_reddit_comments_app_id ON reddit_comments(app_id);
