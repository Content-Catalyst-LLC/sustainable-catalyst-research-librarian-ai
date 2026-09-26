CREATE TABLE IF NOT EXISTS sc_rl_argument_claim_counterclaim_intelligence (
    argument_intelligence_id TEXT PRIMARY KEY,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_argument_claim_counterclaim_events (
    event_id BIGSERIAL PRIMARY KEY,
    argument_intelligence_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_argument_claim_counterclaim_events_project
    ON sc_rl_argument_claim_counterclaim_events(argument_intelligence_id);
CREATE TABLE IF NOT EXISTS sc_rl_argument_claim_counterclaim_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    argument_intelligence_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
