-- Research Librarian v7.1.1 — Fail-closed Neon identity metadata.
-- The application executes the authoritative idempotent migration at startup.
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS storage_backend text NOT NULL DEFAULT 'postgres';
ALTER TABLE sc_rl_generations
  ADD COLUMN IF NOT EXISTS database_fingerprint text NOT NULL DEFAULT '';

INSERT INTO sc_rl_meta(key, value)
VALUES
  ('schema_version', to_jsonb(2::int)),
  ('index_schema', to_jsonb('sc-research-librarian-postgres-index/1.1'::text)),
  ('storage_backend', to_jsonb('postgres'::text))
ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_utc = now();
