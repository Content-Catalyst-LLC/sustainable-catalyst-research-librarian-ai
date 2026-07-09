# Sustainable Catalyst Research Librarian

Current release: **v4.8.0 — Guided Research Paths and Multi-Step Route Builder**.

The Research Librarian is the source-aware routing, indexing, retrieval, handoff, governance, operations, and guided-path layer for Sustainable Catalyst. It routes visitors to the right page, demo, article map, Workbench pathway, Decision Studio workflow, or feature suggestion route while preserving source context, confidence, feedback, governance, curation, integration contracts, and operations metadata.

## v4.8.0 focus

v4.8.0 adds guided research paths and a multi-step route builder. Instead of returning only one route card, the plugin can now build ordered paths with steps, checkpoints, route targets, handoff targets, confidence notes, and exportable path JSON.

## New v4.8.0 shortcodes

```text
[sc_research_librarian mode="guided-paths" title="Research Librarian Guided Paths"]
[sc_research_librarian mode="path-builder" title="Research Librarian Path Builder"]
[sc_research_librarian_paths_summary title="Research Librarian Guided Paths"]
[sc_research_librarian_path_builder title="Research Librarian Path Builder"]
```

## New v4.8.0 endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/paths/status
GET  /wp-json/sc-research-librarian-ai/v1/paths/catalog
POST /wp-json/sc-research-librarian-ai/v1/paths/build
POST /wp-json/sc-research-librarian-ai/v1/paths/save
GET  /wp-json/sc-research-librarian-ai/v1/paths/logs
GET  /wp-json/sc-research-librarian-ai/v1/paths/export
POST /wp-json/sc-research-librarian-ai/v1/paths/reset-defaults
```

## Installation

1. Upload and activate `sustainable-catalyst-research-librarian-ai-plugin-v4.8.0.zip`.
2. Confirm plugin settings are preserved.
3. Rebuild the knowledge index if needed.
4. Regenerate embeddings if the index changed.
5. Review `Settings → Research Librarian Paths` for guided-path templates and saved sessions.

## Boundary

Guided paths are route-planning and learning artifacts. They do not provide legal, financial, investment, medical, mental health, tax, engineering, architecture, compliance, assurance, ESG/SDG certification, or other professional advice.


## v4.8.0 Rebase Note

This release rebuilds guided research paths on top of the v4.6.0 public answer UX layer. It includes the polished public answer layout, source cards, confidence badges, Route Action Center, answer UX endpoints, guided path templates, and the multi-step route builder.


## v4.8.0 — Admin Query Review and Route Improvement Workflow

This release adds a review layer for route quality improvement. It ingests wrong-route feedback, missing-source reports, retrieval evaluation failures, low-confidence saved route sessions, and weak guided paths into an admin-only queue. Review items can be marked, exported, or converted into curation/source-index improvement work.

New public/admin surfaces include `/review/status`, `/review/queue`, `/review/ingest`, `/review/mark`, `/review/correction`, `/review/export`, and `[sc_research_librarian_query_review_summary]`.
