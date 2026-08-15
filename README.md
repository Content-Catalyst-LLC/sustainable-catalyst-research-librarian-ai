# Sustainable Catalyst Research Librarian AI v7.2.0

A site-scoped connected research intelligence platform with Library-native research objects, bounded research contexts, Neon/Postgres durable indexing, verified retrieval, Gemini semantic search, transaction recovery, and a visible public research workspace. See `docs/V720_LIBRARY_OBJECT_MODEL_RESEARCH_CONTEXT_ALIGNMENT.md`.

## v7.2.0 highlights

- Adds a typed Knowledge Library object model for sources, publications, recommendations, saved searches, watchlists, research queues, source bundles, Research Rooms, pathways, and Workspace references.
- Adds saved research contexts spanning Sustainable Catalyst Collection, My Library, Current Project, and Current Research Room without collapsing source provenance.
- Adds context-aware retrieval priority for verified indexed records referenced by the selected context.
- Adds authenticated WordPress context selection and server-side owner resolution before private context reaches FastAPI.
- Treats Library/project/room metadata as untrusted scoping metadata rather than instructions or verified evidence.
- Includes linked Library objects in portable project backups.

## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI uses Neon/Postgres for production knowledge generations, source records, retrieval chunks, and pgvector embeddings. SQLite remains the local-development and ancillary governance/workspace/Library-context store in v7.2.0. Generation is isolated behind `sc-generation-adapter/1.0`; deterministic retrieval and project continuity remain usable when generation is unavailable.

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

`/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/library/object-model`, `/v1/library/objects`, `/v1/research/contexts`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- Neon-compatible PostgreSQL with pgvector for the production knowledge index
- SQLite schema 13 for local development and ancillary platform/Library-context records
- WordPress 6.0+
- No Render persistent disk is required

See `docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md` and `docs/INSTALL.md`.
