# Sustainable Catalyst Research Librarian AI v7.0.6

A site-scoped connected research intelligence platform with transaction reconciliation, resumable knowledge-index recovery, and a visible public research workspace. See `docs/V705_TRANSACTION_RECONCILIATION_PUBLIC_INTERFACE.md`.

## v7.0.6 highlights

- Stages all 24 synchronization batches before index activation begins
- Queues backend activation through a short authenticated endpoint
- Runs the heavy SQLite replacement commit outside the WordPress request
- Polls durable commit status instead of waiting on a proxy-sensitive final response
- Reconciles empty 5xx and transport failures before declaring the rebuild failed
- Detects and safely retries stale activation after a Render restart
- Shows activation phase, progress, activated records, and retrieval chunks in the administration screen
- Retains the v7.0.5 visible public workspace and transaction-replay recovery
- Preserves the previous committed index until the replacement verifies
- Requires no paid vector database or persistent Render disk

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
- SQLite schema 10
- WordPress 6.0+
- Free-tier compatible; no paid vector database or persistent Render disk required

See `docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md` and `docs/INSTALL.md`.
