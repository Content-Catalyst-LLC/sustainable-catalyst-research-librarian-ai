CREATE TABLE IF NOT EXISTS sc_rl_unified_research_environments (
    environment_id TEXT PRIMARY KEY,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_unified_research_environment_events (
    event_id BIGSERIAL PRIMARY KEY,
    environment_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_unified_environment_events_env ON sc_rl_unified_research_environment_events(environment_id);
CREATE TABLE IF NOT EXISTS sc_rl_unified_research_environment_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    environment_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
