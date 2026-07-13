# Research Librarian AI Python Backend v6.3.1

This FastAPI service provides title-aware retrieval, grounded Gemini synthesis, and a durable transactional runtime index for Sustainable Catalyst. WordPress remains the canonical publishing, snapshot, and recovery layer.

## Storage model

The backend uses SQLite schema 4 under `SC_RL_DATA_DIR` (default `/tmp/sc-research-librarian`). It stores active records, metadata, staging jobs, tombstones, and bounded rollback snapshots. Multi-batch jobs do not change the live index until every expected batch has arrived.

The filesystem may be ephemeral. WordPress automatically restores an empty runtime index from its latest verified private gzip snapshot.

## Local development

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
pytest -q
uvicorn app.main:app --reload
```

## Important environment variables

```text
SC_RL_DATA_DIR=/tmp/sc-research-librarian
SC_RL_BACKEND_API_KEY=<shared secret>
SC_RL_GEMINI_API_KEY=<provider key>
SC_RL_GEMINI_MODEL=gemini-3.5-flash
SC_RL_MAX_RUNTIME_SNAPSHOTS=5
SC_RL_STARTUP_WARMUP_SECONDS=12
SC_RL_STALLED_JOB_SECONDS=1800
SC_RL_MAX_REJECTION_DETAILS=100
```

## Knowledge endpoints

```text
GET  /startup
GET  /v1/knowledge/summary
GET  /v1/knowledge/manifest
GET  /v1/knowledge/snapshots
GET  /v1/knowledge/snapshots/validate
POST /v1/knowledge/maintenance
POST /v1/knowledge/sync
POST /v1/knowledge/rollback
POST /v1/retrieve
POST /v1/ask
```

Knowledge endpoints require `X-SC-RL-Key` when `SC_RL_BACKEND_API_KEY` is configured.

## Render

The root `render.yaml` pins Python 3.12.12. No paid persistent disk is required because the runtime SQLite database is recoverable from WordPress. A persistent disk may still be added later as an optimization, not as the canonical source of truth.
