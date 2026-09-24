CREATE TABLE IF NOT EXISTS sc_rl_peer_review_records(
  study_id TEXT PRIMARY KEY,
  core_project_id TEXT NOT NULL,
  record JSONB NOT NULL,
  record_fingerprint TEXT NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_peer_review_events(
  event_id BIGSERIAL PRIMARY KEY,
  study_id TEXT NOT NULL REFERENCES sc_rl_peer_review_records(study_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  actor_ref TEXT NOT NULL DEFAULT '',
  payload JSONB NOT NULL,
  event_hash TEXT NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_peer_review_events_study ON sc_rl_peer_review_events(study_id,event_id);
CREATE TABLE IF NOT EXISTS sc_rl_peer_review_packages(
  package_id TEXT PRIMARY KEY,
  study_id TEXT NOT NULL REFERENCES sc_rl_peer_review_records(study_id) ON DELETE CASCADE,
  package_hash TEXT NOT NULL,
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
