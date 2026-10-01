CREATE TABLE IF NOT EXISTS sc_rl_runtime_authority_snapshots(
  snapshot_id TEXT PRIMARY KEY,
  snapshot_hash TEXT NOT NULL,
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
