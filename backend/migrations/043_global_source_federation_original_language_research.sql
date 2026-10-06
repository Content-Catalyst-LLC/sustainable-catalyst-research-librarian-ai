-- Research Librarian AI v12.3.0
-- Global Source Federation & Original-Language Research.
-- Research Librarian stores federation research context and provenance.
-- Knowledge Library/connectors remain source-ingestion authorities.
-- Cross-language entity/toponym resolution remains deferred to v12.4.0.

CREATE TABLE IF NOT EXISTS sc_rl_global_source_federation_projects(
    federation_id TEXT PRIMARY KEY,
    owner_ref TEXT NOT NULL,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_global_source_federation_projects_owner
    ON sc_rl_global_source_federation_projects(owner_ref);

CREATE TABLE IF NOT EXISTS sc_rl_global_source_federation_events(
    event_id BIGSERIAL PRIMARY KEY,
    federation_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_global_source_federation_events_project
    ON sc_rl_global_source_federation_events(federation_id);

CREATE TABLE IF NOT EXISTS sc_rl_global_source_federation_snapshots(
    snapshot_id TEXT PRIMARY KEY,
    federation_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_global_source_federation_snapshots_project
    ON sc_rl_global_source_federation_snapshots(federation_id);
