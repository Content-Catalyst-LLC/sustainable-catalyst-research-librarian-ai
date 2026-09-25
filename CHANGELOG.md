## 9.5.0 — Research Knowledge Graph & Publication Intelligence
- Added durable research graph nodes, accepted edges, reviewable edge proposals, graph events and immutable snapshots.
- Added publication materialization from declared v9.4 scholarly lineage.
- Added descriptive publication intelligence and graph-neighborhood APIs without impact/truth scoring.
- Added durable research-knowledge-graph-snapshot jobs.
- Preserved human review before semantic relationship acceptance and disabled automatic Core writes.

# Changelog

## 9.3.0 — Peer Review, Replication & Scholarly Validation Environment
- Adds durable structured peer-review rounds and reviewer assignments with conflict declarations.
- Adds human-authored review reports, author responses, revision submissions, and immutable review events.
- Adds explicit replication-attempt registration with runtime/artifact/result/evidence provenance.
- Adds human editorial decisions, validation-readiness checks, and frozen peer-review/replication packages.
- Preserves v9.2 study/protocol/result lineage without automated acceptance, validity certification, replication judgment, or truth promotion.

# v9.2.0 — Original Research & Scholarly Research Environment

- Added durable original/scholarly study registry with Postgres production storage and SQLite local fallback.
- Added protocol freeze, immutable protocol hashes, and explicit post-freeze deviations.
- Added provenance-rich research result registration linked to evidence, specialist runtimes, statistical reasoning objects, and visuals.
- Added human-authored interpretation and manuscript-section registries.
- Added authorship, affiliation, ethics, funding, and conflict declarations.
- Added publication-readiness evaluation with explicit blockers.
- Added immutable study revisions and frozen reproducibility packages.
- Added durable `scholarly-research-package` async job support.
- Preserved governance boundaries: no automatic authorship, peer-review certification, claim acceptance, statistical interpretation, or truth promotion.

# 9.0.0 — Unified Research Intelligence Runtime

- Added one governed 12-stage research-run graph spanning discovery through reproducibility.
- Added deterministic run ids, plan hashes, stage result hashes, and final run fingerprints.
- Added safe unified execution for retrieval planning, candidate extraction, argument planning, statistical planning, visual planning, and project-state planning.
- Added durable `unified-research-runtime` jobs.
- Preserved all human-review gates and prohibited automatic Platform Core writes/truth promotion.

# 8.12.0 — Visual Research Intelligence

- Added deterministic renderer-neutral visual research plans over publications, canonical sources, citation relationships, evidence, findings, claims, arguments, statistical reasoning objects, project state, and provenance.
- Added citation-network, evidence/claim/finding map, contradiction-map, argument-graph, statistical-result, uncertainty, provenance, timeline, source-lineage, concept-map, and generic view kinds.
- Added Platform Core Visual Reasoning Object registration, semantic layer/element/relation registration, immutable visual snapshots, and optional unified research-session visual bindings.
- Added durable `visual-research-plan` jobs to the Postgres-backed queue.
- Added visual object-model and unified visual-runtime readiness probes to the Core client.
- Preserved governance boundaries: no renderer execution, layout computation, inferred graph edges, claim/finding promotion, argument ranking, statistical interpretation, or visual truth promotion.

# 8.10.0 — Argument, Contradiction & Synthesis Integration

- Added deterministic, reviewer-directed argument planning over reviewed Core findings, claims, and evidence.
- Added explicit support/contradiction/qualification/dependency edge preservation without relation inference.
- Added Core contradiction-candidate inspection and reviewer-declared open-tension registration.
- Added researcher-authored synthesis promotion into Core argument synthesis objects and components.
- Added durable `argument-synthesis-plan` jobs to the Postgres-backed v8.3 queue; promotion remains explicit and reviewed.
- Added typed Platform Core v3.3+ argument-node, edge, synthesis, tension, bundle, and readiness client methods.
- Preserved governance boundaries: no automatic argument generation, relation inference, contradiction resolution, ranking, best-argument selection, synthesis generation, conclusion generation, or truth determination.

# 8.9.0 — Finding, Claim & Evidence Extraction Pipeline

- Added deterministic passage-to-candidate extraction for reviewable findings and claims with exact evidence provenance and uncertainty cues.
- Added an explicit human review gate: candidates default to pending and require approved + reviewer identity before Core registration.
- Added Platform Core v3.3+ Finding/Claim/Evidence Intelligence client methods and governed promotion as proposed findings/claims plus evidence links.
- Defaulted candidate evidence relationships to contextualizes unless a stronger relationship is explicitly supplied by a reviewer/caller.
- Added durable `research-intelligence-extraction` jobs to the Postgres-backed v8.3 queue.
- Added Core readiness probes for project-state/versioning and Finding/Claim/Evidence Intelligence, closing the v8.8 readiness-registration gap.
- Preserved governance boundaries: no automatic truth determination, claim/finding acceptance, evidence-strength judgment, contradiction resolution, or publication.

# 8.8.0 — Core Research Object Synchronization

- Added project-level synchronization to Platform Core v3.3+ project-state/versioning contracts.
- Added deterministic synchronization plans for Librarian projects, contexts, Research Rooms, sources, project entities, open questions, and lifecycles.
- Added immutable changed-state versions, frozen versions, snapshots, declared dependency lineage, and idempotent unchanged replay.
- Preserved governance boundaries: synchronization does not determine truth, create claims, publish, advance workflow, or execute research code.

# 8.7.0 — Core Evidence Bridge

- Added typed source-snapshot and passage-evidence promotion into Platform Core v3.3+ evidence-ledger contracts.
- Added deterministic Core IDs, idempotency keys, immutable Librarian↔Core bindings, and conflict recovery.
- Added hydrated-source requirement: citation-only stubs cannot be promoted as governed snapshots.
- Added snapshot-before-evidence enforcement so every promoted passage is anchored to a synchronized Core source snapshot.
- Defaulted passage evidence to neutral/unreviewed with no inferred confidence or automatic claim creation.
- Preserved v8.6 source identity, v8.5 document intelligence, v8.4 retrieval, and v8.3 durable jobs.

# 8.6.0 — Source Identity, Deduplication & Citation Graph

- Added durable canonical scholarly source identity in Postgres with SQLite local/test fallback.
- Added DOI, arXiv, PMID, ISBN, and canonical-URL normalization with deterministic identity priority.
- Added bibliographic fallback deduplication using normalized title, publication year, and first author.
- Added alternate source instances/versions plus author and institution links.
- Added persistent incoming/outgoing citation edges and citation stubs that hydrate when cited works are later ingested.
- Added fail-closed detection when stable identifiers map to multiple canonical sources.
- Integrated v8.5 document intelligence with canonical identity before normal durable indexing.
- Added authenticated `/v1/sources/*` APIs and durable `source-identity` job execution.
- Preserved Platform Core v3.3+ as the governed evidence/reasoning/provenance authority.

# 8.5.0 — Document Intelligence & Scholarly Parsing

- Added deterministic Python parsing for text, Markdown, HTML, and PDF sources.
- Added structural section/page provenance, scholarly identifier extraction, references, citation mentions, tables, figures, and equations.
- Added authenticated `/v1/documents/capabilities`, `/v1/documents/parse`, and `/v1/documents/parse/async` APIs.
- Integrated parsed sections into existing knowledge-record metadata and section-aware chunking.
- Added durable `document-intelligence` job execution while retaining v8.3 queue semantics.
- Preserved Platform Core v3.3+ as the governed evidence/reasoning/provenance authority.

# Changelog

## 8.4.0 — Advanced Retrieval & Reranking Engine

- Adds deterministic, non-generative query decomposition for quoted phrases, comparison components, clauses, and keyword variants derived only from the user's request.
- Adds multi-query rank fusion over the existing exact-title, BM25, optional semantic, and reciprocal-rank-fusion retrieval foundation.
- Adds transparent candidate reranking with query coverage, title coverage, phrase alignment, multi-query consensus, and lexical/semantic support diagnostics.
- Adds typed post-type, source, series, record-ID, URL-prefix, taxonomy, and modified-date retrieval filters applied before ranking.
- Adds canonical-URL, content-hash, and near-duplicate suppression plus bounded maximum-marginal-relevance-style diversity selection.
- Adds `/v1/retrieval/plan` and expands `/v1/retrieve` and `/v1/retrieve/explain` without breaking the existing request defaults.
- Keeps retrieval relevance explicitly separate from evidence quality/truth judgments; Platform Core v3.3+ remains the governed evidence/reasoning authority.
- Preserves the v8.3 Postgres asynchronous processing runtime and v8.2 typed Platform Core integration unchanged.

## 8.3.0 — Asynchronous Ingestion & Document Processing Runtime

- Adds a durable Python job plane for document processing, ingestion, validation, and the future embedding/index/connector executor family.
- Uses Neon/Postgres in production with transactional `FOR UPDATE SKIP LOCKED` worker claims; SQLite remains the local/test fallback.
- Adds idempotency keys, priority, worker leases and heartbeats, bounded retries with exponential backoff, expired-lease recovery, cancellation, manual retry, and immutable job-event history.
- Adds `/v1/jobs/*` authenticated APIs and an in-process FastAPI lifespan-managed worker that can scale safely to multiple workers because the queue claim is database-serialized.
- Adds document normalization → index staging → restart-safe activation → optional embedding → read-back validation while preserving the existing v7.1.x generation/index transaction machinery.
- Keeps Platform Core v3.3+ as the governed evidence/reasoning authority; asynchronous operational processing does not create truth judgments or bypass Core provenance.
- Adds the Postgres migration contract `004_async_document_processing_runtime.sql` and the standalone async runtime schema `sc-research-librarian-async-runtime/1.0`.

## 8.2.0 — Python Service Architecture & Platform Core Client

- Establishes Platform Core v3.3.0+ as a first-class Research Librarian dependency through a typed asynchronous Python client.
- Adds private `/v1/core/*` integration endpoints for architecture/readiness, bindings, governed research-object promotion, unified research-project synchronization, project bundles, and cross-product exchange packages.
- Adds deterministic Core entity IDs, local idempotency protection, 409 recovery reads, transient retry/backoff, version compatibility checks, and fail-closed Core write authentication.
- Adds durable Librarian↔Core binding records in ancillary SQLite schema 19. The production Postgres/pgvector knowledge-index schema remains 3 / `sc-research-librarian-postgres-index/1.2`; no knowledge-index migration is required.
- Keeps responsibilities explicit: Research Librarian Python owns acquisition/document intelligence/retrieval; Platform Core owns governed research objects, provenance/lineage, reasoning objects, reproducibility, visual/statistical reasoning, and cross-product exchange.
- Preserves human review boundaries and does not enable automatic truth promotion, autonomous conclusions, or arbitrary research-code execution in Core.

## 8.0.0 — Unified Research Intelligence & Research Lifecycle Orchestration

- Adds a persistent eight-stage research lifecycle: Frame, Discover, Evaluate, Organize, Collaborate, Synthesize, Promote, and Preserve.
- Adds deterministic, inspectable stage-readiness signals, blockers, and next-action recommendations without automatic stage advancement.
- Requires explicit authenticated human confirmation for lifecycle transitions and records stage lineage as visible events.
- Adds immutable SHA-256-fingerprinted lifecycle checkpoints and includes lifecycle records/events/checkpoints in project backup/import.
- Adds authenticated WordPress lifecycle controls while retaining the `/platform/v7/` REST route namespace for compatibility.
- Keeps lifecycle metadata outside evidence, truth scoring, editorial approval, publication, federated import, and Workspace import semantics.
- Advances ancillary SQLite to schema 18, Connected Research API to 2.0, and the public workspace contract to 3.0. The durable Neon/Postgres knowledge index remains `sc-research-librarian-knowledge-index/13.0`; no knowledge-index migration is required.

## 7.7.0 — Global Library Discovery & Federated Research

- Added fixed, server-side federated adapters for OpenAlex, Crossref, Europe PMC, Open Library, and arXiv.
- Added normalized external result contracts, DOI/ISBN/arXiv-aware deduplication, provider-specific record provenance, access signals, and partial-provider failure reporting.
- Added durable federated-search snapshots to the ancillary research workspace ledger and project backup/import.
- Added authenticated WordPress global-discovery UI, recent-search history, and explicit **Save to My Library** imports.
- Federated saves create private `external-reference` Library objects and never imply Sustainable Catalyst editorial approval, verified evidence, or a truth judgment.
- Advanced ancillary SQLite schema to 17, Connected Research API to 1.6, and public workspace schema to 2.6. The durable Neon/Postgres knowledge-index contract remains `sc-research-librarian-knowledge-index/13.0`; no knowledge-index migration is required.

## 7.6.0 — Workspace Research Handoff & Artifact Promotion

- Adds a governed **Promote to Workspace** outbox for Notebook, Evidence Set, Analysis, Document, and Citation Pack artifact seeds.
- Builds `sc-workspace-research-handoff/1.0` packets with deterministic SHA-256 fingerprints and explicit `sc-workspace-research-import/1.0` semantics.
- Preserves Library source owner, scope, object type, source fingerprint, project relationships, and Research Room participant attribution during promotion.
- Keeps v7.4 individual research state and v7.5 shared room state distinct while allowing both to be represented in a bounded handoff.
- Excludes rejected sources by default; deliberate inclusion remains available for audit/counter-evidence workflows.
- Adds fingerprint-verified export/import receipts that confirm transfer only, never publication or editorial endorsement.
- Adds authenticated WordPress promotion preparation, history, JSON download, and Workspace-open controls with server-side owner/actor resolution and context/project/room/object authorization.
- Includes promotion packets and receipts in project backup/import.
- Advances ancillary SQLite to schema 16 and Connected Research API/workspace contracts to 1.5/2.5; the Neon/Postgres knowledge index remains schema 13.0 and requires no migration.

## 7.5.0 — Collaborative Research Room Intelligence

- Turns Research Rooms into durable collaboration objects with explicit Owner, Editor, Researcher, and Viewer membership roles.
- Adds shared room evidence state while preserving each Library object's original owner, source scope, object type, and provenance.
- Adds collaborative questions whose disposition remains attributable to the creator or room leadership.
- Adds participant-attributed disagreement positions; participants may revise only their own position and only owners/editors may resolve a disagreement.
- Adds an attributable participant activity ledger and bounded room-level synthesis.
- Allows room-scoped context resolution to retrieve sources intentionally shared by other active room members without reclassifying them as editorial or jointly authored.
- Adds an authenticated WordPress Research Rooms workspace with server-side actor identity, membership authorization, evidence sharing, questions, disagreements, activity, synthesis, and room-context promotion.
- Preserves v7.4 personal research state as a separate ledger and keeps room workflow metadata outside verified evidence and model instructions.
- Includes project-linked collaborative room state in portable backup/import.
- Advances ancillary SQLite to schema 15 and connected API/workspace contracts to 1.4/2.4; the Neon/Postgres knowledge-index schema remains 13.0 and requires no migration.

## 7.4.0 — Persistent Research State, Reading History & Open Questions

- Adds a durable, inspectable research-state ledger for searches and explicit workflow actions.
- Adds per-Library-object reading/review state: unread, reading, reviewed, and rejected.
- Adds contradiction flags with explicit resolution state.
- Adds an open-question register with open, resolved, deferred, and dismissed states.
- Adds an authenticated **Research state** workspace view and source-level Reading / Reviewed / Reject / Flag contradiction actions.
- Carries a bounded workflow-memory summary into saved-context Librarian questions while prohibiting prior searches or open questions from becoming evidence.
- Keeps rejected objects in provenance while removing them from context-priority retrieval unless deliberately revisited.
- Includes activity, object state, and open questions in project backup/import.
- Advances the ancillary SQLite workspace schema to 14 and connected API/workspace contracts to 1.3/2.3; the Neon knowledge-index schema remains 13.0 and requires no Postgres migration.
- Preserves the complete v7.3.0 evidence-quality, v7.2.0 Library-context, and v7.1.2 Neon durability lines.

## 7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

- Adds descriptive source profiles for source type, primary/secondary/tertiary role metadata, publisher/institution, publication date, methodology, citations, access state, provenance, and known limitations.
- Adds side-by-side evidence comparison and corpus-level source-mix/provider-diversity summaries.
- Adds deterministic structural evidence-gap detection for missing source diversity, primary evidence, methods visibility, dates, citation metadata, limitations, and comparison contrast.
- Adds an authenticated **Evaluate context** action to the Connected Research Workspace.
- Carries bounded quality signals through resolved research contexts while explicitly keeping them separate from verified evidence.
- Forbids synthetic truth/credibility scores, automatic winners, and automatic source rejection; human judgment remains required.
- Persists optional evaluation/comparison/gap reports as existing project entities, requiring no database migration.
- Advances connected API/workspace contracts to 1.2/2.2 and preserves the complete v7.2.0 Library-context and v7.1.2 Neon durability lines.

## 7.2.0 — Library Object Model & Research Context Alignment

- Adds a Library-native object model for sources, publications, recommendations, saved searches, watchlists, research queue items, source bundles, Research Rooms, pathways, and Workspace references.
- Adds saved contexts spanning Sustainable Catalyst Collection, My Library, Current Project, and Current Research Room while preserving source-scope provenance.
- Adds authenticated WordPress context selection with server-side owner resolution and a 50-object generation boundary.
- Prioritizes verified indexed records referenced by the active context without converting private metadata into evidence.
- Marks route/context metadata as untrusted in the generation prompt and preserves the verified-source citation contract.
- Links Library objects to projects through compatibility entities and carries linked objects in portable project backups.
- Advances the ancillary SQLite store to schema 13 and connected API/workspace contracts to 1.1/2.1.
- Preserves the full v7.1.2 Neon/Postgres durability and timeout-safe chunk activation line.

## 7.1.2 — Timeout-Safe Chunk Processing

- Reduces Neon chunk activation to five records per request by default.
- Persists the durable chunk cursor after every record.
- Bulk-inserts each record's chunks with one JSONB operation instead of hundreds of network round trips.
- Adapts the next batch size to measured step duration.
- Reconciles WordPress cURL timeouts against Neon before declaring failure or retrying.
- Prevents overlapping retries with a Postgres advisory lock.
- Displays current chunk batch size, last-step duration, heartbeat, and timeout recoveries.

## 7.1.1 — Fail-Closed Neon Activation and Database Identity

- Added startup validation for pooled and direct Neon connection identity.
- Added automatic idempotent schema migration and pgvector verification.
- Removed silent production fallback to the local SQLite knowledge index.
- Added password-free database identity and fingerprint diagnostics.
- Added committed-empty and foreign-database marker classification.
- Added automatic WordPress staging replay into a fresh Neon generation.
- Added transactional active-generation verification before commit success.
- Corrected WordPress status storage-engine reporting for Postgres.

## 7.1.0 — Neon Postgres Durable Index

- Moves production source batches, generations, records, chunks, embeddings, and activation cursors to Neon-compatible Postgres.
- Uses pooled `DATABASE_URL` for runtime traffic and direct `DIRECT_DATABASE_URL` for migrations.
- Activates a verified generation through an atomic database pointer rather than SQLite file replacement.
- Adds pgvector storage, database diagnostics, free-tier size reporting, generation rollback, and replay from the preserved WordPress staging file.
- Keeps SQLite as the local-development default and as the temporary ancillary store for governance and connected-workspace records.


## 7.0.8 — Transaction-State Reconciliation and Durable Recovery

- Fixes the empty-missing-batch ambiguity that could exhaust replay attempts despite reporting no missing batch numbers.
- Adds an authenticated reconciliation endpoint that compares backend state with the WordPress expected batch count.
- Returns deterministic `committed`, `activate`, `replay-missing`, or `replay-all` recovery actions.
- Records synchronization batch byte offsets and replays only specific missing batches when possible.
- Recreates missing, empty-shell, mismatched, or indeterminate transactions from the preserved WordPress staging file.
- Resets replay counters after successful reconciliation and supports new recovery generations for failed v7.0.7 jobs.
- Rejects zero-batch activation requests before shadow-index work begins.
- Adds transaction-state, action, ID, generation, and persistent-storage diagnostics to the administration interface.
- Automatically selects a writable `/var/data` disk when available and continues to warn when storage is ephemeral.
- Advances the backend store to SQLite schema 12.

## 7.0.7 — Durable Incremental Index Activation

- Removes FastAPI `BackgroundTasks` from durable-index activation.
- Adds an authenticated, one-step-at-a-time commit endpoint.
- Persists record-copy, chunk-build, checksum, heartbeat, and restart cursors in SQLite schema 11.
- Builds and verifies a shadow replacement while the previous active index remains online.
- Performs only the final database-local table-content switch inside one atomic transaction.
- Upgrades existing v7.0.6 queued/activating jobs in place.
- Replays the durable WordPress staging file when backend ephemeral state is lost.
- Adds granular administration metrics and persistent-storage guidance.

## 7.0.6 — Asynchronous Backend Commit and Ambiguous-Failure Recovery

- Stages all source batches without activating the replacement index inside the final WordPress request.
- Adds a short authenticated commit-queue endpoint and durable backend commit states.
- Runs snapshot, record activation, retrieval-chunk rebuilding, checksum generation, and SQLite commit outside the WordPress HTTP request.
- Polls backend transaction status until activation completes.
- Reconciles ambiguous final-batch transport failures before marking a rebuild failed.
- Detects stale backend commit workers and safely requeues idempotent activation.
- Shows backend activation phase, progress, activated records, and retrieval chunks in the rebuild interface.
- Preserves the previous active index and the complete WordPress staging file until verification succeeds.

## 7.0.5 — Transaction Reconciliation and Public Interface Repair

- Adds authenticated backend transaction-status and incomplete-transaction reset endpoints.
- Detects uncommitted final replacement batches and reconciles backend staging state.
- Replays the durable WordPress JSONL staging file as a fresh bounded transaction without rediscovering source records.
- Adds a production recovery action labeled **Repair and Resume Commit** for existing v7.0.4 failures.
- Displays backend-retained batches, missing batches, replay attempts, validated records, and staging-file size.
- Replaces the unreadable public two-pane/terminal treatment with a visible single-column research workspace.
- Adds eight clearly labeled research-mode cards, readable descriptions, a light question field, a prominent Start Research action, and progressive disclosure for secondary tools.
- Replaces alarming provider-oriented public failure copy with visitor-facing verified-fallback language.
- Preserves the previous committed durable index until the replacement transaction is verified.

## 7.0.4 — Bounded Discovery Finalization and Index Activation

- Skips duplicate legacy fallback migration during normal full rebuilds.
- Adds a persisted `finalizing-discovery` stage with byte and record cursors.
- Removes synchronous full-file scans from the discovery transition and ledger activation.
- Reuses the bounded finalization ledger after the backend commits.
- Adds visible validated-record and byte-progress diagnostics.

## 7.0.3 — Asynchronous Index Rebuild and Recovery

- Moves full knowledge-index rebuild work out of the WordPress browser request.
- Adds a persistent, resumable build job with bounded source-discovery and backend-sync batches.
- Preserves the previously committed Python index until the final replacement batch verifies successfully.
- Streams private JSONL staging data and compressed recovery snapshots without loading the entire corpus into PHP memory.
- Adds Pause, Resume, Run Next Batch Now, Cancel, stale-lock recovery, progress metrics, and WP-Cron/manual processing paths.
- Stops on permanent credential/configuration errors and uses bounded exponential backoff for transient provider or network failures.
- Starts semantic embedding only after durable-index verification.
- Retains all v7.0.2 source-discovery and interface-recovery improvements.

## 7.0.2 — Knowledge Index Recovery and Interface Redesign

- Adds a verified one-click knowledge-index build pipeline.
- Verifies the committed Python runtime after synchronization and attempts snapshot recovery when needed.
- Expands source discovery beyond `public => true` custom post types.
- Introduces four-stage readiness, source coverage, and simplified operational controls.
- Moves advanced settings and diagnostics behind progressive disclosure.
- Replaces raw public provider/model status with visitor-facing research-service states.

## 7.0.1 — Canonical Index, Credential, and Embedding Queue Repair

- Makes the Python durable index the authoritative production index whenever Python Intelligence is enabled.
- Delegates legacy Knowledge Index rebuild/test/embed actions to the authenticated Python backend.
- Expands WordPress fallback indexing from posts/pages to all eligible public post types with pagination.
- Adds safe provider diagnostics naming `SC_RL_GEMINI_API_KEY` and a non-mutating embedding connection test.
- Adds resumable WP-Cron embedding continuation until pending chunks reach zero.
- Adds a one-click **Full Sync and Complete Embedding Queue** recovery operation.
- Counts semantic coverage only for vectors generated by the currently configured embedding model.
- Raises the configurable backend batch ceiling while preserving bounded, persisted batches.
- Stops automatic retries on invalid-key and credential failures while retaining bounded retries for transient provider errors.

## 7.0.0 — Connected Research Intelligence Platform

- Added persistent private-by-default research projects and multi-step investigations.
- Added generic project entities for evidence collections, annotations, reading paths, workflows, contradiction reports, uncertainty registers, and artifact references.
- Added stable `sc-connected-research-api/1.0` resource discovery and workspace schema 2.0.
- Added provider-independent `sc-generation-adapter/1.0` while preserving deterministic fallback.
- Added checksum-verified portable project backups, dry-run import, and project event history.
- Added public, editorial, and institutional WordPress workspace modes and three new shortcodes.
- Advanced SQLite additively to schema version 10.
- Preserved v6.7 governance, v6.6.1 cross-product reliability, v6.5.1 accessibility, v6.4.1 retrieval calibration, and v6.3.1 recovery hardening.

## 7.0.0 — Research Quality and Governance Center

- Added versioned governance policies, source approval and freshness review, privacy-minimized answer traces, quality evaluations, release gates, retention enforcement, methodology publishing, audit exports, and human-controlled overrides.
- Advanced SQLite to schema version 9 while preserving all v6.6.1 handoff reliability and v6.5.1 public workspace behavior.

## 6.6.1 — Cross-Product Reliability Patch

- Added destination-version compatibility states and minimum supported versions.
- Added expiring HMAC delivery tokens, explicit refresh, bounded retries, and exponential backoff metadata.
- Added idempotent preparation, retry, receipt, and artifact-return handling.
- Added intake receipt validation and durable receipt/event ledgers.
- Added artifact type, size, destination, and provenance-fingerprint validation.
- Made artifact and receipt IDs immutable while allowing safe identical replay.
- Advanced the additive SQLite schema to version 8.
- Added WordPress compatibility reporting, retry, token-refresh, and receipt routes.
- Preserved all v6.6.0 typed handoffs and v6.5.1 accessibility/performance behavior.

## 6.6.0 — Platform Intelligence and Typed Research Handoffs

- Added versioned common handoff, route, capability, and artifact-return contracts.
- Added typed destination payloads for Workbench, Decision Studio, Site Intelligence, Lab, and Feature Suggestions.
- Added capability discovery and removal of unavailable destination actions.
- Added provenance fingerprints, verified source context, assumptions, uncertainty, and explicit human-confirmation boundaries.
- Added authenticated backend prepare, validate, log, artifact-return, and artifact-list endpoints.
- Added a nonce-protected WordPress bridge, administrator destination configuration, and handoff export.
- Added SQLite schema version 7 handoff and artifact-return ledgers.
- Advanced the public workspace response to `sc-research-librarian-public-workspace/1.2`.
- Preserved v6.5.1 accessibility, performance, terminal prompt, light evidence cards, and all retrieval/recovery behavior.

## 6.5.1 — Accessibility, Performance, and Interface Reliability

- Added keyboard-complete research-mode radio behavior and roving tabindex.
- Added combobox/listbox title suggestions with active-descendant navigation and live result counts.
- Added progressbar semantics, result focus management, reduced motion, forced colors, and mobile touch-target hardening.
- Replaced browser prompts with an accessible feedback dialog.
- Added shared health/route caches plus browser and checksum-aware WordPress suggestion caches.
- Added stale-request cancellation, duplicate in-flight prevention, and staged answer rendering.
- Added deferred script loading, FastAPI gzip, clipboard fallback, delayed download cleanup, and WordPress-theme compatibility rules.
- Preserved the v6.5.0 public workspace, black-and-green prompt, light evidence cards, calibrated retrieval, and durable recovery architecture.

## 6.5.0 — Production Public Research Workspace

- Added eight explicit research modes for title, subject, path, evidence, analysis, comparison, decision preparation, and auto-detection.
- Added a responsive two-pane public workspace with a focused terminal prompt and a larger answer/evidence surface.
- Added answer-first workspace headers, active-mode labels, source counts, and generated-versus-deterministic response status.
- Added short site-scoped follow-up continuity, suggested next questions, and explicit session reset.
- Added accessible indexed-title suggestions with keyboard navigation and automatic title-mode selection.
- Added copy, Markdown, JSON, research-note, print, session, feedback, and typed-handoff actions.
- Added visible cold-start and recovery progress while verified WordPress fallback remains available.
- Preserved the black-and-green prompt, light answer/source cards, v6.4.1 retrieval calibration, and v6.3.x recovery controls.

## 6.4.1 — Retrieval Calibration and Regression Patch

- Added persistent sanitized retrieval profiles in SQLite schema version 6.
- Added configurable structural, lexical, semantic, and reciprocal-rank-fusion weights.
- Added post-type/source multipliers and record, post-type, source, and URL-prefix exclusions.
- Added a bounded golden-query benchmark comparing lexical-only and calibrated hybrid retrieval.
- Added persisted hit-at-1, hit-at-3, MRR, ambiguity, missing-result, and latency history.
- Added near-duplicate-title ambiguity detection and focused clarification.
- Added minimum-evidence gates before AI synthesis.
- Added unsupported paragraph, citation-coverage, and numeric-claim verification.
- Added context-budget and retrieval-latency diagnostics.
- Preserved v6.4.0 section-aware hybrid retrieval and all v6.3.x durability and recovery controls.

## 6.4.0 — Hybrid Retrieval and Citation Engine

- Added deterministic heading-aware and page-aware chunks backed by SQLite schema version 5.
- Added exact-title priority and BM25 section retrieval.
- Added optional Gemini embeddings, resumable embedding runs, and semantic-coverage reporting.
- Added reciprocal-rank fusion across structural, lexical, and semantic rankings.
- Added evidence IDs, citation labels, section headings, page numbers, passages, and record versions.
- Added generated citation and URL verification with deterministic evidence fallback.

## 6.3.1 — Cold-Start and Recovery Hardening

- Added backend startup state, phase, progress, readiness, service-start time, and uptime reporting.
- Added persisted WordPress recovery phases and public recovery-progress visibility.
- Added bounded exponential retry with configurable ceilings for full sync and cold-start recovery.
- Added retry exhaustion, manual retry clearing, and recovery-event deduplication.
- Added stalled staging-job detection, repair, purge controls, and transaction-timeout handling.
- Added per-record validation, rejection history, and safe valid-record commits with malformed-record isolation.
- Added WordPress snapshot record/hash/checksum validation and runtime snapshot integrity verification before rollback.
- Added administrator snapshot validation, maintenance actions, and JSON operations-log export.
- Added transient public-notice suppression for repeated warm-up or connectivity events.
- Preserved the v6.3.0 transactional SQLite index, private WordPress recovery snapshots, v6.2.1 endpoint reliability, and black-and-green prompt interface.

## 6.3.0 — Durable Knowledge Index, Sync Ledger, and Recovery

- Replaced the Python JSON runtime store with a transactional SQLite knowledge index.
- Added atomic multi-batch staging so incomplete synchronization jobs cannot replace a valid live index.
- Added idempotent jobs, duplicate-batch protection, record content hashes, unchanged detection, and out-of-order batch completion.
- Added incremental upserts, explicit deletions, tombstones, and record-level WordPress change queues.
- Added private gzip WordPress snapshots with checksums, retention controls, and direct-access protection.
- Added automatic cold-start recovery when the backend is reachable but its ephemeral index is empty.
- Added backend runtime safety snapshots, manifest and snapshot endpoints, and authenticated rollback.
- Added WordPress/backend checksum comparison, sync ledger visibility, recovery logs, and administrator recovery controls.
- Added SQLite migration support for the legacy JSON runtime index.
- Preserved v6.2.1 endpoint reliability, rolling public limits, nonce retry, and black-and-green prompt styling.
- Added Python 3.12 release validation and repository-root/backend pytest path coverage.

## 6.2.1 — WordPress Indexing and Endpoint Reliability Patch

- Prioritized full canonical WordPress article records over duplicate summary-only route-index records.
- Added detailed sync jobs, batch outcomes, source counts, duplicate counts, rejected-record counts, and sync history.
- Added WordPress REST, permalink, WP-Cron, backend, integration-key, empty-index, provider-quota, and rate-limit diagnostics.
- Added authenticated backend verification plus **Repair Endpoint and Resynchronize**.
- Added rolling public request limits, editor exemptions, `Retry-After` responses, status reporting, and administrator reset controls.
- Added public nonce refresh with one safe retry for questions and title suggestions.
- Added structured endpoint status to Python, fallback, and direct WordPress provider responses.
- Restyled the public question textarea as a black-and-green terminal prompt while retaining light answer and source cards.
- Added FastAPI sync job and batch metadata with accepted/rejected counts.
- Added repository-root pytest path configuration and backend-directory release-test execution.

## 6.2.0 — Knowledge Library Intelligence and Production UX

- Added a production FastAPI backend designed for Render deployment.
- Added secure WordPress-to-Python authentication and backend health/status reporting.
- Added full public library synchronization across eligible public post types.
- Added title-aware hybrid ranking with exact-title priority.
- Added related-title discovery, research paths, title suggestions, and short session continuity.
- Added grounded Gemini answer generation using retrieved Sustainable Catalyst sources only.
- Added the Research Librarian AI → Python Intelligence administration page.
- Added scheduled and post-change synchronization.
- Added a larger answer-first public interface with advanced diagnostics hidden behind disclosure controls.
- Moved direct WordPress AI provider configuration to an optional fallback screen under Advanced.


## 6.1.1 — Gemini Authorization Key Compatibility Patch

- Accept modern Google AI Studio authorization keys, including key strings containing periods.
- Detect older standard Gemini keys and display migration/restriction guidance.
- Explain 400, 403, 404, 429, and temporary Gemini provider failures in administrator diagnostics.
- Preserve live AI status, Site Intelligence country routing, semantic retrieval, and deterministic fallback behavior.

## 6.1.0 — Live AI Restoration and Admin Consolidation

- Restored live Gemini/OpenAI generation as the clearly identified primary assistant path.
- Added public-safe AI provider status and administrator-only connection diagnostics.
- Added last-success, last-failure, latency, HTTP-status, and transport-error records.
- Added administrator Gemini generate-content model discovery.
- Added ISO country recognition with country-aware Site Intelligence routes.
- Added Pakistan-to-PAK Country Intelligence regression coverage.
- Added Site Intelligence source records and Dashboard Studio, Workbench, and Decision Studio handoffs.
- Replaced first-match keyword fallback with weighted route scoring.
- Added the dedicated Research Librarian AI WordPress menu and consolidated specialized tools under Advanced.
- Removed Research Librarian module links from the general WordPress Settings menu.
- Updated Gemini requests to use server-side header authentication, system instructions, normalized model names, and configurable timeouts.
- Added `/ai/status`, `/ai/test`, and `/ai/models` REST endpoints.
- Preserved collision-safe v6.0.1 bootstrap behavior, governed learning, retrieval, paths, handoffs, feedback, and operational capabilities.

## 6.0.1 — WordPress Bootstrap Registration Repair

- Removed a self-detecting class guard that caused v6.0.0 to return before bootstrap on every request.
- Replaced collision-prone internal PHP class names with v6-specific names.
- Replaced collision-prone bootstrap helper function names with v6-specific names.
- Preserved the historic main class name through a compatibility alias only when it is unclaimed.
- Ensured settings, shortcodes, REST routes, and admin pages register even when a legacy class loads first.
- Added an administrator notice that identifies the legacy class file and version.
- Prevented the read-only diagnostics plugin from being classified as a duplicate Research Librarian installation.
- Raised the main v6 registration priority to make the current plugin authoritative.

## 5.9.0 — Closed-Loop Route Improvement

- Added versioned feedback-to-route improvement proposals.
- Added deterministic before-and-after route evaluation.
- Added configurable regression pass-rate and minimum-evidence gates.
- Added human-only approval and rejection workflow.
- Applied approved changes through the existing editorial curation registry.
- Added provenance records, audit history, and rollback snapshots.
- Added administrator REST endpoints and privacy-safe Site Intelligence events.
- Preserved v5.8 adaptive prompts, v5.7 demand intelligence, v5.6 feedback bridge, v5.5 operations, and v5.4 deep links.

## 5.8.0 — Adaptive Prompt and Survey Experiences

- Added versioned adaptive experience rules and administrator configuration.
- Added contextual triggers for low confidence, zero sources, route abandonment, path completion, tool demand, and destination handoffs.
- Added consent-aware evaluation, daily frequency caps, cooldown periods, and dismissal suppression.
- Added Feature Suggestions survey handoffs and custom integration hooks.
- Added bounded aggregate analytics and privacy-minimized Site Intelligence events.
- Added public evaluation/response endpoints and administrator rules/analytics endpoints.
- Added the `[sc_research_librarian_adaptive_experience]` shortcode.

## 5.7.0 — Research Demand and Knowledge-Gap Intelligence

- Added aggregate demand intelligence across route sessions, guided paths, feedback records, Feature Suggestions bridge records, evaluation failures, and source coverage.
- Added 30-day, 90-day, and all-time analysis windows.
- Added high-demand routes, emerging topic clusters, low-confidence route clusters, missing-source clusters, missing-tool clusters, and prompt evaluation failure summaries.
- Added advisory opportunity scoring that combines demand, confidence, source gaps, evaluation failures, and zero-source sessions.
- Added an administrator dashboard, protected REST report and export endpoints, daily refresh scheduling, and a bounded audit log.
- Added optional public aggregate summaries with minimum-count suppression; public summaries remain disabled by default.
- Added privacy-minimized `librarian.demand_intelligence_refreshed` Site Intelligence events.
- Preserved Feature Suggestions feedback bridging, deep-link actions, stable operations, route ranking, and article-map integrations.

## v5.6.0 — Feature Suggestions Feedback Bridge

- Added contextual route ratings and detailed issue reporting.
- Added wrong-route, missing-source, missing-topic, missing-tool, unclear-answer, and answer-grounding feedback types.
- Added a Feature Suggestions v3 adapter without a hard plugin dependency.
- Added local queue fallback, receipt-protected status, and 24-hour duplicate protection.
- Added administrator diagnostics and protected JSON export.
- Added privacy-minimized Site Intelligence events.
- Preserved v5.5.0 stable operations and v5.4.0 deep-link actions.

## v5.5.0 — Stable Operations Polish and Release Notes

- Added a unified release-readiness and stable-operations dashboard.
- Added required and recommended runtime, storage, activation, maintenance, integration, release-manifest, and recovery checks.
- Added daily scheduled operational validation with privacy-minimized Site Intelligence events.
- Added repeatable migration validation and versioned operations state.
- Added bounded administrator audit history and protected operations export.
- Added Workbench and Decision Studio destination-health checks.
- Added public release-notes and public-safe operations-status shortcodes.
- Added administrator status, check, and export REST endpoints.
- Preserved v5.4.0 typed handoffs, deep links, Feature Suggestions integration, route ranking, and article-map embeds.

## 5.4.0 — Decision Studio / Workbench Deep-Link Actions

- Added public Workbench and Decision Studio actions to the Route Action Center.
- Added typed `sc-research-handoff/1.1` payloads and 30-minute token resolution.
- Added destination capability discovery, failure recovery, and shared platform events.
- Preserved v5.3.3 contextual feedback and Site Intelligence integration.

# Changelog

## 8.3.0 — Asynchronous Ingestion & Document Processing Runtime

- Adds a durable Python job plane for document processing, ingestion, validation, and the future embedding/index/connector executor family.
- Uses Neon/Postgres in production with transactional `FOR UPDATE SKIP LOCKED` worker claims; SQLite remains the local/test fallback.
- Adds idempotency keys, priority, worker leases and heartbeats, bounded retries with exponential backoff, expired-lease recovery, cancellation, manual retry, and immutable job-event history.
- Adds `/v1/jobs/*` authenticated APIs and an in-process FastAPI lifespan-managed worker that can scale safely to multiple workers because the queue claim is database-serialized.
- Adds document normalization → index staging → restart-safe activation → optional embedding → read-back validation while preserving the existing v7.1.x generation/index transaction machinery.
- Keeps Platform Core v3.3+ as the governed evidence/reasoning authority; asynchronous operational processing does not create truth judgments or bypass Core provenance.
- Adds the Postgres migration contract `004_async_document_processing_runtime.sql` and the standalone async runtime schema `sc-research-librarian-async-runtime/1.0`.

## 7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

- Adds descriptive source profiles for source type, primary/secondary/tertiary role metadata, publisher/institution, publication date, methodology, citations, access state, provenance, and known limitations.
- Adds side-by-side evidence comparison and corpus-level source-mix/provider-diversity summaries.
- Adds deterministic structural evidence-gap detection for missing source diversity, primary evidence, methods visibility, dates, citation metadata, limitations, and comparison contrast.
- Adds an authenticated **Evaluate context** action to the Connected Research Workspace.
- Carries bounded quality signals through resolved research contexts while explicitly keeping them separate from verified evidence.
- Forbids synthetic truth/credibility scores, automatic winners, and automatic source rejection; human judgment remains required.
- Persists optional evaluation/comparison/gap reports as existing project entities, requiring no database migration.
- Advances connected API/workspace contracts to 1.2/2.2 and preserves the complete v7.2.0 Library-context and v7.1.2 Neon durability lines.

## v5.3.3 — Pre-v5.4 Integration Bridge

- Added Feature Suggestions v3 contextual feedback compatibility without a hard plugin dependency.
- Added privacy-minimized shared platform events for Site Intelligence ingestion.
- Added typed Workbench and Decision Studio handoff preparation with schema validation.
- Added destination capability discovery and availability checks.
- Added route, source-card, article-map, session, answer, and prompt references.
- Added integration health and capability REST endpoints.
- Added an administrator integration diagnostics page and test event.
- Preserved the v5.4.0 boundary: no public deep-link action center is enabled in this release.
- Preserved v5.3.2 duplicate activation repair and all v5.3 article-map features.

## v5.3.2 — Duplicate Activation Notice Cleanup and Stale Active Plugin Repair

- Added duplicate active-plugin path detection.
- Added stale missing plugin record detection.
- Added nonce-protected one-click repair action from the admin notice.
- Added exact plugin path display inside the duplicate/stale activation notice.
- Added admin-only activation status and repair REST endpoints.
- Reduced the activation guard from a hard error-style nag to an actionable repair notice.
- Preserved the v5.3.1 article-map features and stable plugin folder packaging.

## v5.3.1 — Activation Fatal Guard and Stable Plugin Folder Fix

- Repackages the WordPress plugin zip with the stable plugin folder slug `sustainable-catalyst-research-librarian-ai` instead of a versioned directory.
- Adds a duplicate-active-copy guard to avoid a PHP fatal if an older versioned copy is still active.
- Preserves all v5.3.0 article map integration features.
- Recommended install path: deactivate older versioned plugin copies, delete them after confirming v5.3.1 is active, then upload v5.3.1.

## v5.3.0 — On-Page Research Path Embeds and Article Map Integration

- Added public-safe article path embeds.
- Added article map integration summary shortcode.
- Added related article route cards shortcode.
- Added contextual article-to-route path builder.
- Added Workbench, Decision Studio, module artifact, and Knowledge Library path templates.
- Added Article Maps admin dashboard.
- Added article-map status, catalog, build, and export REST endpoints.



## 5.2.0 — Public Route Quality Tuning and Source Card Ranking

### Added

- Public route-quality tuning layer.
- Source-card ranking rules for Workbench, Decision Studio, module, impact, data, finance, narrative risk, and platform queries.
- Dominant prompt signal detection.
- Route quality diagnostics inside grounded route notes.
- Admin route-quality calibration dashboard.
- Admin-only quality export endpoint.
- Public-safe route-quality and source-ranking shortcodes.

### Changed

- Matched source cards are now re-ranked after keyword/semantic retrieval using route fit, prompt intent, source type, title/summary terms, and route specificity.
- Health output now includes a public-safe route-quality status object.

### Fixed

- Specialized questions are less likely to show broad platform cards above Workbench, Decision Studio, or module-specific sources.

# Changelog

## 8.3.0 — Asynchronous Ingestion & Document Processing Runtime

- Adds a durable Python job plane for document processing, ingestion, validation, and the future embedding/index/connector executor family.
- Uses Neon/Postgres in production with transactional `FOR UPDATE SKIP LOCKED` worker claims; SQLite remains the local/test fallback.
- Adds idempotency keys, priority, worker leases and heartbeats, bounded retries with exponential backoff, expired-lease recovery, cancellation, manual retry, and immutable job-event history.
- Adds `/v1/jobs/*` authenticated APIs and an in-process FastAPI lifespan-managed worker that can scale safely to multiple workers because the queue claim is database-serialized.
- Adds document normalization → index staging → restart-safe activation → optional embedding → read-back validation while preserving the existing v7.1.x generation/index transaction machinery.
- Keeps Platform Core v3.3+ as the governed evidence/reasoning authority; asynchronous operational processing does not create truth judgments or bypass Core provenance.
- Adds the Postgres migration contract `004_async_document_processing_runtime.sql` and the standalone async runtime schema `sc-research-librarian-async-runtime/1.0`.

## 7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

- Adds descriptive source profiles for source type, primary/secondary/tertiary role metadata, publisher/institution, publication date, methodology, citations, access state, provenance, and known limitations.
- Adds side-by-side evidence comparison and corpus-level source-mix/provider-diversity summaries.
- Adds deterministic structural evidence-gap detection for missing source diversity, primary evidence, methods visibility, dates, citation metadata, limitations, and comparison contrast.
- Adds an authenticated **Evaluate context** action to the Connected Research Workspace.
- Carries bounded quality signals through resolved research contexts while explicitly keeping them separate from verified evidence.
- Forbids synthetic truth/credibility scores, automatic winners, and automatic source rejection; human judgment remains required.
- Persists optional evaluation/comparison/gap reports as existing project entities, requiring no database migration.
- Advances connected API/workspace contracts to 1.2/2.2 and preserves the complete v7.2.0 Library-context and v7.1.2 Neon durability lines.

## v5.1.0 — Live Public Experience QA, Prompt Library, and UX Calibration

- Added live public experience QA status.
- Added visitor prompt library for public route testing.
- Added live QA checklist for answer cards, source cards, handoff actions, guided paths, mobile review, and boundary behavior.
- Added admin Live UX dashboard.
- Added public-safe Live UX summary shortcode.
- Added prompt-library and live-QA shortcodes.
- Added admin-only Live UX JSON export.
- Added v5.1.0 documentation and manifest.


## v5.0.0 — Stable Public Release, Launch Checklist, and Acceptance Gate

- Added stable public release readiness score.
- Added launch checklist and acceptance gate.
- Added admin-only release export.
- Added public-safe stable release and launch checklist shortcodes.
- Added v5.0.0 manifest and release documentation.


## v4.9.1 — Documentation Snapshot Visibility Fix

- Replaced the JavaScript-only Generate Documentation Snapshot action with nonce-protected `admin-post.php` actions.
- Added visible admin success and reset notices.
- Added a Generated Documentation Preview panel to confirm that snapshot generation changed the stored page payload.
- Added copy-ready Markdown output inside the Documentation admin page.
- Added server-side documentation JSON export through an admin-post action so export works without relying on REST nonce JavaScript.
- Preserved the public documentation REST endpoints and shortcodes from v4.9.0.

# Changelog

## 8.3.0 — Asynchronous Ingestion & Document Processing Runtime

- Adds a durable Python job plane for document processing, ingestion, validation, and the future embedding/index/connector executor family.
- Uses Neon/Postgres in production with transactional `FOR UPDATE SKIP LOCKED` worker claims; SQLite remains the local/test fallback.
- Adds idempotency keys, priority, worker leases and heartbeats, bounded retries with exponential backoff, expired-lease recovery, cancellation, manual retry, and immutable job-event history.
- Adds `/v1/jobs/*` authenticated APIs and an in-process FastAPI lifespan-managed worker that can scale safely to multiple workers because the queue claim is database-serialized.
- Adds document normalization → index staging → restart-safe activation → optional embedding → read-back validation while preserving the existing v7.1.x generation/index transaction machinery.
- Keeps Platform Core v3.3+ as the governed evidence/reasoning authority; asynchronous operational processing does not create truth judgments or bypass Core provenance.
- Adds the Postgres migration contract `004_async_document_processing_runtime.sql` and the standalone async runtime schema `sc-research-librarian-async-runtime/1.0`.

## 7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

- Adds descriptive source profiles for source type, primary/secondary/tertiary role metadata, publisher/institution, publication date, methodology, citations, access state, provenance, and known limitations.
- Adds side-by-side evidence comparison and corpus-level source-mix/provider-diversity summaries.
- Adds deterministic structural evidence-gap detection for missing source diversity, primary evidence, methods visibility, dates, citation metadata, limitations, and comparison contrast.
- Adds an authenticated **Evaluate context** action to the Connected Research Workspace.
- Carries bounded quality signals through resolved research contexts while explicitly keeping them separate from verified evidence.
- Forbids synthetic truth/credibility scores, automatic winners, and automatic source rejection; human judgment remains required.
- Persists optional evaluation/comparison/gap reports as existing project entities, requiring no database migration.
- Advances connected API/workspace contracts to 1.2/2.2 and preserves the complete v7.2.0 Library-context and v7.1.2 Neon durability lines.

## v4.9.0 — Public Documentation Page Generator

- Added public-safe documentation generator.
- Added documentation catalog for public, admin, and developer-facing Research Librarian surfaces.
- Added generated public documentation page payload with HTML and Markdown outputs.
- Added shortcode inventory and endpoint group summaries.
- Added admin Documentation dashboard.
- Added admin-only documentation export.
- Added public documentation summary, docs catalog, and generated documentation page shortcodes.
- Added documentation REST endpoints.

## v4.8.0 — Admin Query Review and Route Improvement Workflow

- Added admin query review dashboard.
- Added review queue ingestion from feedback, evaluation failures, saved sessions, and guided path logs.
- Added manual correction endpoint for expected-route and observed-route review records.
- Added review status, queue, export, mark, clear, and ingest REST endpoints.
- Added public-safe query review summary shortcode.
- Added route-improvement workflow documentation and manifest.
- Preserved v4.6.0 public answer UX and v4.7.1 guided paths.

## v4.7.1 — Guided Research Paths Rebased on Public Answer UX

- Rebuilt v4.7.x on top of v4.6.0 Public Answer UX.
- Preserved recommended route cards, matched source cards, confidence badges, reason-code chips, and the Route Action Center.
- Preserved answer UX endpoints and summary shortcodes.
- Added guided research path templates and multi-step route builder endpoints.
- Added path builder UI while keeping the public assistant answer layout intact.

# Changelog

## 8.3.0 — Asynchronous Ingestion & Document Processing Runtime

- Adds a durable Python job plane for document processing, ingestion, validation, and the future embedding/index/connector executor family.
- Uses Neon/Postgres in production with transactional `FOR UPDATE SKIP LOCKED` worker claims; SQLite remains the local/test fallback.
- Adds idempotency keys, priority, worker leases and heartbeats, bounded retries with exponential backoff, expired-lease recovery, cancellation, manual retry, and immutable job-event history.
- Adds `/v1/jobs/*` authenticated APIs and an in-process FastAPI lifespan-managed worker that can scale safely to multiple workers because the queue claim is database-serialized.
- Adds document normalization → index staging → restart-safe activation → optional embedding → read-back validation while preserving the existing v7.1.x generation/index transaction machinery.
- Keeps Platform Core v3.3+ as the governed evidence/reasoning authority; asynchronous operational processing does not create truth judgments or bypass Core provenance.
- Adds the Postgres migration contract `004_async_document_processing_runtime.sql` and the standalone async runtime schema `sc-research-librarian-async-runtime/1.0`.

## 7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

- Adds descriptive source profiles for source type, primary/secondary/tertiary role metadata, publisher/institution, publication date, methodology, citations, access state, provenance, and known limitations.
- Adds side-by-side evidence comparison and corpus-level source-mix/provider-diversity summaries.
- Adds deterministic structural evidence-gap detection for missing source diversity, primary evidence, methods visibility, dates, citation metadata, limitations, and comparison contrast.
- Adds an authenticated **Evaluate context** action to the Connected Research Workspace.
- Carries bounded quality signals through resolved research contexts while explicitly keeping them separate from verified evidence.
- Forbids synthetic truth/credibility scores, automatic winners, and automatic source rejection; human judgment remains required.
- Persists optional evaluation/comparison/gap reports as existing project entities, requiring no database migration.
- Advances connected API/workspace contracts to 1.2/2.2 and preserves the complete v7.2.0 Library-context and v7.1.2 Neon durability lines.

## v4.7.1 — Guided Research Paths and Multi-Step Route Builder

- Added guided research path templates.
- Added public multi-step route builder endpoint.
- Added quick, standard, and deep path depth options.
- Added path confidence scoring and checkpoints.
- Added Workbench, Decision Studio, module artifact, feature suggestion, and knowledge-route handoff targets.
- Added path session save/log/export endpoints.
- Added public guided-path summary and path-builder shortcodes.
- Added admin Guided Paths dashboard under Settings.
- Added v4.7.1 guided paths manifest and documentation.


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

## 8.3.0 — Asynchronous Ingestion & Document Processing Runtime

- Adds a durable Python job plane for document processing, ingestion, validation, and the future embedding/index/connector executor family.
- Uses Neon/Postgres in production with transactional `FOR UPDATE SKIP LOCKED` worker claims; SQLite remains the local/test fallback.
- Adds idempotency keys, priority, worker leases and heartbeats, bounded retries with exponential backoff, expired-lease recovery, cancellation, manual retry, and immutable job-event history.
- Adds `/v1/jobs/*` authenticated APIs and an in-process FastAPI lifespan-managed worker that can scale safely to multiple workers because the queue claim is database-serialized.
- Adds document normalization → index staging → restart-safe activation → optional embedding → read-back validation while preserving the existing v7.1.x generation/index transaction machinery.
- Keeps Platform Core v3.3+ as the governed evidence/reasoning authority; asynchronous operational processing does not create truth judgments or bypass Core provenance.
- Adds the Postgres migration contract `004_async_document_processing_runtime.sql` and the standalone async runtime schema `sc-research-librarian-async-runtime/1.0`.

## 7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

- Adds descriptive source profiles for source type, primary/secondary/tertiary role metadata, publisher/institution, publication date, methodology, citations, access state, provenance, and known limitations.
- Adds side-by-side evidence comparison and corpus-level source-mix/provider-diversity summaries.
- Adds deterministic structural evidence-gap detection for missing source diversity, primary evidence, methods visibility, dates, citation metadata, limitations, and comparison contrast.
- Adds an authenticated **Evaluate context** action to the Connected Research Workspace.
- Carries bounded quality signals through resolved research contexts while explicitly keeping them separate from verified evidence.
- Forbids synthetic truth/credibility scores, automatic winners, and automatic source rejection; human judgment remains required.
- Persists optional evaluation/comparison/gap reports as existing project entities, requiring no database migration.
- Advances connected API/workspace contracts to 1.2/2.2 and preserves the complete v7.2.0 Library-context and v7.1.2 Neon durability lines.

## 3.9.0 — Scheduled Index Maintenance, Sitemap Sync, and Health Alerts

- Added scheduled knowledge-index maintenance.
- Added WordPress cron hook and maintenance schedule sync action.
- Added manual maintenance run action.
- Added optional sitemap URL ingestion.
- Added maintenance status/export REST endpoints.
- Added maintenance-summary shortcode.
- Added health/alert configuration for index maintenance.

# Changelog

## 8.3.0 — Asynchronous Ingestion & Document Processing Runtime

- Adds a durable Python job plane for document processing, ingestion, validation, and the future embedding/index/connector executor family.
- Uses Neon/Postgres in production with transactional `FOR UPDATE SKIP LOCKED` worker claims; SQLite remains the local/test fallback.
- Adds idempotency keys, priority, worker leases and heartbeats, bounded retries with exponential backoff, expired-lease recovery, cancellation, manual retry, and immutable job-event history.
- Adds `/v1/jobs/*` authenticated APIs and an in-process FastAPI lifespan-managed worker that can scale safely to multiple workers because the queue claim is database-serialized.
- Adds document normalization → index staging → restart-safe activation → optional embedding → read-back validation while preserving the existing v7.1.x generation/index transaction machinery.
- Keeps Platform Core v3.3+ as the governed evidence/reasoning authority; asynchronous operational processing does not create truth judgments or bypass Core provenance.
- Adds the Postgres migration contract `004_async_document_processing_runtime.sql` and the standalone async runtime schema `sc-research-librarian-async-runtime/1.0`.

## 7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

- Adds descriptive source profiles for source type, primary/secondary/tertiary role metadata, publisher/institution, publication date, methodology, citations, access state, provenance, and known limitations.
- Adds side-by-side evidence comparison and corpus-level source-mix/provider-diversity summaries.
- Adds deterministic structural evidence-gap detection for missing source diversity, primary evidence, methods visibility, dates, citation metadata, limitations, and comparison contrast.
- Adds an authenticated **Evaluate context** action to the Connected Research Workspace.
- Carries bounded quality signals through resolved research contexts while explicitly keeping them separate from verified evidence.
- Forbids synthetic truth/credibility scores, automatic winners, and automatic source rejection; human judgment remains required.
- Persists optional evaluation/comparison/gap reports as existing project entities, requiring no database migration.
- Advances connected API/workspace contracts to 1.2/2.2 and preserves the complete v7.2.0 Library-context and v7.1.2 Neon durability lines.

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

## 8.3.0 — Asynchronous Ingestion & Document Processing Runtime

- Adds a durable Python job plane for document processing, ingestion, validation, and the future embedding/index/connector executor family.
- Uses Neon/Postgres in production with transactional `FOR UPDATE SKIP LOCKED` worker claims; SQLite remains the local/test fallback.
- Adds idempotency keys, priority, worker leases and heartbeats, bounded retries with exponential backoff, expired-lease recovery, cancellation, manual retry, and immutable job-event history.
- Adds `/v1/jobs/*` authenticated APIs and an in-process FastAPI lifespan-managed worker that can scale safely to multiple workers because the queue claim is database-serialized.
- Adds document normalization → index staging → restart-safe activation → optional embedding → read-back validation while preserving the existing v7.1.x generation/index transaction machinery.
- Keeps Platform Core v3.3+ as the governed evidence/reasoning authority; asynchronous operational processing does not create truth judgments or bypass Core provenance.
- Adds the Postgres migration contract `004_async_document_processing_runtime.sql` and the standalone async runtime schema `sc-research-librarian-async-runtime/1.0`.

## 7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

- Adds descriptive source profiles for source type, primary/secondary/tertiary role metadata, publisher/institution, publication date, methodology, citations, access state, provenance, and known limitations.
- Adds side-by-side evidence comparison and corpus-level source-mix/provider-diversity summaries.
- Adds deterministic structural evidence-gap detection for missing source diversity, primary evidence, methods visibility, dates, citation metadata, limitations, and comparison contrast.
- Adds an authenticated **Evaluate context** action to the Connected Research Workspace.
- Carries bounded quality signals through resolved research contexts while explicitly keeping them separate from verified evidence.
- Forbids synthetic truth/credibility scores, automatic winners, and automatic source rejection; human judgment remains required.
- Persists optional evaluation/comparison/gap reports as existing project entities, requiring no database migration.
- Advances connected API/workspace contracts to 1.2/2.2 and preserves the complete v7.2.0 Library-context and v7.1.2 Neon durability lines.

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
## 6.0.0 — Integrated Research Guidance Platform

- Added an integrated platform command center spanning routing, article maps, deep-link actions, operations, feedback, demand intelligence, adaptive experiences, and closed-loop route improvement.
- Added versioned platform and research-journey schemas.
- Added public platform-summary and guidance-journey shortcodes.
- Added protected platform status and snapshot exports plus a public journey endpoint.
- Added unified capability discovery and module readiness reporting.
- Added privacy-minimized platform health events and bounded administrative audit history.
- Preserved human approval, regression protection, and privacy boundaries across every integrated module.
