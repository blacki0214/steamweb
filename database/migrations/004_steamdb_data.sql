-- Migration 004: SteamDB chart snapshots table

CREATE TABLE IF NOT EXISTS steamdb_chart_snapshots (
  id                    BIGSERIAL PRIMARY KEY,
  snapshot_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  chart_type            TEXT NOT NULL,
  rank                  INTEGER NOT NULL,
  app_id                BIGINT,
  game_name             TEXT NOT NULL,
  players_current       INTEGER,
  players_peak_24h      INTEGER,
  players_all_time_peak INTEGER,
  raw_metrics           JSONB DEFAULT '{}',
  source_url            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_snapshot_at
  ON steamdb_chart_snapshots(snapshot_at);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_chart_rank
  ON steamdb_chart_snapshots(chart_type, rank);

CREATE INDEX IF NOT EXISTS idx_steamdb_snapshots_app_id
  ON steamdb_chart_snapshots(app_id);
