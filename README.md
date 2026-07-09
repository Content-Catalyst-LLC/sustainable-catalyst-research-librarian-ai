# Sustainable Catalyst Research Librarian

Current release: **v4.5.0 — Integration Contracts, API Catalog, and Developer Handoffs**.

The Research Librarian is the source-aware routing, indexing, retrieval, handoff, governance, and operations layer for Sustainable Catalyst. It routes visitors to the right page, demo, article map, Workbench pathway, Decision Studio workflow, or feature suggestion route while preserving source context, confidence, feedback, governance, curation, and operations metadata.

## v4.5.0 focus

v4.5.0 adds an integration contract layer so the Research Librarian can be used as documented platform infrastructure. It provides public-safe contract status, API catalogs, developer handoff payload shapes, shortcode inventories, and admin-only contract exports.

## New v4.5.0 shortcodes

```text
[sc_research_librarian mode="contracts-summary" title="Research Librarian Integration Contracts"]
[sc_research_librarian_contracts_summary title="Research Librarian Integration Contracts"]
[sc_research_librarian_api_catalog_summary title="Research Librarian API Catalog"]
```

## New v4.5.0 endpoints

```text
GET /wp-json/sc-research-librarian-ai/v1/contracts/status
GET /wp-json/sc-research-librarian-ai/v1/contracts/catalog
GET /wp-json/sc-research-librarian-ai/v1/contracts/export
GET /wp-json/sc-research-librarian-ai/v1/developer/catalog
GET /wp-json/sc-research-librarian-ai/v1/developer/export
```

## Installation

1. Upload and activate `sustainable-catalyst-research-librarian-ai-plugin-v4.5.0.zip`.
2. Confirm plugin settings are preserved.
3. Rebuild the knowledge index if needed.
4. Regenerate embeddings if the index changed.
5. Review `Settings → Research Librarian Contracts` for API and handoff contracts.

## Boundary

Public contract endpoints are safe for page integrations. Admin exports are for maintenance and documentation review only. The plugin does not expose Gemini/OpenAI keys or raw credentials.
