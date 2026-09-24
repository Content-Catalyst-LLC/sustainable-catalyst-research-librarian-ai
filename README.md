# Sustainable Catalyst Research Librarian AI v9.0.0

Research Librarian AI is the Python-backed acquisition, document-intelligence, source-identity, indexing, retrieval, collaboration, and research-orchestration layer for Sustainable Catalyst. **v9.0.0 adds the Unified Research Intelligence Runtime: a governed 12-stage research lifecycle that composes the v8.x subsystems into one deterministic, durable and reproducible research-run contract without bypassing human review or Platform Core authority.**

### v9.0.0 architecture

The unified runtime coordinates discovery, ingestion, scholarly parsing, canonical source identity, retrieval, evidence governance, findings/claims, argument/contradiction work, statistical planning, visual research, project-state synchronization, and reproducibility. The runtime can execute safe local planning/extraction stages and emit one content-addressed run manifest; promoted research objects still require the existing explicit Core promotion/synchronization endpoints and their human-review gates.

### New v9.0.0 backend resources

- `GET /v1/core/unified-research/capabilities`
- `GET /v1/core/unified-research/readiness`
- `POST /v1/core/unified-research/plan`
- `POST /v1/core/unified-research/execute`
- durable job type `unified-research-runtime`

### v8.12.0 architecture

- **Renderer-neutral visual plans:** citation networks, evidence/claim/finding maps, contradiction maps, argument graphs, statistical/uncertainty views, provenance graphs, timelines, source lineage, and concept maps.
- **Explicit relations only:** visual graph edges are preserved only when supplied by the researcher/reviewer; the Librarian does not infer support, contradiction, causality, or relevance edges from visual form.
- **Core visual authority:** approved plans register canonical Platform Core visual reasoning objects, semantic elements/layers/relations, immutable snapshots, and optional unified-research-session visual bindings.
- **Rendering boundary:** the Librarian does not perform layout, SVG/Canvas/WebGL rendering, GPU work, animation, or visual inference. Specialist visual runtimes remain rendering authorities.
- **Human review gate:** plans default to `pending`; Core promotion requires `approved` and an explicit reviewer identity.
- **Durable planning:** `visual-research-plan` is supported by the Postgres durable job runtime.

### New v8.12.0 backend resources

`GET /v1/core/visual-research/capabilities`, `GET /v1/core/visual-research/readiness`, `POST /v1/core/visual-research/plan`, and `POST /v1/core/visual-research/promote`; generic durable jobs also accept `visual-research-plan`.

### v8.10.0 architecture

- **Declared argument planning:** reviewer-supplied Core findings, claims, evidence, roles, and relations become a deterministic pending argument plan.
- **No relation inference:** support, contradiction, qualification, dependency, and contextual relations are preserved only when explicitly supplied.
- **Contradiction inspection:** the Librarian can surface Core contradiction candidates for review without automatically resolving them.
- **Governed Core graph:** approved plans create Core arguments, nodes, edges, and open tensions under `sc.research.argument-evidentiary-synthesis.v1`.
- **Researcher-authored synthesis:** synthesis prose must be supplied by the researcher/reviewer; the Librarian does not generate a conclusion from it.
- **Human review gate:** plans default to `pending`; Core promotion requires `approved` and an explicit reviewer identity.
- **Durable planning:** `argument-synthesis-plan` is supported by the Postgres durable job runtime.

### New v8.10.0 backend resources

`GET /v1/core/argument-synthesis/capabilities`, `POST /v1/core/argument-synthesis/plan`, `GET /v1/core/argument-synthesis/contradictions/{core_project_id}`, and `POST /v1/core/argument-synthesis/promote`; generic durable jobs also accept `argument-synthesis-plan`.

### v8.9.0 architecture

- **Deterministic candidate extraction:** Python sentence segmentation and transparent cue rules identify candidate findings and claims without generative rewriting.
- **Evidence-bound candidates:** local evidence IDs resolve through v8.7 bindings to governed Platform Core EvidenceRecord IDs when available.
- **Human review gate:** every extracted candidate defaults to `pending`; Core promotion requires explicit `approved` plus a reviewer identity.
- **Conservative evidence semantics:** links default to `contextualizes` unless a reviewer/caller explicitly supplies supports/contradicts/qualifies or another Core relation.
- **Governed Core registration:** approved candidates enter Core as `proposed`, preserving revision history and avoiding automatic acceptance or truth determination.
- **Durable execution:** `research-intelligence-extraction` is available through the Postgres durable-job runtime.

### v8.9.0 backend resources

`GET /v1/core/research-intelligence/capabilities`, `POST /v1/core/research-intelligence/extract`, and `POST /v1/core/research-intelligence/promote`.

### v8.8.0 architecture

- **Unified project binding:** every synchronized Librarian project is anchored to its governed Platform Core unified research project identity.
- **Immutable Core project-state versions:** changed Librarian project state creates a new Core project-state version; unchanged state replays idempotently.
- **Cross-product bindings:** Research contexts, Research Rooms, Library sources, open questions, lifecycles, and project entities become declared Core project-state bindings.
- **Declared lineage:** dependency edges explicitly relate synchronized objects to the project without inferring causal or evidentiary meaning.
- **Governance boundary:** synchronization does not determine truth, publish research, create claims, advance workflow, or execute research code.
- **Core authority:** Platform Core v3.3+ owns immutable project-state versions, cross-product bindings, lineage, and reproducibility state; the Librarian owns source/document/retrieval intelligence and synchronization orchestration.

### v8.8.0 backend resources

`GET /v1/core/research-sync/capabilities`, `POST /v1/core/research-sync/plan`, and `POST /v1/core/research-sync/synchronize`.

### v8.7.0 architecture

- **Source snapshot promotion:** hydrated canonical v8.6 sources can become immutable Platform Core `SourceSnapshot` objects.
- **Passage evidence promotion:** selected passages can become Core `EvidenceRecord` objects anchored to their promoted source snapshot.
- **Governance defaults:** passage promotions default to `neutral`, `unreviewed`, and no confidence value; the bridge does not infer truth, stance, or evidentiary strength.
- **Durable lineage:** every promotion creates a Librarian↔Core binding carrying canonical source identity, local IDs, Core IDs, payload hash, idempotency key, and synchronization state.
- **Fail closed:** citation-only stubs cannot be promoted as source snapshots, snapshot/evidence bindings are immutable, and passage promotion requires a synchronized snapshot binding.
- **Core authority:** Platform Core v3.3+ remains authoritative for governed evidence, reviews, claims, arguments, lineage, reasoning, and reproducibility.

### New v8.7.0 backend resources

`GET /v1/core/evidence/capabilities`, `POST /v1/core/evidence/source-snapshots/promote`, and `POST /v1/core/evidence/passages/promote`.

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

`/v1/core/argument-synthesis/capabilities`, `/v1/core/argument-synthesis/plan`, `/v1/core/argument-synthesis/contradictions/{core_project_id}`, `/v1/core/argument-synthesis/promote`, `/v1/core/research-intelligence/capabilities`, `/v1/core/research-intelligence/extract`, `/v1/core/research-intelligence/promote`, `/v1/core/research-sync/capabilities`, `/v1/core/research-sync/plan`, `/v1/core/research-sync/synchronize`, `/v1/core/evidence/capabilities`, `/v1/core/evidence/source-snapshots/promote`, `/v1/core/evidence/passages/promote`, `/v1/sources/capabilities`, `/v1/sources/resolve`, `/v1/sources/{canonical_source_id}`, `/v1/sources/{canonical_source_id}/graph`, `/v1/sources/{canonical_source_id}/citations`, `/v1/documents/capabilities`, `/v1/documents/parse`, `/v1/documents/parse/async`, `/v1/retrieval/plan`, `/v1/retrieve`, `/v1/retrieve/explain`, `/v1/core/architecture`, `/v1/core/readiness`, `/v1/core/bindings`, `/v1/core/research-objects/promote`, `/v1/core/research-projects/synchronize`, `/v1/core/exchange/packages`, `/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/library/object-model`, `/v1/library/objects`, `/v1/research/contexts`, `/v1/research/contexts/{context_id}/evidence-quality`, `/v1/research/sources/evaluate`, `/v1/research/evidence/compare`, `/v1/research/evidence/gaps`, `/v1/research/state/summary`, `/v1/research/activity`, `/v1/research/object-states`, `/v1/research/questions`, `/v1/research/rooms`, `/v1/research/rooms/{room_id}`, `/v1/research/rooms/{room_id}/members`, `/v1/research/rooms/{room_id}/evidence`, `/v1/research/rooms/{room_id}/questions`, `/v1/research/rooms/{room_id}/disagreements`, `/v1/research/rooms/{room_id}/activity`, `/v1/research/rooms/{room_id}/synthesis`, `/v1/federation/providers`, `/v1/federation/search`, `/v1/federation/searches`, `/v1/federation/searches/{search_id}`, `/v1/federation/searches/{search_id}/results/{result_id}/save`, `/v1/workspace/promotions/catalog`, `/v1/workspace/promotions`, `/v1/workspace/promotions/{promotion_id}`, `/v1/workspace/promotions/{promotion_id}/receipt`, `/v1/research/lifecycle/catalog`, `/v1/research/lifecycles`, `/v1/research/lifecycles/{lifecycle_id}`, `/v1/research/lifecycles/{lifecycle_id}/summary`, `/v1/research/lifecycles/{lifecycle_id}/transition`, `/v1/research/lifecycles/{lifecycle_id}/checkpoint`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

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

See `docs/V8100_ARGUMENT_CONTRADICTION_SYNTHESIS_INTEGRATION.md`, `docs/V890_FINDING_CLAIM_EVIDENCE_EXTRACTION_PIPELINE.md`, `docs/V880_CORE_RESEARCH_OBJECT_SYNCHRONIZATION.md`, `docs/V870_CORE_EVIDENCE_BRIDGE.md`, `docs/V860_SOURCE_IDENTITY_DEDUPLICATION_CITATION_GRAPH.md`, `docs/V850_DOCUMENT_INTELLIGENCE_SCHOLARLY_PARSING.md`, `docs/V840_ADVANCED_RETRIEVAL_RERANKING_ENGINE.md`, `docs/V800_UNIFIED_RESEARCH_INTELLIGENCE_LIFECYCLE.md`, `docs/V770_GLOBAL_LIBRARY_DISCOVERY_FEDERATED_RESEARCH.md`, `docs/V760_WORKSPACE_RESEARCH_HANDOFF_ARTIFACT_PROMOTION.md`, `docs/V750_COLLABORATIVE_RESEARCH_ROOM_INTELLIGENCE.md`, `docs/V740_PERSISTENT_RESEARCH_STATE_READING_HISTORY_OPEN_QUESTIONS.md`, `docs/V730_SOURCE_EVALUATION_EVIDENCE_COMPARISON_RESEARCH_QUALITY_SIGNALS.md`, and `docs/INSTALL.md`.
