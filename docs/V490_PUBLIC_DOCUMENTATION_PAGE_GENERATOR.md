# Research Librarian v4.9.0 — Public Documentation Page Generator

v4.9.0 adds a public documentation layer for the Sustainable Catalyst Research Librarian. It generates a public-safe documentation catalog, page outline, shortcode inventory, endpoint summary, and JSON export that can be used to maintain the Research Librarian public page and supporting documentation.

## What it adds

- Documentation catalog for the Research Librarian product surface
- Generated public documentation page payload
- Generated HTML and Markdown documentation sections
- Shortcode inventory for public assistant and infrastructure summaries
- Endpoint group summary for routing, retrieval, handoffs, guided paths, documentation, and admin-only routes
- Admin Documentation dashboard
- Public-safe documentation summary shortcode
- Admin-only documentation export

## Public shortcodes

```text
[sc_research_librarian mode="documentation-summary" title="Research Librarian Documentation"]
[sc_research_librarian_documentation_summary title="Research Librarian Documentation"]
[sc_research_librarian_docs_catalog title="Research Librarian Documentation Catalog"]
[sc_research_librarian_documentation_page title="Research Librarian Public Documentation"]
```

## REST endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/documentation/status
GET  /wp-json/sc-research-librarian-ai/v1/documentation/catalog
GET  /wp-json/sc-research-librarian-ai/v1/documentation/page
POST /wp-json/sc-research-librarian-ai/v1/documentation/generate
GET  /wp-json/sc-research-librarian-ai/v1/documentation/export
POST /wp-json/sc-research-librarian-ai/v1/documentation/reset
```

## Boundary

The documentation generator is public-safe by design. It does not expose API keys, raw session logs, raw feedback logs, private diagnostics, or regulated conclusions.
