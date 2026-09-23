# Research Librarian AI Python Backend v8.6.0

FastAPI backend for durable Sustainable Catalyst acquisition, indexing, advanced retrieval/reranking, connected research projects, governance, typed handoffs, and first-class Platform Core v3.3.0+ integration.


## v8.5 document intelligence and scholarly parsing

- Deterministic text, Markdown, HTML, and PDF structural extraction.
- Sections/page provenance feed existing section-aware chunks.
- DOI/arXiv/PMID/ISBN/URL discovery plus bibliography and citation mentions.
- Figure/table/equation labels and captions are retained as research metadata.
- Synchronous `/v1/documents/parse` and durable asynchronous `/v1/documents/parse/async`.
- Parsing does not assign truth/evidence quality; Platform Core governs promoted evidence.

## v8.4 advanced retrieval and reranking

- Deterministic, non-generative query decomposition and inspectable `/v1/retrieval/plan`.
- Multi-query candidate retrieval over exact-title, BM25, optional semantic similarity, and reciprocal-rank fusion.
- Transparent reranking with query/title coverage, phrase alignment, multi-query consensus, and lexical/semantic support.
- Typed metadata, taxonomy, source, series, record, URL-prefix, and modified-date filtering before ranking.
- Canonical URL, content-hash, and near-duplicate suppression followed by bounded MMR-style diversity selection.
- Retrieval relevance remains separate from evidence quality and Platform Core governance.


## v8.3 durable asynchronous processing

- Production queue: Postgres/Neon `sc_rl_async_jobs` + `sc_rl_async_job_events`.
- Worker claim: `FOR UPDATE SKIP LOCKED` with durable worker leases and heartbeats.
- Local/test queue: SQLite `async_jobs.sqlite3` with `BEGIN IMMEDIATE` claims.
- Retry: bounded exponential backoff plus expired-lease recovery.
- Document processing: normalize → stage/index → restart-safe activation → optional embedding → read-back validation.
- Authenticated API: `/v1/jobs/*`.

The queue is operational infrastructure, not a truth/evidence authority. Governed research objects remain in Platform Core.

## v8.2 Platform Core boundary

- Private Core service default: `http://sc-core:8090` on the shared `sc-internal` network.
- Core writes require `SC_RL_CORE_WRITE_API_KEY` and are sent as `X-SC-API-Key`.
- Librarian-to-Core writes create durable `platform_core_bindings` with deterministic identity and idempotency metadata.
- Research Librarian owns ingestion/document intelligence/retrieval; Core owns governed research/reasoning/provenance objects.
- No automatic truth or conclusion promotion is enabled.

## Runtime

Python 3.12.12. Production knowledge generations and v8.3 asynchronous jobs use Postgres/pgvector-compatible infrastructure; ancillary workflow/Core-binding state uses SQLite schema 19. Local/test async jobs use a separate SQLite queue.

## Platform Core integration endpoints

- `GET /v1/core/architecture`
- `GET /v1/core/readiness`
- `GET /v1/core/bindings`
- `POST /v1/core/research-objects/promote`
- `POST /v1/core/research-projects/synchronize`
- `GET /v1/core/research-projects/{core_project_id}/bundle`
- `POST /v1/core/exchange/packages`

All non-public endpoints require `X-SC-RL-Key`.

## Connected platform endpoints

- `GET /v1/platform/api`
- `GET /v1/platform/summary`
- `GET|POST /v1/projects`
- `GET /v1/projects/{project_id}`
- `POST /v1/investigations`
- `POST /v1/projects/entities`
- `GET /v1/projects/{project_id}/entities`
- `POST /v1/workflows/template`
- `POST /v1/research/contradictions`
- `POST /v1/research/uncertainties`
- `POST /v1/projects/{project_id}/backup`
- `GET /v1/platform/backups`
- `POST /v1/platform/backups/import`

All non-public endpoints require `X-SC-RL-Key`.

## Generation boundary

`generation_adapter.py` provides `sc-generation-adapter/1.0`. Project state, retrieval, governance, and deterministic fallback do not depend on a specific generation provider.
