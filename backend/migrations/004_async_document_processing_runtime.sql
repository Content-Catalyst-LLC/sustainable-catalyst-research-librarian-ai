-- Research Librarian v8.3.0 — Durable asynchronous ingestion/document-processing jobs.
-- The application performs the authoritative idempotent migration at startup.
CREATE TABLE IF NOT EXISTS sc_rl_async_jobs (
    job_id text PRIMARY KEY,
    job_type text NOT NULL,
    state text NOT NULL,
    priority integer NOT NULL DEFAULT 100,
    idempotency_key text NOT NULL DEFAULT '',
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    result jsonb NOT NULL DEFAULT '{}'::jsonb,
    error text NOT NULL DEFAULT '',
    attempts integer NOT NULL DEFAULT 0,
    max_attempts integer NOT NULL DEFAULT 3,
    progress integer NOT NULL DEFAULT 0,
    stage text NOT NULL DEFAULT 'queued',
    worker_id text NOT NULL DEFAULT '',
    lease_expires_utc timestamptz,
    available_utc timestamptz NOT NULL DEFAULT now(),
    created_utc timestamptz NOT NULL DEFAULT now(),
    updated_utc timestamptz NOT NULL DEFAULT now(),
    started_utc timestamptz,
    completed_utc timestamptz,
    fingerprint text NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_async_jobs_idempotency
    ON sc_rl_async_jobs(idempotency_key) WHERE idempotency_key <> '';
CREATE INDEX IF NOT EXISTS idx_sc_rl_async_jobs_claim
    ON sc_rl_async_jobs(state, available_utc, priority, created_utc);
CREATE TABLE IF NOT EXISTS sc_rl_async_job_events (
    event_id bigserial PRIMARY KEY,
    job_id text NOT NULL REFERENCES sc_rl_async_jobs(job_id) ON DELETE CASCADE,
    event_type text NOT NULL,
    stage text NOT NULL DEFAULT '',
    message text NOT NULL DEFAULT '',
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_utc timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_async_job_events_job
    ON sc_rl_async_job_events(job_id, event_id);
