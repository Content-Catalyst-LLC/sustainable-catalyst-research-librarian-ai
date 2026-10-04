CREATE TABLE IF NOT EXISTS sc_rl_identities(
  identity_id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  password_salt TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  failed_login_count INTEGER NOT NULL DEFAULT 0,
  locked_until TIMESTAMPTZ,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_identities_role
  ON sc_rl_identities(role,status);

CREATE TABLE IF NOT EXISTS sc_rl_identity_sessions(
  auth_session_id TEXT PRIMARY KEY,
  identity_id TEXT NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL,
  client_label TEXT NOT NULL DEFAULT '',
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_utc TIMESTAMPTZ NOT NULL,
  last_seen_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_utc TIMESTAMPTZ,
  revoke_reason TEXT NOT NULL DEFAULT '',
  FOREIGN KEY(identity_id) REFERENCES sc_rl_identities(identity_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_identity_sessions_identity
  ON sc_rl_identity_sessions(identity_id,state,expires_utc DESC);
CREATE INDEX IF NOT EXISTS idx_sc_rl_identity_sessions_expiry
  ON sc_rl_identity_sessions(state,expires_utc);

CREATE TABLE IF NOT EXISTS sc_rl_identity_access_events(
  event_id TEXT PRIMARY KEY,
  identity_id TEXT NOT NULL DEFAULT '',
  auth_session_id TEXT NOT NULL DEFAULT '',
  action TEXT NOT NULL,
  outcome TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_identity_access_events_identity
  ON sc_rl_identity_access_events(identity_id,created_utc DESC);
