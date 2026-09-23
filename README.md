# Sustainable Catalyst Research Librarian AI v8.6.0

Research Librarian AI is the Python-backed acquisition, document-intelligence, source-identity, indexing, retrieval, collaboration, and research-orchestration layer for Sustainable Catalyst. **v8.6.0 adds durable canonical source identity, deduplication, and a scholarly citation graph on top of v8.5 document intelligence, v8.4 advanced retrieval, v8.3 durable jobs, and v8.2 Platform Core integration.**

### v8.6.0 architecture

- **Canonical scholarly identity:** DOI → arXiv → PMID → ISBN → canonical URL, then bibliographic fingerprint fallback.
- **Duplicate-safe copies:** publisher URLs, repository copies, PDFs, and other instances can resolve to one canonical work.
- **Citation graph:** bibliography identifiers create persistent outgoing/incoming citation edges. Unknown cited works can exist as stubs and hydrate later.
- **Fail-closed conflicts:** identifiers that point to multiple existing works are never silently merged.
- **Ingestion integration:** v8.5 parsing resolves canonical identity before the existing durable index activation path.
- **Storage:** Postgres is authoritative in production; SQLite is the local/test fallback for the source graph.
- **Core boundary:** Platform Core v3.3+ remains authoritative for governed evidence, findings, claims, reasoning, provenance, lineage, and reproducibility.

### New v8.6.0 backend resources

`GET /v1/sources/capabilities`, `POST /v1/sources/resolve`, `GET /v1/sources/{canonical_source_id}`, `GET /v1/sources/{canonical_source_id}/graph`, and `POST /v1/sources/{canonical_source_id}/citations`.

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

`/v1/sources/capabilities`, `/v1/sources/resolve`, `/v1/sources/{canonical_source_id}`, `/v1/sources/{canonical_source_id}/graph`, `/v1/sources/{canonical_source_id}/citations`, `/v1/documents/capabilities`, `/v1/documents/parse`, `/v1/documents/parse/async`, `/v1/retrieval/plan`, `/v1/retrieve`, `/v1/retrieve/explain`, `/v1/core/architecture`, `/v1/core/readiness`, `/v1/core/bindings`, `/v1/core/research-objects/promote`, `/v1/core/research-projects/synchronize`, `/v1/core/exchange/packages`, `/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/library/object-model`, `/v1/library/objects`, `/v1/research/contexts`, `/v1/research/contexts/{context_id}/evidence-quality`, `/v1/research/sources/evaluate`, `/v1/research/evidence/compare`, `/v1/research/evidence/gaps`, `/v1/research/state/summary`, `/v1/research/activity`, `/v1/research/object-states`, `/v1/research/questions`, `/v1/research/rooms`, `/v1/research/rooms/{room_id}`, `/v1/research/rooms/{room_id}/members`, `/v1/research/rooms/{room_id}/evidence`, `/v1/research/rooms/{room_id}/questions`, `/v1/research/rooms/{room_id}/disagreements`, `/v1/research/rooms/{room_id}/activity`, `/v1/research/rooms/{room_id}/synthesis`, `/v1/federation/providers`, `/v1/federation/search`, `/v1/federation/searches`, `/v1/federation/searches/{search_id}`, `/v1/federation/searches/{search_id}/results/{result_id}/save`, `/v1/workspace/promotions/catalog`, `/v1/workspace/promotions`, `/v1/workspace/promotions/{promotion_id}`, `/v1/workspace/promotions/{promotion_id}/receipt`, `/v1/research/lifecycle/catalog`, `/v1/research/lifecycles`, `/v1/research/lifecycles/{lifecycle_id}`, `/v1/research/lifecycles/{lifecycle_id}/summary`, `/v1/research/lifecycles/{lifecycle_id}/transition`, `/v1/research/lifecycles/{lifecycle_id}/checkpoint`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- Neon-compatible PostgreSQL with pgvector for the production knowledge index
- SQLite schema 19 for local development and ancillary platform/Library/research-state/collaboration/promotion/lifecycle/Core-binding records
- Advanced retrieval schema `sc-research-librarian-advanced-retrieval/1.0` with deterministic multi-query planning, reranking, deduplication, and diversity selection
- Source identity schema `sc-research-librarian-source-identity/1.0` with Postgres production tables for canonical sources, identifiers, instances, authors/institutions, citations, and resolution events.
- Async job runtime schema `sc-research-librarian-async-runtime/1.0`; Postgres production queue uses `sc_rl_async_jobs` / `sc_rl_async_job_events`
- Knowledge-index schema remains `sc-research-librarian-knowledge-index/13.0`
- WordPress 6.0+
- No Render persistent disk is required for the durable production knowledge index

See `docs/V860_SOURCE_IDENTITY_DEDUPLICATION_CITATION_GRAPH.md`, `docs/V850_DOCUMENT_INTELLIGENCE_SCHOLARLY_PARSING.md`, `docs/V840_ADVANCED_RETRIEVAL_RERANKING_ENGINE.md`, `docs/V800_UNIFIED_RESEARCH_INTELLIGENCE_LIFECYCLE.md`, `docs/V770_GLOBAL_LIBRARY_DISCOVERY_FEDERATED_RESEARCH.md`, `docs/V760_WORKSPACE_RESEARCH_HANDOFF_ARTIFACT_PROMOTION.md`, `docs/V750_COLLABORATIVE_RESEARCH_ROOM_INTELLIGENCE.md`, `docs/V740_PERSISTENT_RESEARCH_STATE_READING_HISTORY_OPEN_QUESTIONS.md`, `docs/V730_SOURCE_EVALUATION_EVIDENCE_COMPARISON_RESEARCH_QUALITY_SIGNALS.md`, and `docs/INSTALL.md`.
