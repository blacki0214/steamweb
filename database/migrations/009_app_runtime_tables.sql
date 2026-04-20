-- Migration 009: add runtime tables that previously existed only in ORM models.
-- This keeps the database folder complete for real deployments.

CREATE TABLE IF NOT EXISTS oauth_states (
  state TEXT PRIMARY KEY,
  discord_user_id TEXT NOT NULL,
  redirect_uri TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oauth_states_discord_user_id
  ON oauth_states(discord_user_id);

CREATE TABLE IF NOT EXISTS user_connections (
  discord_user_id TEXT PRIMARY KEY,
  steam_id TEXT NOT NULL,
  connected_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_connections_steam_id
  ON user_connections(steam_id);

CREATE TABLE IF NOT EXISTS user_steam_stats (
  discord_user_id TEXT PRIMARY KEY,
  steam_id TEXT NOT NULL,
  persona_name TEXT,
  profile_url TEXT,
  avatar_url TEXT,
  total_games INTEGER,
  total_playtime_hours DOUBLE PRECISION,
  top_games JSONB NOT NULL DEFAULT '[]'::jsonb,
  synced_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_user_steam_stats_steam_id
  ON user_steam_stats(steam_id);

CREATE TABLE IF NOT EXISTS user_profiles (
  discord_user_id TEXT PRIMARY KEY,
  steam_connected BOOLEAN NOT NULL DEFAULT FALSE,
  top_genres JSONB NOT NULL DEFAULT '[]'::jsonb,
  mood_preferences JSONB NOT NULL DEFAULT '[]'::jsonb,
  play_style JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendation_snapshots (
  request_id TEXT PRIMARY KEY,
  base_request_id TEXT,
  payload JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback_events (
  id BIGSERIAL PRIMARY KEY,
  discord_user_id TEXT NOT NULL,
  game_id TEXT NOT NULL,
  feedback_type TEXT NOT NULL,
  context JSONB NOT NULL DEFAULT '{}'::jsonb,
  idempotency_key TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feedback_events_discord_user_id
  ON feedback_events(discord_user_id);

CREATE INDEX IF NOT EXISTS idx_feedback_events_game_id
  ON feedback_events(game_id);
