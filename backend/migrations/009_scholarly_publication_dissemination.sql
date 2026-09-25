CREATE TABLE IF NOT EXISTS sc_rl_scholarly_publications(
  publication_id TEXT PRIMARY KEY, study_id TEXT NOT NULL, record JSONB NOT NULL,
  record_fingerprint TEXT NOT NULL, idempotency_key TEXT NOT NULL DEFAULT '',
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(), updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_scholarly_publications_idempotency ON sc_rl_scholarly_publications(idempotency_key) WHERE idempotency_key<>'';
CREATE TABLE IF NOT EXISTS sc_rl_scholarly_publication_events(
  event_id BIGSERIAL PRIMARY KEY, publication_id TEXT NOT NULL REFERENCES sc_rl_scholarly_publications(publication_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL, actor_ref TEXT NOT NULL DEFAULT '', payload JSONB NOT NULL,
  event_hash TEXT NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_scholarly_publication_packages(
  package_id TEXT PRIMARY KEY, publication_id TEXT NOT NULL REFERENCES sc_rl_scholarly_publications(publication_id) ON DELETE CASCADE,
  package_hash TEXT NOT NULL, record JSONB NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
