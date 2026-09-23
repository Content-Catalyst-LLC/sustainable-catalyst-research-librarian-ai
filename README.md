# Sustainable Catalyst Research Librarian AI v8.3.0

Research Librarian AI is the Python-backed acquisition, document-intelligence, indexing, retrieval, collaboration, and research-orchestration layer for Sustainable Catalyst. **v8.3.0 adds the durable asynchronous ingestion and document-processing runtime on top of the v8.2 Platform Core integration.**

### v8.3.0 architecture

- **Durable Python job plane:** authenticated `/v1/jobs/*` APIs, idempotent enqueue, priority, retry/backoff, worker leases, event history, cancellation, manual retry, and restart recovery.
- **Postgres-first production queue:** production jobs use the configured Neon/Postgres database and workers claim tasks with `FOR UPDATE SKIP LOCKED`; SQLite is the local/test fallback.
- **Document worker:** normalized document payloads flow through staging, restart-safe index activation, optional embedding, and read-back validation without bypassing the existing knowledge-index transaction model.
- **Research Librarian Python:** owns source acquisition, parsing, chunking, embedding, indexing, retrieval, connectors, document intelligence, and asynchronous processing.
- **Platform Core v3.3+:** remains the authoritative layer for governed research/evidence objects, provenance and lineage, findings/claims/arguments, statistical and visual reasoning, reproducibility, and cross-product exchange.
- **Specialist runtimes:** Workspace, Workbench, Research Lab, Analytics R, and other runtimes perform computation; Core records governed results.
- **WordPress:** presentation, access, configuration, and user interaction rather than the document-processing engine.

v8.3.0 intentionally does **not** duplicate Platform Core reasoning objects and does not enable autonomous truth promotion. The asynchronous runtime performs operational processing; governed evidence and research reasoning continue to cross the v8.2 typed Core boundary.

### New v8.3.0 backend resources

`GET /v1/jobs/runtime`, `GET /v1/jobs`, `POST /v1/jobs`, `POST /v1/jobs/documents`, `GET /v1/jobs/{job_id}`, `GET /v1/jobs/{job_id}/events`, `POST /v1/jobs/{job_id}/retry`, and `DELETE /v1/jobs/{job_id}`.

## v8.0.0 highlights

- Unifies the v7.2–v7.7 research capabilities into **Frame → Discover → Evaluate → Organize → Collaborate → Synthesize → Promote → Preserve**.
- Adds durable lifecycle records, transition events, deterministic readiness signals, blockers, next actions, and immutable fingerprinted checkpoints.
- Requires explicit human confirmation for every lifecycle stage transition; no AI or heuristic can silently advance research state.
- Keeps lifecycle/readiness metadata outside evidence, truth judgments, editorial approval, and publication.
- Carries lifecycle events and checkpoints in project backup/export while preserving Library, Research Room, federated-discovery, and Workspace-promotion provenance boundaries.
- Advances ancillary SQLite to schema 18, Connected Research API to 2.0, and public workspace to 3.0 without changing the Neon/Postgres knowledge-index schema.

## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI uses Neon/Postgres for production knowledge generations, source records, retrieval chunks, and pgvector embeddings. SQLite remains the local-development and ancillary governance/workspace/Library-context/research-state/collaboration/promotion/lifecycle/Core-binding store. v8.3 asynchronous jobs use Postgres in production and a separate SQLite queue only for local/test operation. Generation is isolated behind `sc-generation-adapter/1.0`; deterministic retrieval and project continuity remain usable when generation is unavailable.

## Public shortcodes

- `[sustainable_catalyst_research_librarian_ai]`
- `[sc_research_librarian]`
- `[sc_connected_research_workspace]`
- `[sc_research_projects_summary]`
- `[sc_connected_research_platform_status]`
- `[sc_research_librarian_methodology]`
- `[sc_research_librarian_governance_status]`
- `[sc_research_librarian_platform_handoffs]`

## Backend resources

`/v1/core/architecture`, `/v1/core/readiness`, `/v1/core/bindings`, `/v1/core/research-objects/promote`, `/v1/core/research-projects/synchronize`, `/v1/core/exchange/packages`, `/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/library/object-model`, `/v1/library/objects`, `/v1/research/contexts`, `/v1/research/contexts/{context_id}/evidence-quality`, `/v1/research/sources/evaluate`, `/v1/research/evidence/compare`, `/v1/research/evidence/gaps`, `/v1/research/state/summary`, `/v1/research/activity`, `/v1/research/object-states`, `/v1/research/questions`, `/v1/research/rooms`, `/v1/research/rooms/{room_id}`, `/v1/research/rooms/{room_id}/members`, `/v1/research/rooms/{room_id}/evidence`, `/v1/research/rooms/{room_id}/questions`, `/v1/research/rooms/{room_id}/disagreements`, `/v1/research/rooms/{room_id}/activity`, `/v1/research/rooms/{room_id}/synthesis`, `/v1/federation/providers`, `/v1/federation/search`, `/v1/federation/searches`, `/v1/federation/searches/{search_id}`, `/v1/federation/searches/{search_id}/results/{result_id}/save`, `/v1/workspace/promotions/catalog`, `/v1/workspace/promotions`, `/v1/workspace/promotions/{promotion_id}`, `/v1/workspace/promotions/{promotion_id}/receipt`, `/v1/research/lifecycle/catalog`, `/v1/research/lifecycles`, `/v1/research/lifecycles/{lifecycle_id}`, `/v1/research/lifecycles/{lifecycle_id}/summary`, `/v1/research/lifecycles/{lifecycle_id}/transition`, `/v1/research/lifecycles/{lifecycle_id}/checkpoint`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- Neon-compatible PostgreSQL with pgvector for the production knowledge index
- SQLite schema 19 for local development and ancillary platform/Library/research-state/collaboration/promotion/lifecycle/Core-binding records
- Async job runtime schema `sc-research-librarian-async-runtime/1.0`; Postgres production queue uses `sc_rl_async_jobs` / `sc_rl_async_job_events`
- Knowledge-index schema remains `sc-research-librarian-knowledge-index/13.0`
- WordPress 6.0+
- No Render persistent disk is required for the durable production knowledge index

See `docs/V800_UNIFIED_RESEARCH_INTELLIGENCE_LIFECYCLE.md`, `docs/V770_GLOBAL_LIBRARY_DISCOVERY_FEDERATED_RESEARCH.md`, `docs/V760_WORKSPACE_RESEARCH_HANDOFF_ARTIFACT_PROMOTION.md`, `docs/V750_COLLABORATIVE_RESEARCH_ROOM_INTELLIGENCE.md`, `docs/V740_PERSISTENT_RESEARCH_STATE_READING_HISTORY_OPEN_QUESTIONS.md`, `docs/V730_SOURCE_EVALUATION_EVIDENCE_COMPARISON_RESEARCH_QUALITY_SIGNALS.md`, and `docs/INSTALL.md`.
