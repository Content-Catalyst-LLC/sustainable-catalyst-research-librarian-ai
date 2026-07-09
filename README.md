# Sustainable Catalyst Research Librarian v3.2.0

The Sustainable Catalyst Research Librarian is the routing and source-aware retrieval layer for the Sustainable Catalyst platform. It helps visitors choose the right Sustainable Catalyst starting point: Knowledge Library, Platform, Platform Demos, Decision Studio, Workbench, Catalyst Canvas, Catalyst Data, Analytics R, Global Impact Catalyst, Narrative Risk, Catalyst Finance, Catalyst Grit, Methodology, Feature Suggestions, or GitHub repositories.

v3.2.0 adds a Knowledge Indexer and Admin Crawl Dashboard on top of the v3.1.0 grounded routing layer.

## What it does

- Provides deterministic route recommendations with confidence, reason codes, source support, and handoffs.
- Supports optional Gemini or OpenAI responses while keeping routing scoped to Sustainable Catalyst.
- Maintains a curated route map and grounding source index.
- Builds a local knowledge index from curated source records plus recent published WordPress pages/posts.
- Flags missing summaries, missing topics, stale records, duplicate URLs, and failed crawl records.
- Exposes index summary, records, rebuild, and export endpoints.
- Produces exportable route notes and route JSON.

## v3.2.0 endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/index/summary
GET  /wp-json/sc-research-librarian-ai/v1/index/records
POST /wp-json/sc-research-librarian-ai/v1/index/rebuild
GET  /wp-json/sc-research-librarian-ai/v1/index/export
```

Existing endpoints remain:

```text
POST /wp-json/sc-research-librarian-ai/v1/ask
GET  /wp-json/sc-research-librarian-ai/v1/routes
GET  /wp-json/sc-research-librarian-ai/v1/sources
POST /wp-json/sc-research-librarian-ai/v1/grounded-route
GET  /wp-json/sc-research-librarian-ai/v1/health
```

## Shortcodes

```text
[sustainable_catalyst_research_librarian_ai]
[sc_research_librarian title="Sustainable Catalyst Research Librarian"]
[sc_research_librarian mode="landing" title="Sustainable Catalyst Research Librarian"]
[sc_research_librarian mode="route-map" title="Research Librarian Route Map"]
[sc_research_librarian mode="index-summary" title="Research Librarian Knowledge Index"]
```

## Admin workflow

Go to **Settings → Research Librarian**.

The v3.2.0 admin page includes:

- Knowledge Indexer and Crawl Dashboard
- indexed record count
- route group count
- metadata warning count
- stale record count
- last indexed timestamp
- rebuild index button
- reset to seed index button
- export index JSON link
- indexed source table

## Boundaries

The Research Librarian is educational routing infrastructure. It does not provide legal, financial, medical, tax, engineering, compliance, assurance, ESG/SDG certification, or regulated-information advice.

MIT-licensed.
