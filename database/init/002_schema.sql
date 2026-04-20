-- Full bootstrap schema for a fresh Postgres/Supabase deployment.
-- This file is intentionally self-contained so a new environment does not
-- depend on replaying every historical migration to get a working schema.

CREATE TABLE IF NOT EXISTS games (
  id BIGINT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  short_description TEXT,
  header_image TEXT,
  genres TEXT[] NOT NULL DEFAULT '{}',
  tags TEXT[] NOT NULL DEFAULT '{}',
  normalized_gameplay_tags TEXT[] NOT NULL DEFAULT '{}',
  price_usd NUMERIC(8, 2),
  is_free BOOLEAN NOT NULL DEFAULT FALSE,
  metacritic_score INTEGER,
  total_reviews INTEGER NOT NULL DEFAULT 0,
  positive_reviews INTEGER NOT NULL DEFAULT 0,
  review_score_desc TEXT,
  release_date TEXT,
  developer TEXT,
  publisher TEXT,
  website TEXT,
  embedding vector(1536),
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_games_normalized_gameplay_tags_gin
  ON games USING GIN (normalized_gameplay_tags);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  preferred_language TEXT DEFAULT 'vi',
  favorite_tags TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS steam_reviews (
  id BIGSERIAL PRIMARY KEY,
  app_id BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  recommendation_id TEXT UNIQUE,
  author_steamid TEXT,
  voted_up BOOLEAN NOT NULL,
  playtime_hours INTEGER,
  review_text TEXT,
  votes_helpful INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ,
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_steam_reviews_app_id ON steam_reviews(app_id);
CREATE INDEX IF NOT EXISTS idx_steam_reviews_voted_up ON steam_reviews(voted_up);

CREATE TABLE IF NOT EXISTS youtube_videos (
  id BIGSERIAL PRIMARY KEY,
  app_id BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  video_id TEXT NOT NULL UNIQUE,
  title TEXT,
  channel_title TEXT,
  thumbnail_url TEXT,
  embed_url TEXT GENERATED ALWAYS AS ('https://www.youtube.com/embed/' || video_id) STORED,
  published_at TIMESTAMPTZ,
  view_count BIGINT NOT NULL DEFAULT 0,
  like_count BIGINT NOT NULL DEFAULT 0,
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_youtube_videos_app_id ON youtube_videos(app_id);

CREATE TABLE IF NOT EXISTS reddit_posts (
  id TEXT PRIMARY KEY,
  app_id BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  subreddit TEXT,
  title TEXT,
  selftext TEXT,
  score INTEGER NOT NULL DEFAULT 0,
  upvote_ratio NUMERIC(4, 3),
  num_comments INTEGER NOT NULL DEFAULT 0,
  url TEXT,
  created_utc TIMESTAMPTZ,
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reddit_comments (
  id TEXT PRIMARY KEY,
  post_id TEXT NOT NULL REFERENCES reddit_posts(id) ON DELETE CASCADE,
  app_id BIGINT NOT NULL,
  body TEXT,
  score INTEGER NOT NULL DEFAULT 0,
  created_utc TIMESTAMPTZ,
  scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reddit_posts_app_id ON reddit_posts(app_id);
CREATE INDEX IF NOT EXISTS idx_reddit_comments_post_id ON reddit_comments(post_id);
CREATE INDEX IF NOT EXISTS idx_reddit_comments_app_id ON reddit_comments(app_id);

CREATE TABLE IF NOT EXISTS steamdb_chart_snapshots (
  id BIGSERIAL PRIMARY KEY,
  snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  chart_type TEXT NOT NULL,
  rank INTEGER NOT NULL,
  app_id BIGINT,
  game_name TEXT NOT NULL,
  players_current INTEGER,
  players_peak_24h INTEGER,
  players_all_time_peak INTEGER,
  raw_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_url TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_snapshot_at
  ON steamdb_chart_snapshots(snapshot_at);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_chart_rank
  ON steamdb_chart_snapshots(chart_type, rank);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_app_id
  ON steamdb_chart_snapshots(app_id);

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
