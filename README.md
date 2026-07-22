# Sustainable Catalyst Research Librarian AI v7.1.0

A site-scoped connected research intelligence platform with Neon/Postgres durable indexing, verified retrieval, Gemini semantic search, transaction recovery, and a visible public research workspace. See `docs/V710_NEON_POSTGRES_DURABLE_INDEX.md`.

## v7.1.0 highlights

- Neon/Postgres is the production knowledge-index store.
- `pgvector` persists semantic embeddings outside Render's ephemeral filesystem.
- Each rebuild creates an invisible generation and switches the active pointer only after record, chunk, and checksum verification.
- Existing WordPress staging files can replay failed v7.0.x rebuilds directly into Neon.
- SQLite remains the default for local development and ancillary governance/workspace data.


## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI uses Neon/Postgres for production knowledge generations, source records, retrieval chunks, and pgvector embeddings. SQLite remains the local-development and ancillary governance/workspace store in v7.1.0. Generation is isolated behind `sc-generation-adapter/1.0`; deterministic retrieval and project continuity remain usable when generation is unavailable.

## Public shortcodes

- `[sustainable_catalyst_research_librarian_ai]`
- `[sc_research_librarian]`
- `[sc_connected_research_workspace]`
- `[sc_research_projects_summary]`
- `[sc_connected_research_platform_status]`
- `[sc_research_librarian_methodology]`
- `[sc_research_librarian_governance_status]`
- `[sc_research_librarian_platform_handoffs]`

## Backend resources

`/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- Neon-compatible PostgreSQL with pgvector for the production knowledge index
- SQLite schema 12 for local development and ancillary platform records
- WordPress 6.0+
- No Render persistent disk is required

See `docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md` and `docs/INSTALL.md`.
