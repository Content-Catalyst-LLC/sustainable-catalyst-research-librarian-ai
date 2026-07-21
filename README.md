# Sustainable Catalyst Research Librarian AI v7.0.7

A site-scoped connected research intelligence platform with restart-safe knowledge-index activation, verified retrieval, and a visible public research workspace. See `docs/V707_DURABLE_INCREMENTAL_INDEX_ACTIVATION.md`.

## v7.0.7 highlights

- Removes long-running FastAPI in-process background activation
- Advances activation through short authenticated `commit/step` requests
- Copies records, builds retrieval chunks, and verifies checksums in bounded persisted batches
- Resumes after backend process restarts without resetting durable cursors
- Upgrades existing v7.0.6 queued or activating transactions in place
- Keeps the previous active index untouched until the verified atomic switch
- Replays the complete WordPress staging file when ephemeral backend state disappears
- Shows shadow-record, chunked-record, verified-record, and durable-step progress
- Supports `SC_RL_DATA_DIR` for a persistent backend disk
- Preserves Gemini generation, semantic indexing, deterministic fallback, and human control

## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI provides durable SQLite research state, retrieval, project services, cross-product handoffs, governance, and backup verification. Generation is isolated behind `sc-generation-adapter/1.0`; retrieval and project continuity remain usable when generation is unavailable.

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
- SQLite schema 11
- WordPress 6.0+
- No paid vector database is required; persistent backend storage is recommended for strongest restart durability

See `docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md` and `docs/INSTALL.md`.
