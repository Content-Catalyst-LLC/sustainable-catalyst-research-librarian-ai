-- Research Librarian v10.3.0 — Evidence Search Strategy Engine
CREATE TABLE IF NOT EXISTS sc_rl_evidence_search_strategies (
    strategy_id TEXT PRIMARY KEY,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_evidence_search_strategy_events (
    event_id BIGSERIAL PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_evidence_search_events_strategy ON sc_rl_evidence_search_strategy_events(strategy_id);
CREATE TABLE IF NOT EXISTS sc_rl_evidence_search_strategy_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
