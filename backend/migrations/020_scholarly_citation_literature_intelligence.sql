-- Research Librarian v10.5.0 — Scholarly Citation & Literature Intelligence
CREATE TABLE IF NOT EXISTS sc_rl_scholarly_literature_intelligence (intelligence_id TEXT PRIMARY KEY, record JSONB NOT NULL, record_hash TEXT NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now(), updated_utc TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sc_rl_scholarly_literature_intelligence_events (event_id BIGSERIAL PRIMARY KEY, intelligence_id TEXT NOT NULL, event_type TEXT NOT NULL, actor_ref TEXT NOT NULL, payload JSONB NOT NULL, event_hash TEXT NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_sc_rl_literature_events_intelligence ON sc_rl_scholarly_literature_intelligence_events(intelligence_id);
CREATE TABLE IF NOT EXISTS sc_rl_scholarly_literature_intelligence_snapshots (snapshot_id TEXT PRIMARY KEY, intelligence_id TEXT NOT NULL, snapshot_hash TEXT NOT NULL, record JSONB NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now());
