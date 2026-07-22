-- Research Librarian v7.1.0 — Neon Postgres durable index
-- The application runs the same idempotent migration automatically at startup.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sc_rl_meta (
    key text PRIMARY KEY,
    value jsonb NOT NULL,
    updated_utc timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sc_rl_generations (
    generation_id text PRIMARY KEY,
    job_id text UNIQUE NOT NULL,
    source_site text NOT NULL DEFAULT '',
    mode text NOT NULL DEFAULT 'replace',
    state text NOT NULL DEFAULT 'staging',
    commit_phase text NOT NULL DEFAULT 'staged',
    commit_progress integer NOT NULL DEFAULT 0,
    expected_batches integer NOT NULL DEFAULT 0,
    received_batches integer[] NOT NULL DEFAULT '{}',
    staged_records integer NOT NULL DEFAULT 0,
    staged_deletions integer NOT NULL DEFAULT 0,
    rejected_records integer NOT NULL DEFAULT 0,
    activation_records integer NOT NULL DEFAULT 0,
    activation_total integer NOT NULL DEFAULT 0,
    indexed_chunks integer NOT NULL DEFAULT 0,
    chunk_records_processed integer NOT NULL DEFAULT 0,
    checksum_records integer NOT NULL DEFAULT 0,
    activation_cursor text NOT NULL DEFAULT '',
    chunk_cursor text NOT NULL DEFAULT '',
    checksum_cursor text NOT NULL DEFAULT '',
    activation_checksum text NOT NULL DEFAULT '',
    activation_step_count integer NOT NULL DEFAULT 0,
    activation_restart_count integer NOT NULL DEFAULT 0,
    recovery_generation integer NOT NULL DEFAULT 0,
    active boolean NOT NULL DEFAULT false,
    error text NOT NULL DEFAULT '',
    result jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_utc timestamptz NOT NULL DEFAULT now(),
    updated_utc timestamptz NOT NULL DEFAULT now(),
    commit_started_utc timestamptz,
    commit_heartbeat_utc timestamptz,
    completed_utc timestamptz
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_one_active_generation
ON sc_rl_generations(active) WHERE active;

-- Remaining batch, record, chunk, rejection, and embedding-run tables are
-- created by backend/app/postgres_store.py. This file is intentionally a
-- human-readable bootstrap, while the application migration is authoritative.
