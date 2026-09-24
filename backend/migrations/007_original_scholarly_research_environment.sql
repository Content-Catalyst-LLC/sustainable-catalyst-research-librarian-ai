-- Research Librarian AI v9.2.0 — Original Research & Scholarly Research Environment
CREATE TABLE IF NOT EXISTS sc_rl_scholarly_studies (
  study_id TEXT PRIMARY KEY,
  core_project_id TEXT NOT NULL,
  local_project_id TEXT NOT NULL DEFAULT '',
  workflow_id TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL,
  record JSONB NOT NULL,
  study_fingerprint TEXT NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_scholarly_studies_project ON sc_rl_scholarly_studies(core_project_id, updated_utc);
CREATE INDEX IF NOT EXISTS idx_sc_rl_scholarly_studies_state ON sc_rl_scholarly_studies(state, updated_utc);

CREATE TABLE IF NOT EXISTS sc_rl_scholarly_study_revisions (
  revision_id BIGSERIAL PRIMARY KEY,
  study_id TEXT NOT NULL REFERENCES sc_rl_scholarly_studies(study_id) ON DELETE CASCADE,
  revision_number INTEGER NOT NULL,
  revision_hash TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  actor_ref TEXT NOT NULL DEFAULT '',
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(study_id, revision_number)
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_scholarly_revisions ON sc_rl_scholarly_study_revisions(study_id, revision_number);

CREATE TABLE IF NOT EXISTS sc_rl_scholarly_packages (
  package_id TEXT PRIMARY KEY,
  study_id TEXT NOT NULL REFERENCES sc_rl_scholarly_studies(study_id) ON DELETE CASCADE,
  package_hash TEXT NOT NULL,
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_scholarly_packages ON sc_rl_scholarly_packages(study_id, created_utc);
