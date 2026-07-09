# Changelog

## v4.5.0 — Integration Contracts, API Catalog, and Developer Handoffs

- Added integration contract layer for routing, source, retrieval, handoff, session, feedback, governance, and operations payloads.
- Added public-safe contract status and catalog endpoints.
- Added developer catalog endpoint with public-safe payload shapes and SDK examples.
- Added admin-only contract export and developer export endpoints.
- Added contract summary and API catalog shortcodes.
- Added admin Contracts page under Settings.
- Added v4.5.0 manifest and documentation.

## v4.4.0 — Editorial Curation, Route Overrides, and Source Weighting

- Added route override rules.
- Added source weighting rules.
- Added boundary pattern rules.
- Added admin curation dashboard.
- Added public-safe curation summary shortcode.
- Added admin-only curation rules/export endpoints.
- Added curation test endpoint.
- Integrated route overrides into deterministic route selection before keyword fallback.
- Integrated source weighting into source-priority scoring before hybrid ranking.
- Added v4.4.0 curation manifest and documentation.

## v4.3.0 — Observability, Operations Runbook, and Production Checks

- Added operational readiness score.
- Added admin Observability page.
- Added public-safe observability summary shortcode.
- Added admin-only observability events and export.
- Added operations runbook status and export endpoints.
- Added checks across index, embeddings, evaluation, handoffs, sessions, feedback, governance, maintenance, recovery, and security layers.
- Added `data/research_librarian_observability_manifest_v4.3.0.json`.
- Added `docs/V430_OBSERVABILITY_OPERATIONS_RUNBOOK.md`.

## 4.2.0 — Security Hardening, Endpoint Permissions, and Access Review

- Added security posture summary and public-safe security shortcode.
- Added endpoint access inventory that classifies public and admin-only surfaces.
- Added admin-only security audit and export endpoints.
- Added secret-safe diagnostics that expose fingerprints rather than raw API keys.
- Added warnings for missing Gemini fingerprints, empty indexes, long retention windows, and disabled export redaction.
- Added Research Librarian Security admin page.
- Added v4.2.0 security manifest and documentation.

## 4.1.0 — Index Snapshots, Backup, and Recovery Readiness

- Added admin recovery snapshot dashboard.
- Added recovery status, create, export, restore, and delete endpoints.
- Added public-safe recovery summary shortcode.
- Added dry-run restore planning.
- Added snapshot retention limit.
- Added recovery manifest and documentation.
- Strips embedding vectors from snapshots while preserving embedding status summaries.


## 4.0.0 — Enterprise Readiness and Release Audit

- Added enterprise readiness summary.
- Added release audit summary.
- Added aggregate checks across index, retrieval, evaluation, handoffs, sessions, feedback, governance, and maintenance.
- Added public-safe enterprise summary shortcode.
- Added public-safe release audit shortcode.
- Added admin-only enterprise export endpoint.
- Added admin-only release export endpoint.
- Added endpoint, shortcode, and manifest inventories.
- Added v4.0.0 enterprise manifest and documentation.

# Changelog

## 3.9.0 — Scheduled Index Maintenance, Sitemap Sync, and Health Alerts

- Added scheduled knowledge-index maintenance.
- Added WordPress cron hook and maintenance schedule sync action.
- Added manual maintenance run action.
- Added optional sitemap URL ingestion.
- Added maintenance status/export REST endpoints.
- Added maintenance-summary shortcode.
- Added health/alert configuration for index maintenance.

# Changelog

## v3.8.0 — Governance, Privacy Controls, and Retention Policies

- Added governance status endpoint.
- Added admin governance export endpoint.
- Added purge-expired governance helper.
- Added governance summary shortcode.
- Added retention policy defaults for sessions, feedback, evaluation, and handoffs.
- Added export redaction option for question/note fields.
- Added public privacy posture summary and admin-only export boundary summary.
- Updated plugin version metadata to 3.8.0.

## 3.7.0 — Feedback, Correction Queue, and Knowledge Gap Triage

- Added public feedback actions for helpful routes and route issues.
- Added feedback records, triage labels, and knowledge-gap review logging.
- Added admin feedback dashboard and exportable feedback JSON.
- Added feedback summary shortcode and REST endpoints.
- Added feedback log limit setting and clear-feedback admin action.


## v3.6.0 — Saved Route Sessions and Admin Analytics

- Added saved route-session records for useful Research Librarian outputs.
- Added public assistant **Save session** action.
- Added `/session/save`, `/session/logs`, `/session/export`, and `/analytics/summary` REST endpoints.
- Added admin analytics for common routes, handoff targets, confidence distribution, and recent saved sessions.
- Added session export and clear-session admin controls.
- Added public `session-summary` and `analytics-summary` shortcode modes.
- Added session log limit setting.
- Preserved v3.5.0 handoff payload behavior and v3.4.0 evaluation behavior.


## v3.5.0 — Workbench and Decision Studio Handoff Payloads

- Added structured handoff payload generation for Workbench, Decision Studio, module artifacts, Feature Suggestions, and knowledge-route follow-up.
- Added `/handoff/schema`, `/handoff/prepare`, `/handoff/logs`, and `/handoff/export` REST endpoints.
- Added `handoff_payload` to exported route notes.
- Added public `[sc_research_librarian mode="handoff-summary"]` shortcode.
- Added handoff JSON download button to the assistant UI.
- Added handoff target inference, source-context preservation, assumptions/register seeds, Decision Packet seed objects, Workbench analysis-intent objects, and module artifact field recommendations.
- Added handoff log summary and admin-only handoff log export.


## 3.4.0 — Retrieval Evaluation, Confidence Tuning, and Failure Logs

- Added retrieval evaluation suite for standard Sustainable Catalyst routing prompts.
- Added expected-route comparison and pass/fail labels.
- Added confidence threshold settings for high/medium route confidence.
- Added source-coverage checks and weak-source warnings.
- Added keyword vs semantic score breakdown for top source matches.
- Added evaluation failure logs and admin export endpoint.
- Added admin dashboard section for evaluation results.
- Added evaluation summary shortcode.
- Added REST endpoints for suite, run, query, logs, and export.
- Preserved v3.3.3 Gemini key-persistence and embedding queue behavior.

# Changelog

## 3.7.0 — Feedback, Correction Queue, and Knowledge Gap Triage

- Added public feedback actions for helpful routes and route issues.
- Added feedback records, triage labels, and knowledge-gap review logging.
- Added admin feedback dashboard and exportable feedback JSON.
- Added feedback summary shortcode and REST endpoints.
- Added feedback log limit setting and clear-feedback admin action.


## v3.3.3 — Gemini Key Persistence and Batch Credential Fix

- Added protected API-key replacement fields so blank password inputs cannot overwrite saved keys.
- Added explicit clear-key checkboxes for Gemini and OpenAI credentials.
- Added placeholder/masked/autofill/incomplete-key detection.
- Added saved-key and last-run key fingerprints to diagnostics without exposing secrets.
- Added key fingerprint metadata to embedding status, single tests, and batch runs.
- Improved admin guidance for batch embedding after successful single embedding tests.

## v3.3.2 — Embedding Queue, Rate Limit Handling, and Key Preservation

- Added resumable Gemini embedding generation.
- Added delay and retry settings for more stable free-tier embedding jobs.
- Added saved-key fingerprint diagnostics without exposing the key.
- Preserved existing embeddings when later batches fail.
- Improved distinction between key/auth failures and temporary rate-limit/server failures.


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
