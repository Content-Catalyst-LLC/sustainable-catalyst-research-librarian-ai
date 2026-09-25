CREATE TABLE IF NOT EXISTS sc_rl_research_graph_nodes(node_ref TEXT PRIMARY KEY,kind TEXT NOT NULL,label TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sc_rl_research_graph_edges(edge_id TEXT PRIMARY KEY,source_ref TEXT NOT NULL,target_ref TEXT NOT NULL,relation TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(source_ref,target_ref,relation));
CREATE TABLE IF NOT EXISTS sc_rl_research_graph_proposals(proposal_id TEXT PRIMARY KEY,record JSONB NOT NULL,status TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sc_rl_research_graph_events(event_id BIGSERIAL PRIMARY KEY,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS sc_rl_research_graph_snapshots(snapshot_id TEXT PRIMARY KEY,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_sc_rl_graph_edges_source ON sc_rl_research_graph_edges(source_ref);
CREATE INDEX IF NOT EXISTS idx_sc_rl_graph_edges_target ON sc_rl_research_graph_edges(target_ref);
CREATE INDEX IF NOT EXISTS idx_sc_rl_graph_edges_relation ON sc_rl_research_graph_edges(relation);
