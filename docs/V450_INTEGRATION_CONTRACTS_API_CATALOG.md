# Research Librarian v4.5.0 — Integration Contracts, API Catalog, and Developer Handoffs

v4.5.0 adds a developer-facing contract layer for the Sustainable Catalyst Research Librarian. It documents the public REST surface, admin-only endpoints, response shapes, handoff payloads, shortcode surfaces, and integration notes needed to treat the Research Librarian as platform infrastructure.

## New endpoints

Public-safe:

- `GET /wp-json/sc-research-librarian-ai/v1/contracts/status`
- `GET /wp-json/sc-research-librarian-ai/v1/contracts/catalog`
- `GET /wp-json/sc-research-librarian-ai/v1/developer/catalog`

Admin-only:

- `GET /wp-json/sc-research-librarian-ai/v1/contracts/export`
- `GET /wp-json/sc-research-librarian-ai/v1/developer/export`

## New shortcodes

- `[sc_research_librarian mode="contracts-summary" title="Research Librarian Integration Contracts"]`
- `[sc_research_librarian_contracts_summary title="Research Librarian Integration Contracts"]`
- `[sc_research_librarian_api_catalog_summary title="Research Librarian API Catalog"]`

## Contract groups

- Route recommendation responses
- Source record and knowledge-index records
- Hybrid retrieval matches
- Workbench and Decision Studio handoff payloads
- Session and feedback records
- Governance, operations, security, curation, and release-review records

## Boundary

The contract layer is documentation and infrastructure support. It does not expose API keys, raw credentials, private diagnostics, or professional conclusions.
