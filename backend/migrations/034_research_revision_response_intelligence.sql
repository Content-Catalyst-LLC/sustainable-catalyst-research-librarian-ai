CREATE TABLE IF NOT EXISTS sc_rl_revision_response_projects(
  revision_response_id TEXT PRIMARY KEY,
  record JSONB NOT NULL,
  record_hash TEXT NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_revision_response_events(
  event_id BIGSERIAL PRIMARY KEY,
  revision_response_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor_ref TEXT NOT NULL,
  payload JSONB NOT NULL,
  event_hash TEXT NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_revision_response_events_project
  ON sc_rl_revision_response_events(revision_response_id);
CREATE TABLE IF NOT EXISTS sc_rl_revision_response_snapshots(
  snapshot_id TEXT PRIMARY KEY,
  revision_response_id TEXT NOT NULL,
  snapshot_hash TEXT NOT NULL,
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
