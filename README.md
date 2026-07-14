# Sustainable Catalyst Research Librarian AI v7.0.0

A site-scoped connected research intelligence platform for Sustainable Catalyst.

## v7.0.0 highlights

- Persistent, private-by-default research projects
- Multi-step investigations and project event history
- Evidence, annotation, reading-path, contradiction, uncertainty, workflow, and artifact entities
- Reusable Workbench, Decision Studio, Site Intelligence, Lab, and evidence-review workflow templates
- Stable `sc-connected-research-api/1.0` resource contract
- Provider-independent generation adapter with deterministic fallback
- Portable checksum-verified project backup and dry-run import
- Public, editorial, and institutional workspace modes
- Existing hybrid retrieval, verified citations, durable recovery, typed handoffs, and governance retained
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
