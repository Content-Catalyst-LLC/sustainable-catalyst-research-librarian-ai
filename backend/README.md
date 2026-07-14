# Research Librarian AI Python Backend v7.0.0

FastAPI backend for durable Sustainable Catalyst retrieval, connected research projects, governance, typed handoffs, and portable backup/recovery.

## Runtime

Python 3.12.12 with SQLite schema version 10.

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
