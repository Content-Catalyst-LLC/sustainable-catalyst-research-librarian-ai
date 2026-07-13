=== Sustainable Catalyst Research Librarian ===
Contributors: Content Catalyst LLC
Tags: research, routing, ai, gemini, embeddings, knowledge index
Requires at least: 6.0
Tested up to: 6.7
Stable tag: 6.4.1
License: MIT

A site-scoped Research Librarian for Sustainable Catalyst with calibrated hybrid retrieval, benchmarked ranking, verified citations, durable indexing, and deterministic evidence fallback.

== Description ==

Research Librarian AI retrieves Sustainable Catalyst publications and documents through exact-title priority, section-aware BM25 ranking, optional Gemini embeddings, calibrated reciprocal-rank fusion, and citation-verified synthesis. WordPress remains the canonical publishing and recovery source, while FastAPI provides a durable SQLite runtime index compatible with free Render infrastructure.

v6.4.1 adds persistent ranking profiles, lexical-versus-hybrid benchmarks, confusing-title protection, minimum-evidence gates, unsupported-claim detection, source weighting, exclusions, context budgets, and retrieval latency diagnostics.

== Shortcodes ==

[sustainable_catalyst_research_librarian_ai]
[sc_research_librarian]
[sc_research_librarian mode="landing"]
[sc_research_librarian mode="route-map"]
[sc_research_librarian mode="index-summary"]
[sc_research_librarian mode="retrieval-status"]
[sc_research_librarian mode="evaluation-summary"]
[sc_research_librarian mode="handoff-summary"]
[sc_research_librarian mode="session-summary"]
[sc_research_librarian mode="analytics-summary"]
[sc_research_librarian mode="security-summary"]
[sc_research_librarian mode="guided-paths"]
[sc_research_librarian mode="path-builder"]
[sc_research_librarian_paths_summary]
[sc_research_librarian_path_builder]
[sc_research_librarian_security_summary]
[sc_research_librarian_article_path_embed]
[sc_research_librarian_article_map_summary]
[sc_research_librarian_article_route_cards]

== Changelog ==

= 6.4.1 =
* Adds persistent, bounded retrieval profiles in SQLite schema version 6.
* Adds administrator controls for structural, lexical, semantic, and RRF weights, evidence thresholds, context limits, source multipliers, and exclusions.
* Adds a packaged golden-query benchmark comparing lexical-only and calibrated hybrid retrieval.
* Persists hit-at-1, hit-at-3, MRR, ambiguity, missing-result, and latency metrics.
* Detects near-duplicate titles and requests clarification instead of silently choosing.
* Blocks AI synthesis when evidence count, score, lexical, semantic, or ambiguity requirements are not met.
* Rejects low-overlap paragraphs, unsupported numeric claims, unknown citation labels, and unknown generated URLs.
* Preserves v6.4.0 hybrid retrieval, v6.3.x recovery hardening, and the black-and-green prompt with light answer cards.

= 6.3.0 =
* Replaces the ephemeral JSON runtime index with a transactional SQLite knowledge index.
* Stages every expected batch before atomically committing a full replacement.
* Adds idempotent sync jobs, duplicate-batch protection, content hashes, tombstones, and incremental insert/update/delete processing.
* Creates private compressed WordPress snapshots as the canonical recovery source.
* Automatically rehydrates an empty backend from the latest verified WordPress snapshot.
* Adds backend manifests, sync ledgers, checksums, runtime snapshots, and administrator rollback controls.
* Preserves v6.2.1 endpoint diagnostics, rate-limit improvements, nonce retry, and terminal prompt styling.

= 6.2.1 =
* Makes canonical published WordPress records take precedence over summary-only legacy index entries.
* Adds per-job and per-batch sync reporting with eligible, collected, skipped, duplicate, accepted, and rejected totals.
* Adds precise WordPress, nonce, backend, integration-key, empty-index, provider-quota, and rate-limit diagnostics.
* Adds authenticated backend testing, one-click endpoint repair and full resynchronization, WP-Cron visibility, and public rate-limit reset controls.
* Replaces fixed hourly counting with rolling public request windows and `Retry-After` responses while exempting authenticated editors by default.
* Adds one safe nonce refresh and retry for questions and title suggestions.
* Restyles the public question textarea with a black background and accessible green terminal text while preserving light answer and source-card surfaces.

= 6.2.0 =
* Adds the Render-ready FastAPI knowledge intelligence backend.
* Synchronizes the full public Sustainable Catalyst library across eligible public post types.
* Adds exact-title, slug, heading, series, article-map, taxonomy, summary, and content ranking.
* Adds grounded Gemini synthesis, related-title discovery, research paths, and short session continuity.
* Adds the dedicated Python Intelligence administration page and secure server-to-server integration.
* Replaces the beta-style route-card-first interface with a production answer-first experience.
* Keeps direct WordPress AI provider operation as an optional fallback under Advanced.


= 6.1.1 =
* Accepts modern Google AI Studio authorization keys, including URL-safe period characters.
* Adds administrator guidance for standard-key restriction and authorization-key migration.
* Adds actionable diagnostics for invalid keys, permission failures, unavailable models, quota limits, and temporary provider errors.
* Preserves v6.1.0 live AI status, country-aware Site Intelligence routing, and consolidated administration.

= 6.1.0 =
* Restored the live AI provider as the primary public experience with visible operational status.
* Added administrator provider tests, exact error diagnostics, latency and success/failure history, and Gemini model discovery.
* Added country recognition and first-class Site Intelligence routing, including Pakistan to PAK Country Intelligence.
* Replaced first-match fallback routing with weighted route selection.
* Added Site Intelligence, Country Intelligence, Cross-Domain Comparison, Dashboard Studio, Sources and Methodology, and Public Observatories source records.
* Added a dedicated top-level Research Librarian AI menu and removed the module list from WordPress Settings.
* Added public AI status and administrator AI test/model REST endpoints.
* Updated Gemini authentication, system instructions, model normalization, timeout handling, and structured provider errors.


= 6.0.1 =
* Removed the self-detecting class guard that prevented v6.0.0 from bootstrapping.
* Added a collision-safe v6 bootstrap with unique internal class and helper names.
* Restored Settings links, admin pages, and shortcodes when a legacy Research Librarian class is loaded first.
* Added a visible legacy-class source notice with reflected file and version information.
* Raised core shortcode, REST, settings, and admin registration priority so v6 remains authoritative.
* Tightened duplicate-plugin detection so the diagnostics plugin is not misclassified as a Research Librarian copy.


= 6.0.0 =
* Added the Integrated Research Guidance Platform command center.
* Unified routing, article maps, platform actions, feedback, demand intelligence, adaptive surveys, and closed-loop improvement.
* Added public platform and journey shortcodes plus protected status and export endpoints.
* Added versioned integrated-platform schemas and privacy-minimized health events.
* Preserved human approval and regression protection across route changes.




= 5.9.0 =
* Added rule-based adaptive prompt and survey experiences.
* Added low-confidence, zero-source, route-abandonment, path-completion, tool-demand, and handoff triggers.
* Added consent-aware evaluation, daily frequency caps, cooldowns, and dismissal suppression.
* Added Feature Suggestions survey handoffs and custom integration filters/actions.
* Added aggregate adaptive-experience analytics and privacy-minimized Site Intelligence events.
* Added the [sc_research_librarian_adaptive_experience] shortcode and protected rules/analytics endpoints.

= 5.7.0 =
* Added Research Demand and Knowledge-Gap Intelligence administration dashboard.
* Added 30-day, 90-day, and all-time aggregate demand windows.
* Added route demand, topic clusters, low-confidence routes, missing-source clusters, missing-tool clusters, and evaluation-failure signals.
* Added advisory demand-and-coverage opportunity scoring with human-review boundaries.
* Added protected demand report, refresh, and export REST endpoints.
* Added optional privacy-thresholded public demand summary shortcode and endpoint.
* Added aggregate Site Intelligence refresh events and a daily refresh schedule.

= 5.6.0 =

* Added the Feature Suggestions Feedback Bridge.
* Added contextual route ratings and correction reports.
* Added missing-source, missing-topic, missing-tool, and answer-grounding reports.
* Added receipt-protected status and duplicate protection.
* Added local queue fallback and privacy-minimized shared events.

= 5.5.0 =
* Added stable operations readiness dashboard, daily checks, migration and recovery validation, integration health, operations exports, audit history, and public release notes.

= 5.3.2 =
* Added article path embeds, article map integration, contextual route templates, and article-map REST endpoints.

= 4.9.1 =
* Adds guided research paths, multi-step route builder, path sessions, checkpoints, handoff targets, and exportable path JSON.

= 4.5.0 =
* Adds integration contracts, API catalog, developer handoff documentation, public-safe contract summaries, and admin-only contract exports.

= 4.2.0 =
* Added security hardening, endpoint permissions, and access review.
* Added security status/endpoints/run-audit/export REST endpoints.
* Added security-summary shortcode and admin security dashboard.
* Added secret-safe diagnostics and endpoint access classification.

= 4.1.0 =
* Added index snapshots, backup, and recovery readiness.


= 3.7.0 =
- Adds feedback, source-correction queue, and knowledge-gap triage.

= 3.6.0 =
* Added saved route sessions and admin analytics.
* Added Save session button to the assistant UI.
* Added session save/log/export and analytics summary REST endpoints.
* Added session-summary and analytics-summary shortcode modes.
* Added session log limit setting and admin clear/export actions.

= 3.3.0 =
* Added Gemini Retrieval Backend with Embeddings.
* Added hybrid keyword + semantic source retrieval.
* Added retrieval status/query endpoints and index embedding endpoint.
* Added Generate Gemini Embeddings admin action.
* Added retrieval-status shortcode mode.

= 3.2.0 =
* Added Knowledge Indexer and Admin Crawl Dashboard.
* Added index summary, index records, rebuild, and export endpoints.
* Added public index-summary shortcode mode.
* Updated grounded routing to use the knowledge index when available.

= 3.1.0 =
* Added grounded routing and source-aware recommendations.

= 3.0.0 =
* Added product routing layer.


== Changelog ==

= 5.5.0 =
* Added stable operations readiness dashboard, daily checks, migration and recovery validation, integration health, operations exports, audit history, and public release notes.

= 5.3.2 =
* Added article path embeds, article map integration, contextual route templates, and article-map REST endpoints.

= 4.9.1 =
* Adds guided research paths, multi-step route builder, path sessions, checkpoints, handoff targets, and exportable path JSON.

= 4.5.0 =
* Adds integration contracts, API catalog, developer handoff documentation, public-safe contract summaries, and admin-only contract exports.

= 3.7.0 =
- Adds feedback, source-correction queue, and knowledge-gap triage.

= 3.6.0 =
* Added saved route sessions and admin analytics.
* Added Save session button to the assistant UI.
* Added session save/log/export and analytics summary REST endpoints.
* Added session-summary and analytics-summary shortcode modes.
* Added session log limit setting and admin clear/export actions.

= 3.3.1 =
* Gemini embedding diagnostics and request-format reliability build.
* Adds single-record embedding test, admin diagnostics JSON, clearer errors, model normalization, and x-goog-api-key request header support.


= 3.4.0 =
* Added resumable Gemini embedding batches.
* Added delay/retry settings for rate-limit stability.
* Added saved-key fingerprint diagnostics.

= 3.4.0 =
* Protect Gemini/OpenAI keys from blank, masked, autofilled, or incomplete overwrites.
* Add last-run key fingerprint diagnostics for embedding tests and batches.

= 3.4.0 =
* Added retrieval evaluation suite, confidence tuning, source coverage checks, failure logs, and evaluation exports.


= 3.5.0 =
* Added structured Workbench, Decision Studio, module artifact, feature suggestion, and knowledge-route handoff payloads.
* Added handoff schema, prepare, logs, and export endpoints.
* Added handoff summary shortcode and assistant handoff JSON download.


= 3.8.0 =
* Added governance, privacy, retention, and export-control layer.
* Added governance status/export endpoints and governance summary shortcode.


= 4.1.0 =
* Added recovery snapshots, backup/export controls, dry-run restore planning, and migration readiness.

= 4.0.0 =
* Enterprise readiness and release audit layer.
* Public-safe readiness and release audit shortcodes.
* Admin-only enterprise and release exports.

= 3.9.0 =
* Adds scheduled index maintenance, sitemap sync, maintenance status/export endpoints, and maintenance-summary shortcode.


= 4.4.0 =
* Added editorial curation, route overrides, source weighting, boundary pattern controls, admin curation dashboard, curation exports, and public-safe curation summary.

= 4.3.0 =
* Added observability status, operational runbook endpoints, admin event logs, and production readiness checks.


= 4.9.1 =
* Added admin query review and route improvement workflow.
* Added review queue ingestion from feedback, evaluation failures, route sessions, and guided paths.
* Added review/correction REST endpoints and public-safe review summary shortcode.

= 4.9.1 =
* Fixed documentation snapshot generation so the admin action visibly saves and refreshes the snapshot.
* Added nonce-protected admin-post fallback actions for generate, export, and reset.
* Added admin success/reset notices, generated documentation preview, and copy-ready Markdown output.


== Changelog ==

= 5.5.0 =
* Added stable operations readiness dashboard, daily checks, migration and recovery validation, integration health, operations exports, audit history, and public release notes.

= 5.3.2 =
* Added article path embeds, article map integration, contextual route templates, and article-map REST endpoints.

= 5.0.0 =
* Stable public release, launch checklist, and acceptance gate.
* Public-safe readiness score and launch checklist shortcodes.
* Admin acceptance runner and release export.


== v5.1.0 ==
Live public experience QA, visitor prompt library, QA checklist, and UX calibration layer.

= 5.3.2 =
* Fixes activation conflicts caused by versioned plugin folder packaging and duplicate active copies.


= 5.3.2 =
* Added duplicate activation notice cleanup and stale active-plugin repair.
* Added activation status and activation repair diagnostics.
* Preserved v5.3.1 article-map features.

= 5.4.0 =
* Added public Workbench and Decision Studio deep-link actions with typed, time-limited handoffs and safe fallback navigation.

## Closed-loop route improvement

v5.9.0 converts reviewed feedback into versioned route-change proposals with deterministic before/after tests, regression gates, human approval, provenance, audit history, and rollback snapshots. Approved changes are applied through the existing editorial curation registry.
