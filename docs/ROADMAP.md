# Research Librarian Roadmap

## v6.3.0 — Durable Knowledge Index, Sync Ledger, and Recovery — Complete

- Transactional SQLite runtime index
- Atomic multi-batch replacement
- Idempotent jobs and duplicate-batch protection
- Record hashes, incremental upserts, deletes, and tombstones
- Private compressed WordPress recovery snapshots
- Automatic empty-index rehydration on ephemeral Render infrastructure
- Sync ledger, checksums, manifest comparison, recovery logs, and rollback
- Free-tier deployment without a paid database

## v6.3.1 — Cold-Start and Recovery Hardening — Complete

- Startup phase, progress, readiness, and public warm-up status
- Bounded exponential retry, retry exhaustion, and stalled-job repair
- Failed-record isolation with rejection history and prior-record protection
- WordPress and runtime snapshot integrity validation
- Administrator maintenance controls and JSON operations-log export
- Recovery-event deduplication and transient-notice suppression

## v6.4.0 — Hybrid Retrieval and Citation Engine — Complete

- BM25 lexical retrieval plus exact-title priority
- Heading-aware article chunking
- Resumable Gemini embedding queue
- Lexical, semantic, relationship, and route-signal fusion
- Structured evidence objects and generated-citation verification
- PDF full-text and page-aware evidence records
- Deterministic evidence summaries when Gemini is unavailable

## v6.4.1 — Retrieval Calibration and Regression Patch — Complete

- Persistent, sanitized retrieval profiles
- Golden-query lexical-versus-hybrid benchmark and history
- Near-duplicate-title ambiguity protection
- Minimum-evidence gates before AI synthesis
- Unsupported paragraph and numeric-claim rejection
- Ranking weights, source multipliers, exclusions, and context budgets
- Retrieval latency and calibration diagnostics

## v6.5.0 — Production Public Research Workspace — Complete

- Answer-first responsive public workspace
- Eight explicit research modes
- Terminal prompt with light evidence and source cards
- Accessible title suggestions and keyboard navigation
- Bounded follow-up continuity and explicit session reset
- Citation, path, related-record, and action sections
- Markdown, JSON, research-note, print, session, feedback, and handoff actions
- Visible cold-start and recovery progress

## v6.5.1 — Accessibility, Performance, and Interface Reliability — Complete

- Full keyboard and screen-reader audit
- Reduced-motion and high-contrast refinements
- Cached title suggestions and reduced duplicate REST traffic
- Staged answer rendering and performance budgets
- Browser, theme, and mobile compatibility regression suite

## v6.6.0 — Platform Intelligence and Typed Research Handoffs — Complete

- Versioned handoffs to Workbench, Decision Studio, Site Intelligence, and Lab
- Provenance-preserving artifact return
- Capability discovery and destination-health validation

## v6.6.1 — Cross-Product Reliability Patch — Complete

- Destination-version checks, retry, and recovery
- Expired-token repair and duplicate-event prevention
- Artifact-return validation and end-to-end integration tests

## v7.0.0 — Research Quality and Governance Center

- Retrieval, citation, route, latency, and fallback benchmarks
- Source approval, freshness controls, prompt/model/index provenance, and rollback
- Privacy-minimized analytics and public methodology

## v7.0.0 — Connected Research Intelligence Platform

- Persistent research workspaces
- Multi-step investigations and evidence collections
- Cross-platform research workflows
- Stable public API, provider-independent generation boundary, and auditable history

## Completed foundation

v6.2.1 repaired WordPress indexing, endpoint diagnostics, rate limiting, nonce retry, and the terminal prompt. v6.2.0 introduced the Render-ready knowledge-intelligence service. v6.1.x restored live AI and provider diagnostics. v6.0.x established the integrated research-guidance platform and collision-safe bootstrap.


## v7.0.0 — Research Quality and Governance Center — Complete

Answer traceability, source approval and freshness controls, retention, quality evaluation, release gates, governance export, and public methodology.

## v7.0.0 — Connected Research Intelligence Platform — Complete

## Beyond v7.0.0

Future work should be maintenance-led: destination intake adoption, project collaboration permissions, structured conflict resolution, long-running workflow orchestration, and production usage evaluation. These should extend the stable v7 contracts rather than replace them.

## v7.0.7 — Durable Incremental Index Activation — Complete

- Restart-safe shadow-index activation
- Bounded record, chunk, and checksum cursors
- Atomic verified index switch
- v7.0.6 transaction migration and WordPress replay recovery
- Persistent data-directory support and activation diagnostics

## v7.1.0 — Transaction-State Reconciliation and Durable Recovery — Complete

- WordPress/backend expected-batch manifest comparison
- Explicit committed, activate, replay-missing, and replay-all actions
- Empty-shell and mismatched-transaction recovery
- Missing-batch byte-offset replay
- Recovery-generation reset for exhausted v7.0.7 jobs
- Persistent Render disk auto-detection and transaction diagnostics


## v7.1.0 — Neon Postgres Durable Index — Complete

Persistent Neon Postgres generations, pgvector embeddings, idempotent batch replay, verified active-generation switching, and free-tier storage diagnostics.
