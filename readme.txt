=== Sustainable Catalyst Research Librarian ===
Contributors: Content Catalyst LLC
Tags: research, routing, ai, gemini, embeddings, knowledge index
Requires at least: 6.0
Tested up to: 6.7
Stable tag: 5.0.0
License: MIT

A site-scoped Research Librarian for Sustainable Catalyst with source-aware routing, route notes, handoff payloads, saved route sessions, admin analytics, a knowledge indexer, and optional Gemini embeddings for hybrid retrieval, and security/access review tooling.

== Description ==

The Research Librarian helps visitors choose the right Sustainable Catalyst route: Knowledge Library, Platform, Demos, Decision Studio, Workbench, Catalyst modules, Methodology, Feature Suggestions, or GitHub repositories.

v4.7.1 adds guided research paths and a multi-step route builder so visitors can move from a question into ordered Sustainable Catalyst workflows with steps, checkpoints, handoffs, and exportable path JSON.

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

== Changelog ==

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

= 5.0.0 =
* Stable public release, launch checklist, and acceptance gate.
* Public-safe readiness score and launch checklist shortcodes.
* Admin acceptance runner and release export.
