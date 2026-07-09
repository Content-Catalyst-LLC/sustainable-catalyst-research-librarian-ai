# Sustainable Catalyst Research Librarian AI

Current version: **v4.9.0 — Public Documentation Page Generator**.

The Research Librarian is the source-aware routing, retrieval, guided-path, and documentation layer for Sustainable Catalyst. It combines deterministic routing, source-aware recommendations, a knowledge index, Gemini embeddings, public answer UX, guided research paths, handoff payloads, query review, governance, maintenance, recovery, security, observability, curation, integration contracts, and now public-safe documentation generation.

## v4.9.0 highlights

- Public documentation page generator
- Documentation catalog
- Generated HTML and Markdown documentation payloads
- Shortcode inventory
- Endpoint group summary
- Admin Documentation dashboard
- Admin-only documentation export
- Public-safe documentation summary shortcode

## Main shortcode

```text
[sc_research_librarian title="Sustainable Catalyst Research Librarian"]
```

## Documentation shortcodes

```text
[sc_research_librarian mode="documentation-summary" title="Research Librarian Documentation"]
[sc_research_librarian_documentation_summary title="Research Librarian Documentation"]
[sc_research_librarian_docs_catalog title="Research Librarian Documentation Catalog"]
[sc_research_librarian_documentation_page title="Research Librarian Public Documentation"]
```

## Documentation endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/documentation/status
GET  /wp-json/sc-research-librarian-ai/v1/documentation/catalog
GET  /wp-json/sc-research-librarian-ai/v1/documentation/page
POST /wp-json/sc-research-librarian-ai/v1/documentation/generate
GET  /wp-json/sc-research-librarian-ai/v1/documentation/export
POST /wp-json/sc-research-librarian-ai/v1/documentation/reset
```
