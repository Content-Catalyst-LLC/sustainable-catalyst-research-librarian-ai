# Research Librarian AI Python Backend v8.2.0

FastAPI backend for durable Sustainable Catalyst acquisition, indexing, retrieval, connected research projects, governance, typed handoffs, and first-class Platform Core v3.3.0+ integration.

## v8.2 Platform Core boundary

- Private Core service default: `http://sc-core:8090` on the shared `sc-internal` network.
- Core writes require `SC_RL_CORE_WRITE_API_KEY` and are sent as `X-SC-API-Key`.
- Librarian-to-Core writes create durable `platform_core_bindings` with deterministic identity and idempotency metadata.
- Research Librarian owns ingestion/document intelligence/retrieval; Core owns governed research/reasoning/provenance objects.
- No automatic truth or conclusion promotion is enabled.

## Runtime

Python 3.12.12. Production knowledge generations use Postgres/pgvector; ancillary workflow/Core-binding state uses SQLite schema 19.

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
