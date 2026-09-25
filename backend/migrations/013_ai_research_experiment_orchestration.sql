CREATE TABLE IF NOT EXISTS sc_rl_ai_research_experiments (
    experiment_id TEXT PRIMARY KEY, record JSONB NOT NULL, record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_ai_research_trials (
    trial_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, record JSONB NOT NULL, record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_ai_research_trials_experiment ON sc_rl_ai_research_trials(experiment_id);
CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_handoffs (
    handoff_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, record JSONB NOT NULL, record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_ai_experiment_handoffs_experiment ON sc_rl_ai_experiment_handoffs(experiment_id);
CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_run_receipts (
    receipt_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, record JSONB NOT NULL, record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_ai_experiment_receipts_experiment ON sc_rl_ai_experiment_run_receipts(experiment_id);
CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_evaluation_bindings (
    binding_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, record JSONB NOT NULL, record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_ai_experiment_bindings_experiment ON sc_rl_ai_experiment_evaluation_bindings(experiment_id);
CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_snapshots (
    snapshot_id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, snapshot_hash TEXT NOT NULL, record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sc_rl_ai_experiment_events (
    event_id BIGSERIAL PRIMARY KEY, experiment_id TEXT NOT NULL, event_type TEXT NOT NULL, actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL, event_hash TEXT NOT NULL, created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_ai_experiment_events_experiment ON sc_rl_ai_experiment_events(experiment_id, created_utc);
