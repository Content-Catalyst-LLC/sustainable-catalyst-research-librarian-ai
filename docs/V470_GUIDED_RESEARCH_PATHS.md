# Research Librarian v4.7.0 — Guided Research Paths and Multi-Step Route Builder

v4.7.0 adds a guided-path layer on top of the Research Librarian routing, retrieval, handoff, and governance stack.

## Purpose

The path builder turns a visitor question into an ordered Sustainable Catalyst workflow. It helps a visitor move from orientation into the correct sequence of routes: platform pages, knowledge libraries, module demos, Workbench, Decision Studio, methodology, or feature suggestions.

## What it adds

- Guided research path templates
- Multi-step route builder endpoint
- Quick, standard, and deep path depth options
- Path confidence scoring
- Checkpoints and boundary notes
- Workbench / Decision Studio / module / feature-suggestion handoff targets
- Public path builder shortcode
- Saved path sessions
- Admin guided-path dashboard
- Exportable path JSON

## New shortcodes

```text
[sc_research_librarian mode="guided-paths" title="Research Librarian Guided Paths"]
[sc_research_librarian mode="path-builder" title="Research Librarian Path Builder"]
[sc_research_librarian_paths_summary title="Research Librarian Guided Paths"]
[sc_research_librarian_path_builder title="Research Librarian Path Builder"]
```

## New endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/paths/status
GET  /wp-json/sc-research-librarian-ai/v1/paths/catalog
POST /wp-json/sc-research-librarian-ai/v1/paths/build
POST /wp-json/sc-research-librarian-ai/v1/paths/save
GET  /wp-json/sc-research-librarian-ai/v1/paths/logs
GET  /wp-json/sc-research-librarian-ai/v1/paths/export
POST /wp-json/sc-research-librarian-ai/v1/paths/reset-defaults
```

## Boundary

Guided paths are routing artifacts. They do not provide legal, financial, medical, mental-health, tax, engineering, architecture, compliance, assurance, ESG/SDG certification, or other professional advice.
