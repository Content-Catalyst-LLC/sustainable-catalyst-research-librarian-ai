CREATE TABLE IF NOT EXISTS sc_rl_wordpress_migration_runs(
  run_id TEXT PRIMARY KEY,
  source_site TEXT NOT NULL,
  source_instance TEXT NOT NULL DEFAULT '',
  actor_ref TEXT NOT NULL DEFAULT '',
  inventory_hash TEXT NOT NULL,
  state TEXT NOT NULL,
  candidate_count INTEGER NOT NULL DEFAULT 0,
  migratable_count INTEGER NOT NULL DEFAULT 0,
  duplicate_count INTEGER NOT NULL DEFAULT 0,
  conflict_count INTEGER NOT NULL DEFAULT 0,
  blocked_count INTEGER NOT NULL DEFAULT 0,
  compatibility_count INTEGER NOT NULL DEFAULT 0,
  applied_count INTEGER NOT NULL DEFAULT 0,
  failed_count INTEGER NOT NULL DEFAULT 0,
  record JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_migration_runs_site
  ON sc_rl_wordpress_migration_runs(source_site,created_utc DESC);

CREATE TABLE IF NOT EXISTS sc_rl_wordpress_migration_candidates(
  candidate_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  source_site TEXT NOT NULL,
  source_type TEXT NOT NULL,
  legacy_id TEXT NOT NULL,
  owner_key TEXT NOT NULL DEFAULT '',
  parent_legacy_id TEXT NOT NULL DEFAULT '',
  fingerprint TEXT NOT NULL,
  classification TEXT NOT NULL,
  target_type TEXT NOT NULL DEFAULT '',
  target_id TEXT NOT NULL DEFAULT '',
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY(run_id) REFERENCES sc_rl_wordpress_migration_runs(run_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_migration_candidates_run
  ON sc_rl_wordpress_migration_candidates(run_id,classification,source_type);
CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_migration_candidates_legacy
  ON sc_rl_wordpress_migration_candidates(source_site,source_type,legacy_id);

CREATE TABLE IF NOT EXISTS sc_rl_wordpress_migration_receipts(
  receipt_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  candidate_id TEXT NOT NULL,
  source_site TEXT NOT NULL,
  source_type TEXT NOT NULL,
  legacy_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  outcome TEXT NOT NULL,
  target_type TEXT NOT NULL DEFAULT '',
  target_id TEXT NOT NULL DEFAULT '',
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(candidate_id,fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_migration_receipts_run
  ON sc_rl_wordpress_migration_receipts(run_id,created_utc DESC);

CREATE TABLE IF NOT EXISTS sc_rl_wordpress_compatibility_aliases(
  alias_id TEXT PRIMARY KEY,
  source_site TEXT NOT NULL,
  source_type TEXT NOT NULL,
  legacy_id TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(source_site,source_type,legacy_id)
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_compatibility_alias_target
  ON sc_rl_wordpress_compatibility_aliases(target_type,target_id);
