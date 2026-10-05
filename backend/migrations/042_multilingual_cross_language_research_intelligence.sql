-- Research Librarian AI v12.2.0
-- Multilingual & Cross-Language Research Intelligence
-- Original-language-first research context and transformation provenance.
-- Global source federation and new source ingestion remain deferred to v12.3.0.

CREATE TABLE IF NOT EXISTS sc_rl_multilingual_research_projects(
    multilingual_research_id TEXT PRIMARY KEY,
    owner_ref TEXT NOT NULL,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_multilingual_research_projects_owner
    ON sc_rl_multilingual_research_projects(owner_ref);

CREATE TABLE IF NOT EXISTS sc_rl_multilingual_research_events(
    event_id BIGSERIAL PRIMARY KEY,
    multilingual_research_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_multilingual_research_events_project
    ON sc_rl_multilingual_research_events(multilingual_research_id);

CREATE TABLE IF NOT EXISTS sc_rl_multilingual_research_snapshots(
    snapshot_id TEXT PRIMARY KEY,
    multilingual_research_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_multilingual_research_snapshots_project
    ON sc_rl_multilingual_research_snapshots(multilingual_research_id);
