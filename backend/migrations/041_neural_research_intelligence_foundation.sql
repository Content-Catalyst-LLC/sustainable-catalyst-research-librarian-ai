-- Research Librarian AI v12.1.0
-- Neural Research Intelligence Foundation
-- Research-side neural object registry and provenance ledger.
-- Model contracts remain governed by Platform Core; execution remains in specialist runtimes.

CREATE TABLE IF NOT EXISTS sc_rl_neural_research_projects(
    neural_research_id TEXT PRIMARY KEY,
    owner_ref TEXT NOT NULL,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_neural_research_projects_owner
    ON sc_rl_neural_research_projects(owner_ref);

CREATE TABLE IF NOT EXISTS sc_rl_neural_research_events(
    event_id BIGSERIAL PRIMARY KEY,
    neural_research_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_neural_research_events_project
    ON sc_rl_neural_research_events(neural_research_id);

CREATE TABLE IF NOT EXISTS sc_rl_neural_research_snapshots(
    snapshot_id TEXT PRIMARY KEY,
    neural_research_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_neural_research_snapshots_project
    ON sc_rl_neural_research_snapshots(neural_research_id);
