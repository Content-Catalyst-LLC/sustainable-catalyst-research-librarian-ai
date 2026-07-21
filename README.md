# Sustainable Catalyst Research Librarian AI v7.0.5

A site-scoped connected research intelligence platform with transaction reconciliation, resumable knowledge-index recovery, and a visible public research workspace. See `docs/V705_TRANSACTION_RECONCILIATION_PUBLIC_INTERFACE.md`.

## v7.0.5 highlights

- Repairs v7.0.4 final-batch failures without rediscovering the source library
- Authenticated backend transaction status with received and missing batch diagnostics
- Durable local staging replay with bounded batches and two-attempt recovery limit
- **Repair and Resume Commit** action for stopped production jobs
- Visible single-column public research workspace with eight readable mode cards
- Light question surface, prominent Start Research action, and secondary tools behind progressive disclosure
- Visitor-safe verified-fallback status language instead of provider-oriented failure copy
- Broader discovery of published document-style custom post types from v7.0.2
- Persistent, private-by-default research projects
- Multi-step investigations and project event history
- Stable `sc-connected-research-api/1.0` resource contract
- Provider-independent generation adapter with deterministic fallback
- Existing hybrid retrieval, verified citations, typed handoffs, governance, and portable recovery retained
- Additive SQLite schema version 10

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
