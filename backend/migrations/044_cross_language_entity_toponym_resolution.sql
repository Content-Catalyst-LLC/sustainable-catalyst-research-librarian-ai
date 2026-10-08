CREATE TABLE IF NOT EXISTS sc_rl_cross_language_resolution_projects(
    resolution_id TEXT PRIMARY KEY,
    owner_ref TEXT NOT NULL,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_language_resolution_projects_owner
    ON sc_rl_cross_language_resolution_projects(owner_ref);

CREATE TABLE IF NOT EXISTS sc_rl_cross_language_resolution_events(
    event_id BIGSERIAL PRIMARY KEY,
    resolution_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_language_resolution_events_project
    ON sc_rl_cross_language_resolution_events(resolution_id);

CREATE TABLE IF NOT EXISTS sc_rl_cross_language_resolution_snapshots(
    snapshot_id TEXT PRIMARY KEY,
    resolution_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_language_resolution_snapshots_project
    ON sc_rl_cross_language_resolution_snapshots(resolution_id);
