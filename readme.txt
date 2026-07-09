=== Sustainable Catalyst Research Librarian ===
Contributors: Content Catalyst LLC
Tags: research, routing, ai, gemini, embeddings, knowledge index
Requires at least: 6.0
Tested up to: 6.7
Stable tag: 4.3.0
License: MIT

A site-scoped Research Librarian for Sustainable Catalyst with source-aware routing, route notes, handoff payloads, saved route sessions, admin analytics, a knowledge indexer, and optional Gemini embeddings for hybrid retrieval, and security/access review tooling.

== Description ==

The Research Librarian helps visitors choose the right Sustainable Catalyst route: Knowledge Library, Platform, Demos, Decision Studio, Workbench, Catalyst modules, Methodology, Feature Suggestions, or GitHub repositories.

v4.2.0 adds endpoint security review, admin/public access classification, secret-safe diagnostics, and a security-readiness summary on top of the recovery and enterprise-readiness layers.

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
[sc_research_librarian_security_summary]

== Changelog ==

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


= 4.3.0 =
* Added observability status, operational runbook endpoints, admin event logs, and production readiness checks.
