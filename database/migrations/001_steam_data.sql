-- Migration 001: Extend games table + add steam_reviews
-- Run after init/002_schema.sql

-- Extend games table with Steam metadata fields
ALTER TABLE games
  ADD COLUMN IF NOT EXISTS short_description  TEXT,
  ADD COLUMN IF NOT EXISTS header_image       TEXT,
  ADD COLUMN IF NOT EXISTS genres             TEXT[]   DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS price_usd          NUMERIC(8,2),
  ADD COLUMN IF NOT EXISTS is_free            BOOLEAN  DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS metacritic_score   INTEGER,
  ADD COLUMN IF NOT EXISTS total_reviews      INTEGER  DEFAULT 0,
  ADD COLUMN IF NOT EXISTS positive_reviews   INTEGER  DEFAULT 0,
  ADD COLUMN IF NOT EXISTS review_score_desc  TEXT,
  ADD COLUMN IF NOT EXISTS release_date       TEXT,
  ADD COLUMN IF NOT EXISTS developer          TEXT,
  ADD COLUMN IF NOT EXISTS publisher          TEXT,
  ADD COLUMN IF NOT EXISTS website            TEXT,
  ADD COLUMN IF NOT EXISTS scraped_at         TIMESTAMPTZ DEFAULT NOW();

-- Steam reviews table
CREATE TABLE IF NOT EXISTS steam_reviews (
  id              BIGSERIAL PRIMARY KEY,
  app_id          BIGINT    NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  recommendation_id TEXT    UNIQUE,
  author_steamid  TEXT,
  voted_up        BOOLEAN   NOT NULL,
  playtime_hours  INTEGER,
  review_text     TEXT,
  votes_helpful   INTEGER   DEFAULT 0,
  created_at      TIMESTAMPTZ,
  scraped_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_steam_reviews_app_id ON steam_reviews(app_id);
CREATE INDEX IF NOT EXISTS idx_steam_reviews_voted_up ON steam_reviews(voted_up);
