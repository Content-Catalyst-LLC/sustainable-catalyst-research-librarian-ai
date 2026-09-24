-- Research Librarian AI v9.1.0 — Research Automation & Durable Workflow Engine
CREATE TABLE IF NOT EXISTS sc_rl_research_workflows (
  workflow_id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  run_id TEXT NOT NULL UNIQUE,
  core_project_id TEXT NOT NULL,
  local_project_id TEXT NOT NULL DEFAULT '',
  record JSONB NOT NULL,
  workflow_fingerprint TEXT NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_utc TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_research_workflows_state ON sc_rl_research_workflows(state, updated_utc);
CREATE TABLE IF NOT EXISTS sc_rl_research_workflow_events (
  event_id BIGSERIAL PRIMARY KEY,
  workflow_id TEXT NOT NULL REFERENCES sc_rl_research_workflows(workflow_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  stage TEXT NOT NULL DEFAULT '',
  actor_ref TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL DEFAULT '',
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_research_workflow_events ON sc_rl_research_workflow_events(workflow_id,event_id);
CREATE TABLE IF NOT EXISTS sc_rl_research_workflow_checkpoints (
  checkpoint_id BIGSERIAL PRIMARY KEY,
  workflow_id TEXT NOT NULL REFERENCES sc_rl_research_workflows(workflow_id) ON DELETE CASCADE,
  checkpoint_hash TEXT NOT NULL,
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_research_workflow_checkpoints ON sc_rl_research_workflow_checkpoints(workflow_id,checkpoint_id);
