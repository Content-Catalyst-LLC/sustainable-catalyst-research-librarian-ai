# Sustainable Catalyst Research Librarian AI v8.5.0

Research Librarian AI is the Python-backed acquisition, document-intelligence, indexing, retrieval, collaboration, and research-orchestration layer for Sustainable Catalyst. **v8.5.0 adds deterministic scholarly/document parsing on top of the v8.4 retrieval engine, v8.3 durable processing runtime, and v8.2 Platform Core integration.**

### v8.5.0 architecture

- **Document intelligence:** deterministic parsing for text, Markdown, HTML, and PDF (`pypdf`).
- **Scholarly structure:** sections, page provenance, bibliography entries, citation mentions, figures, tables, equations, and common scholarly identifiers.
- **Retrieval integration:** parsed sections are written into existing knowledge-record metadata and consumed by section-aware chunking and v8.4 advanced retrieval.
- **Durable parsing:** large parses can run through the v8.3 Postgres/SQLite durable job runtime.
- **Governance boundary:** parsing is not a truth/evidence-quality judgment; Platform Core v3.3+ remains authoritative for governed evidence, reasoning, provenance, and lineage.
- **OCR boundary:** image-only PDFs are reported explicitly; OCR is not silently fabricated.

### New v8.5.0 backend resources

`GET /v1/documents/capabilities`, `POST /v1/documents/parse`, and `POST /v1/documents/parse/async`.

## v8.0.0 highlights

- Unifies the v7.2–v7.7 research capabilities into **Frame → Discover → Evaluate → Organize → Collaborate → Synthesize → Promote → Preserve**.
- Adds durable lifecycle records, transition events, deterministic readiness signals, blockers, next actions, and immutable fingerprinted checkpoints.
- Requires explicit human confirmation for every lifecycle stage transition; no AI or heuristic can silently advance research state.
- Keeps lifecycle/readiness metadata outside evidence, truth judgments, editorial approval, and publication.
- Carries lifecycle events and checkpoints in project backup/export while preserving Library, Research Room, federated-discovery, and Workspace-promotion provenance boundaries.
- Advances ancillary SQLite to schema 18, Connected Research API to 2.0, and public workspace to 3.0 without changing the Neon/Postgres knowledge-index schema.

## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI uses Neon/Postgres for production knowledge generations, source records, retrieval chunks, and pgvector embeddings. SQLite remains the local-development and ancillary governance/workspace/Library-context/research-state/collaboration/promotion/lifecycle/Core-binding store. v8.3+ asynchronous jobs use Postgres in production and a separate SQLite queue only for local/test operation. Generation is isolated behind `sc-generation-adapter/1.0`; deterministic retrieval and project continuity remain usable when generation is unavailable.

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

`/v1/retrieval/plan`, `/v1/retrieve`, `/v1/retrieve/explain`, `/v1/core/architecture`, `/v1/core/readiness`, `/v1/core/bindings`, `/v1/core/research-objects/promote`, `/v1/core/research-projects/synchronize`, `/v1/core/exchange/packages`, `/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/library/object-model`, `/v1/library/objects`, `/v1/research/contexts`, `/v1/research/contexts/{context_id}/evidence-quality`, `/v1/research/sources/evaluate`, `/v1/research/evidence/compare`, `/v1/research/evidence/gaps`, `/v1/research/state/summary`, `/v1/research/activity`, `/v1/research/object-states`, `/v1/research/questions`, `/v1/research/rooms`, `/v1/research/rooms/{room_id}`, `/v1/research/rooms/{room_id}/members`, `/v1/research/rooms/{room_id}/evidence`, `/v1/research/rooms/{room_id}/questions`, `/v1/research/rooms/{room_id}/disagreements`, `/v1/research/rooms/{room_id}/activity`, `/v1/research/rooms/{room_id}/synthesis`, `/v1/federation/providers`, `/v1/federation/search`, `/v1/federation/searches`, `/v1/federation/searches/{search_id}`, `/v1/federation/searches/{search_id}/results/{result_id}/save`, `/v1/workspace/promotions/catalog`, `/v1/workspace/promotions`, `/v1/workspace/promotions/{promotion_id}`, `/v1/workspace/promotions/{promotion_id}/receipt`, `/v1/research/lifecycle/catalog`, `/v1/research/lifecycles`, `/v1/research/lifecycles/{lifecycle_id}`, `/v1/research/lifecycles/{lifecycle_id}/summary`, `/v1/research/lifecycles/{lifecycle_id}/transition`, `/v1/research/lifecycles/{lifecycle_id}/checkpoint`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- Neon-compatible PostgreSQL with pgvector for the production knowledge index
- SQLite schema 19 for local development and ancillary platform/Library/research-state/collaboration/promotion/lifecycle/Core-binding records
- Advanced retrieval schema `sc-research-librarian-advanced-retrieval/1.0` with deterministic multi-query planning, reranking, deduplication, and diversity selection
- Async job runtime schema `sc-research-librarian-async-runtime/1.0`; Postgres production queue uses `sc_rl_async_jobs` / `sc_rl_async_job_events`
- Knowledge-index schema remains `sc-research-librarian-knowledge-index/13.0`
- WordPress 6.0+
- No Render persistent disk is required for the durable production knowledge index

See `docs/V840_ADVANCED_RETRIEVAL_RERANKING_ENGINE.md`, `docs/V800_UNIFIED_RESEARCH_INTELLIGENCE_LIFECYCLE.md`, `docs/V770_GLOBAL_LIBRARY_DISCOVERY_FEDERATED_RESEARCH.md`, `docs/V760_WORKSPACE_RESEARCH_HANDOFF_ARTIFACT_PROMOTION.md`, `docs/V750_COLLABORATIVE_RESEARCH_ROOM_INTELLIGENCE.md`, `docs/V740_PERSISTENT_RESEARCH_STATE_READING_HISTORY_OPEN_QUESTIONS.md`, `docs/V730_SOURCE_EVALUATION_EVIDENCE_COMPARISON_RESEARCH_QUALITY_SIGNALS.md`, and `docs/INSTALL.md`.
