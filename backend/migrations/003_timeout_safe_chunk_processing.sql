-- Research Librarian v7.1.2 — Timeout-safe chunk processing.
-- The application executes the authoritative idempotent migration at startup.
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS chunk_batch_limit integer NOT NULL DEFAULT 5;
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS chunk_timeout_count integer NOT NULL DEFAULT 0;
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS last_step_duration_ms integer NOT NULL DEFAULT 0;
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS last_step_records integer NOT NULL DEFAULT 0;
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS last_step_outcome text NOT NULL DEFAULT '';
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS last_step_started_utc timestamptz;
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS last_step_completed_utc timestamptz;

INSERT INTO sc_rl_meta(key, value)
VALUES
  ('schema_version', to_jsonb(3::int)),
  ('index_schema', to_jsonb('sc-research-librarian-postgres-index/1.2'::text))
ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_utc = now();
