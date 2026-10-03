CREATE TABLE IF NOT EXISTS sc_rl_persistent_research_sessions(
  session_id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  client_ref TEXT NOT NULL DEFAULT '',
  project_id TEXT NOT NULL DEFAULT '',
  scientist_environment_id TEXT NOT NULL DEFAULT '',
  research_context_ref TEXT NOT NULL DEFAULT '',
  record JSONB NOT NULL,
  record_hash TEXT NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sc_rl_persistent_research_sessions_client
  ON sc_rl_persistent_research_sessions(client_ref, updated_utc DESC);
CREATE INDEX IF NOT EXISTS idx_sc_rl_persistent_research_sessions_project
  ON sc_rl_persistent_research_sessions(project_id, updated_utc DESC);

CREATE TABLE IF NOT EXISTS sc_rl_persistent_research_turns(
  turn_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  role TEXT NOT NULL,
  record JSONB NOT NULL,
  record_hash TEXT NOT NULL,
  previous_turn_hash TEXT NOT NULL DEFAULT '',
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(session_id, sequence)
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_persistent_research_turns_session
  ON sc_rl_persistent_research_turns(session_id, sequence);

CREATE TABLE IF NOT EXISTS sc_rl_persistent_research_session_snapshots(
  snapshot_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  snapshot_hash TEXT NOT NULL,
  record JSONB NOT NULL,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_persistent_research_session_snapshots_session
  ON sc_rl_persistent_research_session_snapshots(session_id, created_utc DESC);
