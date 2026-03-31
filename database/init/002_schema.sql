CREATE TABLE IF NOT EXISTS games (
  id BIGINT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  tags TEXT[] DEFAULT '{}',
  embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY,
  preferred_language TEXT DEFAULT 'vi',
  favorite_tags TEXT[] DEFAULT '{}'
);
