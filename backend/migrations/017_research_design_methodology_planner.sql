-- Research Librarian v10.2.0 — Research Design & Methodology Planner
CREATE TABLE IF NOT EXISTS sc_rl_research_design_plans (
    plan_id TEXT PRIMARY KEY,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_research_design_plan_events (
    event_id BIGSERIAL PRIMARY KEY,
    plan_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_research_design_plan_events_plan ON sc_rl_research_design_plan_events(plan_id);
CREATE TABLE IF NOT EXISTS sc_rl_research_design_plan_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
