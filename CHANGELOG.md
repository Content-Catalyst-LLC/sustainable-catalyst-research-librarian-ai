# Changelog

## v3.3.1 — Gemini Embedding Diagnostics and Request Format Fix

- Added a single-record Gemini embedding test button in the admin dashboard.
- Added admin diagnostics with HTTP status, error code, first failed source record, raw response excerpt, and recommended next step.
- Added `/retrieval/diagnostics` and `/retrieval/test-embedding` endpoints.
- Updated Gemini embedding requests to use `x-goog-api-key` server-side header authentication.
- Added model normalization for `gemini-embedding-001` and `models/gemini-embedding-001`.
- Added `embedContentConfig` with task type, title, auto-truncation, and optional output dimensionality.
- Added failure early-stop logic to avoid repeated full-index failures during setup.
- Improved status output for all-failed embedding attempts.


## v3.3.0 — Gemini Retrieval Backend with Embeddings

- Added optional Gemini embeddings for indexed Sustainable Catalyst source records.
- Added hybrid source retrieval using route rules, keyword scoring, record priority, and semantic similarity.
- Added Gemini embedding model setting with `gemini-embedding-001` default.
- Added embedding provider, source limit, semantic weight, and keyword weight settings.
- Added admin **Generate Gemini Embeddings** action.
- Added retrieval status dashboard data and embedded-record counts.
- Added REST endpoints for retrieval status, retrieval query, and index embedding generation.
- Added public retrieval-status shortcode mode.
- Updated AI prompt grounding so Gemini/OpenAI receive matched source records, confidence, and handoff context.
- Updated route notes to preserve retrieval mode and scores for matched sources.
- Updated README, docs, plugin metadata, CSS/JS, and validation checks.

## v3.2.0 — Knowledge Indexer and Admin Crawl Dashboard

- Added Knowledge Indexer and Crawl Dashboard.
- Added local knowledge index option storage.
- Added seed-plus-WordPress-content index rebuild workflow.
- Added stale record, metadata warning, duplicate URL, and route coverage summary logic.
- Added admin rebuild/reset/export controls.
- Added REST endpoints for index summary, index records, rebuild, and export.
- Added public index-summary shortcode mode.
- Updated health response with index summary.
- Updated grounded routing to use the knowledge index when available.
- Updated README, docs, CSS, and plugin metadata.

## v3.1.0 — Grounded Routing and Source-Aware Recommendations

- Added grounding source index.
- Added route confidence scoring, reason codes, ambiguity notes, and handoffs.
- Added source-aware route notes and exports.

## v3.0.0 — Product Routing Layer Upgrade

- Reframed Research Librarian as the routing layer for Sustainable Catalyst.
- Added route map, landing mode, route note exports, and provider options.
