-- Research Librarian AI v8.6.0
-- Source Identity, Deduplication & Citation Graph
-- Runtime migration is also performed idempotently by app.source_identity.SourceGraphStore.

CREATE TABLE IF NOT EXISTS sc_rl_canonical_sources (
    canonical_source_id TEXT PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'resolved',
    title TEXT NOT NULL DEFAULT '',
    normalized_title TEXT NOT NULL DEFAULT '',
    publication_year INTEGER,
    fallback_key TEXT NOT NULL DEFAULT '',
    fingerprint TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_canonical_sources_fallback
    ON sc_rl_canonical_sources(fallback_key) WHERE fallback_key <> '';

CREATE TABLE IF NOT EXISTS sc_rl_source_identifiers (
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    canonical_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(identifier_type, identifier_value)
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_source_identifiers_source
    ON sc_rl_source_identifiers(canonical_source_id);

CREATE TABLE IF NOT EXISTS sc_rl_source_instances (
    instance_id TEXT PRIMARY KEY,
    canonical_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,
    source_url TEXT NOT NULL DEFAULT '',
    filename TEXT NOT NULL DEFAULT '',
    media_type TEXT NOT NULL DEFAULT '',
    content_fingerprint TEXT NOT NULL DEFAULT '',
    version_label TEXT NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_source_instance_unique_url
    ON sc_rl_source_instances(canonical_source_id, source_url) WHERE source_url <> '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_source_instance_unique_hash
    ON sc_rl_source_instances(canonical_source_id, content_fingerprint) WHERE content_fingerprint <> '';

CREATE TABLE IF NOT EXISTS sc_rl_source_authors (
    canonical_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,
    author_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY(canonical_source_id, author_id)
);

CREATE TABLE IF NOT EXISTS sc_rl_source_institutions (
    canonical_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,
    institution_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    PRIMARY KEY(canonical_source_id, institution_id)
);

CREATE TABLE IF NOT EXISTS sc_rl_citation_edges (
    edge_id TEXT PRIMARY KEY,
    citing_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,
    cited_source_id TEXT NOT NULL REFERENCES sc_rl_canonical_sources(canonical_source_id) ON DELETE CASCADE,
    raw_reference TEXT NOT NULL DEFAULT '',
    reference_index INTEGER,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(citing_source_id, cited_source_id, reference_index)
);
CREATE INDEX IF NOT EXISTS idx_sc_rl_citation_out ON sc_rl_citation_edges(citing_source_id);
CREATE INDEX IF NOT EXISTS idx_sc_rl_citation_in ON sc_rl_citation_edges(cited_source_id);

CREATE TABLE IF NOT EXISTS sc_rl_source_resolution_events (
    event_id BIGSERIAL PRIMARY KEY,
    canonical_source_id TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);
