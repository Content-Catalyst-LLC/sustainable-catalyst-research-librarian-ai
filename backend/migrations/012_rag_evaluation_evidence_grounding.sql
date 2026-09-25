CREATE TABLE IF NOT EXISTS sc_rl_rag_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    context_id TEXT NOT NULL,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sc_rl_rag_evaluations_context_idx ON sc_rl_rag_evaluations(context_id);

CREATE TABLE IF NOT EXISTS sc_rl_rag_evaluation_cases (
    case_id TEXT PRIMARY KEY,
    evaluation_id TEXT NOT NULL,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sc_rl_rag_evaluation_cases_evaluation_idx ON sc_rl_rag_evaluation_cases(evaluation_id);

CREATE TABLE IF NOT EXISTS sc_rl_rag_claim_assessments (
    assessment_id TEXT PRIMARY KEY,
    evaluation_id TEXT NOT NULL,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sc_rl_rag_claim_assessments_evaluation_idx ON sc_rl_rag_claim_assessments(evaluation_id);

CREATE TABLE IF NOT EXISTS sc_rl_rag_citation_assessments (
    assessment_id TEXT PRIMARY KEY,
    evaluation_id TEXT NOT NULL,
    record JSONB NOT NULL,
    record_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sc_rl_rag_citation_assessments_evaluation_idx ON sc_rl_rag_citation_assessments(evaluation_id);

CREATE TABLE IF NOT EXISTS sc_rl_rag_evaluation_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    evaluation_id TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    record JSONB NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sc_rl_rag_evaluation_snapshots_evaluation_idx ON sc_rl_rag_evaluation_snapshots(evaluation_id);

CREATE TABLE IF NOT EXISTS sc_rl_rag_evaluation_events (
    event_id BIGSERIAL PRIMARY KEY,
    evaluation_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor_ref TEXT NOT NULL,
    payload JSONB NOT NULL,
    event_hash TEXT NOT NULL,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sc_rl_rag_evaluation_events_evaluation_idx ON sc_rl_rag_evaluation_events(evaluation_id, created_utc);
