=== Sustainable Catalyst Research Librarian ===
Contributors: Content Catalyst LLC
Tags: research, routing, ai, gemini, embeddings, knowledge index
Requires at least: 6.0
Tested up to: 6.7
Stable tag: 9.2.0
License: MIT

A connected, site-scoped research intelligence platform for Sustainable Catalyst with persistent projects, verified retrieval, typed workflows, governance, and portable recovery.

== Description ==

Research Librarian AI retrieves Sustainable Catalyst publications and documents through exact-title priority, section-aware BM25 ranking, optional Gemini embeddings, calibrated reciprocal-rank fusion, and citation-verified synthesis. WordPress remains the canonical publishing and recovery source, while FastAPI stores the production knowledge index durably in Neon Postgres with pgvector.

v8.0.0 unifies Library context, federated discovery, evidence evaluation, persistent research state, Research Rooms, synthesis, Workspace promotion, and preservation through an inspectable eight-stage research lifecycle. Readiness is descriptive; every lifecycle stage transition remains an explicit human action.


v9.2.0 adds the Original Research & Scholarly Research Environment. Research projects can now maintain durable studies with frozen protocols, explicit post-freeze deviations, provenance-rich results, human-authored interpretations and manuscript sections, publication-readiness checks, immutable revisions, and frozen reproducibility packages. The environment does not create authorship, certify peer review, accept claims, interpret significance, or promote truth automatically.

v8.12.0 adds Visual Research Intelligence. Reviewed sources, citations, evidence, findings, claims, arguments, statistical reasoning objects, provenance, and timelines can be assembled into renderer-neutral visual research plans and explicitly promoted into Platform Core visual reasoning objects after human review. The Librarian does not render, infer graph edges, compute layout, or promote visual form to truth.

v8.7.0 adds the Core Evidence Bridge. Hydrated canonical Librarian sources can be promoted to governed Platform Core source snapshots, and selected passages can be promoted to Core evidence records with durable cross-system bindings. Promotions default to neutral/unreviewed with no inferred confidence; Platform Core remains the governed evidence/reasoning authority.

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
[sc_research_librarian_platform_handoffs]

== Changelog ==

= 9.2.0 =
* Added durable Original Research & Scholarly Research study registry.
* Added protocol freeze with immutable hashes and explicit post-freeze deviations.
* Added provenance-rich result registration tied to evidence, specialist runtimes, statistical reasoning, and visuals.
* Added human-authored interpretations and manuscript sections.
* Added publication-readiness checks, immutable study revisions, and frozen reproducibility packages.
* Preserved human authorship, explicit review, Platform Core governance, and no automatic truth promotion.


= 8.12.0 =
* Add Visual Research Intelligence plans for citation networks, evidence/claim/finding maps, contradiction maps, argument graphs, statistical views, provenance graphs, timelines, and source lineage.
* Add explicit human-reviewed promotion into Platform Core Visual Reasoning objects and unified research-session visual bindings.
* Preserve renderer-neutral semantics and source-hash provenance while leaving layout/render execution to specialist visual runtimes.
* Forbid inferred graph edges, automatic claim/finding promotion, visual truth promotion, argument ranking, and statistical interpretation.


= 8.7.0 =
* Add the Core Evidence Bridge for canonical-source snapshot and passage-evidence promotion.
* Add immutable Librarian↔Core bindings with deterministic Core IDs and idempotency metadata.
* Reject citation-only stubs and require a synchronized Core snapshot before passage promotion.
* Default promoted passages to neutral, unreviewed, and no inferred confidence.
* Preserve Platform Core as the governed evidence, review, claim, reasoning, lineage, and reproducibility authority.

= 8.6.0 =
* Add durable Postgres canonical source identity with SQLite local/test fallback.
* Normalize DOI, arXiv, PMID, ISBN, and canonical URLs before bibliographic fallback matching.
* Add alternate source instances, author/institution links, and fail-closed identifier conflict handling.
* Add persistent citation edges, cited-work stubs, and later stub hydration.
* Integrate canonical identity into v8.5 document ingestion before durable indexing.
* Add authenticated source identity and citation graph APIs while preserving Platform Core governance.

= 8.5.0 =
* Added deterministic document intelligence and scholarly parsing.
* Added PDF, HTML, Markdown, and text structural extraction.
* Added references, citation mentions, scholarly identifiers, figures, tables, equations, and page provenance.
* Added synchronous and durable asynchronous document parsing APIs.
* Preserved Platform Core as the governed evidence and reasoning authority.

= 8.4.0 =
* Add deterministic multi-query planning using only user-supplied query text.
* Add advanced rank fusion and transparent reranking over exact-title, BM25, optional semantic retrieval, and RRF.
* Add typed research filters for source, content type, series, records, URL prefixes, taxonomies, and modified dates.
* Add canonical URL/content-hash/near-duplicate suppression and bounded diversity selection.
* Add query-plan and expanded retrieval diagnostics while keeping retrieval scores separate from evidence-quality/truth judgments.
* Preserve Platform Core v3.3+ as the governed evidence/reasoning authority and retain the v8.3 durable asynchronous processing runtime.

= 8.0.0 =
* Add the persistent Frame → Discover → Evaluate → Organize → Collaborate → Synthesize → Promote → Preserve research lifecycle.
* Add deterministic stage-readiness signals, blockers, and next actions without automatic stage advancement.
* Require authenticated human confirmation for stage transitions and retain explicit transition lineage.
* Add immutable SHA-256-fingerprinted lifecycle checkpoints and include lifecycle lineage in project backup/import.
* Preserve existing federated Save to My Library, personal/room provenance, and explicit Workspace import boundaries.
* Advance ancillary SQLite schema to 18, Connected Research API to 2.0, and public workspace to 3.0; Neon/Postgres knowledge-index schema remains 13.0.

= 7.7.0 =
* Add fixed-provider federated research discovery for OpenAlex, Crossref, Europe PMC, Open Library, and arXiv.
* Normalize and deduplicate external records while preserving provider identity and provider-specific record provenance.
* Persist federated search snapshots in the ancillary research workspace ledger for audit, project backup, and research continuity.
* Add explicit Save to My Library import as private `external-reference` objects; discovery alone does not create evidence or editorial approval.
* Add partial-provider failure reporting, provider/access signals, recent-search history, and authenticated WordPress discovery UI.
* Advance ancillary SQLite schema to 17, Connected Research API to 1.6, and public workspace to 2.6; Neon/Postgres knowledge-index schema remains 13.0.

= 7.6.0 =
* Add governed Workspace promotion for Notebook, Evidence Set, Analysis, Document, and Citation Pack seeds.
* Prepare versioned fingerprinted handoff packets instead of silently importing or publishing Workspace artifacts.
* Preserve source owner, Library scope, object type, source fingerprints, project linkage, and Research Room attribution.
* Keep personal research state and shared room state distinct in exported provenance.
* Exclude rejected sources by default while allowing explicit opt-in inclusion.
* Require explicit Workspace import and validate export/import receipts against the prepared packet fingerprint.
* Resolve owner/actor identity and context/project/room/object access server-side through WordPress.
* Include Workspace promotion packets and receipts in project backup/import.
* Advance ancillary SQLite to schema 16 and connected API/workspace contracts to 1.5/2.5; the Neon knowledge index remains schema 13.0 with no Postgres migration.

= 7.5.0 =
* Add durable Research Rooms with Owner, Editor, Researcher, and Viewer membership roles.
* Add shared evidence state that preserves original Library ownership, source scope, and provenance.
* Add collaborative questions, participant-attributed disagreement positions, and participant activity history.
* Add bounded room synthesis and room-to-Librarian-context promotion without treating collaboration metadata as evidence.
* Resolve actor identity server-side through WordPress and require active room membership for room-scoped context.
* Keep v7.4 personal reading/review/rejection state separate from shared room state.
* Include project-linked room state in portable backup/import.
* Advance ancillary SQLite to schema 15 and connected API/workspace contracts to 1.4/2.4; the Neon knowledge index remains schema 13.0 with no Postgres migration.

= 7.4.0 =
* Add a durable research activity ledger for saved-context searches and explicit workflow actions.
* Add per-object unread, reading, reviewed, and rejected state plus contradiction flags and resolution.
* Add an explicit open-question register with open, resolved, deferred, and dismissed states.
* Add authenticated Research state workspace controls and source-level reading/review actions.
* Keep research state inspectable and editable while explicitly preventing it from becoming factual evidence.
* Keep rejected objects in provenance while deprioritizing them from context-priority retrieval unless revisited.
* Include research activity, object state, and open questions in project backup/import.
* Advance ancillary SQLite to schema 14 and connected API/workspace contracts to 1.3/2.3; no Neon/Postgres knowledge-index migration is required.

= 7.3.0 =
* Add descriptive source profiles covering source type, evidence role, publisher/institution, publication date, methodology, citations, access, provenance, and limitations.
* Add side-by-side evidence comparison and source-mix/provider-diversity summaries.
* Add deterministic structural evidence-gap detection.
* Add authenticated context-wide evidence review in the Connected Research Workspace.
* Carry bounded quality metadata with authorized research context objects without treating metadata as verified evidence.
* Explicitly prohibit truth scores, credibility scores, automatic winners, and automatic source rejection.
* Advance the connected API/workspace contracts to 1.2/2.2 with no database migration.

= 7.2.0 =
* Add Library-native object types for sources, publications, recommendations, saved searches, watchlists, research queues, source bundles, Research Rooms, pathways, and Workspace references.
* Add saved research contexts for Sustainable Catalyst Collection, My Library, Current Project, and Current Research Room.
* Resolve private context server-side for the authenticated WordPress owner before forwarding bounded metadata to FastAPI.
* Prioritize verified indexed records referenced by the selected context without treating private metadata as evidence.
* Preserve editorial, personal, project, and Research Room provenance boundaries.
* Include linked Library objects in project backup and advance the ancillary SQLite schema to 13.

= 7.1.2 =
* Process five Neon source records per chunk step by default.
* Persist the chunk cursor after every record and bulk-insert each record's chunks.
* Adapt chunk batch size to measured step duration.
* Reconcile cURL timeout 28 against durable Neon state before retrying.
* Prevent overlapping retries and show chunk-step diagnostics.

= 7.1.1 =
* Verify pooled and direct Neon connection identity at startup.
* Run idempotent Postgres migrations automatically.
* Block production SQLite fallback when Neon is configured.
* Recover committed-empty jobs by replaying the preserved staging file.
* Verify active generation records, chunks, pointer, and database fingerprint.

= 7.1.0 =
* Adds Neon Postgres as the durable production knowledge-index store.
* Stores vectors with pgvector and activates verified generations atomically.
* Recovers preserved WordPress staging files without requiring Render persistent disks.
* Adds database diagnostics and Neon free-tier storage reporting.

= 7.0.7 =
* Removes FastAPI in-process background activation from the index rebuild path.
* Adds a bounded authenticated commit-step endpoint with durable SQLite cursors.
* Copies shadow records, builds chunks, and verifies the replacement in resumable batches.
* Upgrades existing v7.0.6 queued and activating transactions without source rediscovery.
* Preserves the previous active index until one verified atomic SQLite switch.
* Replays the WordPress staging file when ephemeral backend transaction state is lost.
* Adds shadow-record, chunked-record, verified-record, durable-step, and storage diagnostics.
* Adds configurable activation batch limits and persistent SC_RL_DATA_DIR support.

= 7.0.2 =
* Added broader published-document discovery, four-stage readiness, and simplified index controls.
* Added runtime verification, snapshot recovery, and resumable semantic-index completion.

= 7.0.0 =
* Adds the Connected Research Intelligence Platform.
* Adds persistent projects, investigations, project entities, reusable workflows, contradiction and uncertainty tracking, and artifact history.
* Adds stable connected-platform APIs, workspace schema 2.0, provider-independent generation adapter, and portable project backup and import.
* Advances SQLite to schema version 10 while preserving all governance, handoff, retrieval, accessibility, and recovery controls.


= 6.6.1 =
* Added destination-version compatibility and minimum-version reporting.
* Added expiring delivery tokens, refresh, bounded retry metadata, and idempotency.
* Added validated intake receipts and immutable artifact-return handling.
* Advanced the additive SQLite index to schema version 8.
* Preserved the terminal prompt, light evidence cards, accessibility, and free-tier architecture.

= 6.6.0 =
* Adds common handoff, route, capability, and artifact-return contracts.
* Adds typed payloads for Workbench, Decision Studio, Site Intelligence, Lab, and Feature Suggestions.
* Adds capability discovery and hides unavailable destination actions.
* Adds provenance fingerprints, evidence context, assumptions, uncertainty, and human-confirmation boundaries.
* Adds backend and WordPress prepare, validate, ledger, export, and artifact-return interfaces.
* Adds additive SQLite schema version 7 handoff and artifact ledgers.
* Preserves v6.5.1 accessibility, performance, black-and-green prompt, and light evidence/source cards.

= 6.5.1 =
* Adds roving-tabindex and arrow-key navigation for research modes.
* Adds combobox/listbox title suggestions with active-descendant navigation and cached results.
* Adds progressbar semantics, result focus, reduced motion, forced colors, and 44-pixel mobile targets.
* Replaces browser prompts with an accessible feedback dialog.
* Coalesces health and route requests and caches suggestions against the current index checksum.
* Cancels stale requests, prevents duplicate in-flight questions, and stages answer rendering.
* Adds deferred script loading, FastAPI gzip, clipboard fallback, safer downloads, and theme/mobile hardening.
* Preserves the black-and-green prompt and light answer/source surfaces.

= 6.5.0 =
* Adds eight explicit research modes: auto-detect, title, subject, path, evidence, analysis, comparison, and decision preparation.
* Adds a responsive two-pane public workspace with the black-and-green terminal prompt and light answer, evidence, and source cards.
* Adds answer-first workspace headers, active-mode labels, source counts, related records, paths, and controlled actions.
* Adds short site-scoped follow-up continuity, suggested next questions, and explicit session reset.
* Adds accessible indexed-title suggestions with keyboard navigation and automatic title-mode selection.
* Adds copy, Markdown, JSON, research-note, print, session, feedback, and typed-handoff controls.
* Adds visible cold-start and recovery progress while verified WordPress fallback remains available.
* Preserves v6.4.1 calibrated hybrid retrieval, citation verification, and v6.3.x recovery hardening.

= 6.4.1 =
* Adds persistent, bounded retrieval profiles in SQLite schema version 6.
* Adds administrator controls for structural, lexical, semantic, and RRF weights, evidence thresholds, context limits, source multipliers, and exclusions.
* Adds a packaged golden-query benchmark comparing lexical-only and calibrated hybrid retrieval.
* Persists hit-at-1, hit-at-3, MRR, ambiguity, missing-result, and latency metrics.
* Detects near-duplicate titles and requests clarification instead of silently choosing.
* Blocks AI synthesis when evidence count, score, lexical, semantic, or ambiguity requirements are not met.
* Rejects low-overlap paragraphs, unsupported numeric claims, unknown citation labels, and unknown generated URLs.

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

= 8.12.0 =
* Add Visual Research Intelligence plans for citation networks, evidence/claim/finding maps, contradiction maps, argument graphs, statistical views, provenance graphs, timelines, and source lineage.
* Add explicit human-reviewed promotion into Platform Core Visual Reasoning objects and unified research-session visual bindings.
* Preserve renderer-neutral semantics and source-hash provenance while leaving layout/render execution to specialist visual runtimes.
* Forbid inferred graph edges, automatic claim/finding promotion, visual truth promotion, argument ranking, and statistical interpretation.

= 7.0.0 =
* Adds the Research Quality and Governance Center.
* Adds answer traces, source review, quality evaluation, release gates, retention enforcement, and public methodology.
* Advances SQLite to schema version 9.


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

= 8.12.0 =
* Add Visual Research Intelligence plans for citation networks, evidence/claim/finding maps, contradiction maps, argument graphs, statistical views, provenance graphs, timelines, and source lineage.
* Add explicit human-reviewed promotion into Platform Core Visual Reasoning objects and unified research-session visual bindings.
* Preserve renderer-neutral semantics and source-hash provenance while leaving layout/render execution to specialist visual runtimes.
* Forbid inferred graph edges, automatic claim/finding promotion, visual truth promotion, argument ranking, and statistical interpretation.

= 7.0.0 =
* Adds the Research Quality and Governance Center.
* Adds answer traces, source review, quality evaluation, release gates, retention enforcement, and public methodology.
* Advances SQLite to schema version 9.


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
