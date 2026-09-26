-- Research Librarian AI v10.7.0 — Research Gap & Novelty Intelligence
CREATE TABLE IF NOT EXISTS sc_rl_research_gap_novelty_intelligence(
    gap_novelty_id TEXT PRIMARY KEY, record JSONB NOT NULL, record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(), updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_research_gap_novelty_events(
    event_id BIGSERIAL PRIMARY KEY, gap_novelty_id TEXT NOT NULL, event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL, payload JSONB NOT NULL, event_hash TEXT NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_research_gap_novelty_events_project ON sc_rl_research_gap_novelty_events(gap_novelty_id);
CREATE TABLE IF NOT EXISTS sc_rl_research_gap_novelty_snapshots(
    snapshot_id TEXT PRIMARY KEY, gap_novelty_id TEXT NOT NULL, snapshot_hash TEXT NOT NULL, record JSONB NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
