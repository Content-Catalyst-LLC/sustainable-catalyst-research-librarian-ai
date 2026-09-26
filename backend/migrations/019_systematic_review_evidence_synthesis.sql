-- Research Librarian v10.4.0 — Systematic Review & Evidence Synthesis Intelligence
CREATE TABLE IF NOT EXISTS sc_rl_systematic_reviews (
    review_id TEXT PRIMARY KEY,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_systematic_review_events (
    event_id BIGSERIAL PRIMARY KEY,
    review_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_systematic_review_events_review ON sc_rl_systematic_review_events(review_id);
CREATE TABLE IF NOT EXISTS sc_rl_systematic_review_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    review_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
