# Research Librarian AI Python Backend v6.4.0

This FastAPI service provides exact-title, section-aware BM25, optional semantic, and reciprocal-rank retrieval with citation-verified Gemini synthesis. WordPress remains the canonical publishing, snapshot, and recovery layer.

## Storage model

SQLite schema version 5 stores:

- active knowledge records and metadata;
- transactional staging jobs and rejected-record history;
- tombstones and bounded rollback snapshots;
- deterministic section/page retrieval chunks;
- retained chunk embeddings and embedding-run history.

The filesystem may be ephemeral. WordPress can restore an empty runtime index from its latest verified private gzip snapshot. Chunks are rebuilt automatically, and embeddings can be repopulated through bounded batches.

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
SC_RL_EMBEDDING_MODEL=gemini-embedding-001
SC_RL_SEMANTIC_ENABLED=true
SC_RL_SEMANTIC_QUERY_EMBEDDINGS=true
SC_RL_CHUNK_MAX_WORDS=220
SC_RL_CHUNK_OVERLAP_WORDS=35
SC_RL_EMBEDDING_BATCH_LIMIT=20
SC_RL_CITATION_REQUIRED=true
SC_RL_MAX_RUNTIME_SNAPSHOTS=5
SC_RL_STARTUP_WARMUP_SECONDS=12
SC_RL_STALLED_JOB_SECONDS=1800
SC_RL_MAX_REJECTION_DETAILS=100
```

## Knowledge and retrieval endpoints

```text
GET  /startup
GET  /status
GET  /v1/knowledge/summary
GET  /v1/knowledge/manifest
GET  /v1/knowledge/snapshots
GET  /v1/knowledge/snapshots/validate
GET  /v1/knowledge/embeddings/status
POST /v1/knowledge/maintenance
POST /v1/knowledge/sync
POST /v1/knowledge/rollback
POST /v1/knowledge/embeddings/process
POST /v1/retrieve
POST /v1/retrieve/explain
POST /v1/ask
```

Knowledge endpoints require `X-SC-RL-Key` when `SC_RL_BACKEND_API_KEY` is configured.

## Retrieval behavior

Exact title matches receive explicit priority. BM25 operates over section-level chunks. Semantic ranking participates only when the feature is enabled and embeddings exist. Reciprocal-rank fusion combines the rankings. Generated answers are checked for unknown evidence labels and unknown URLs before release; verification failure triggers deterministic evidence fallback.

## Render

The root `render.yaml` pins Python 3.12.12. No paid persistent disk or vector database is required. A persistent disk may be added later as an optimization, not as the canonical source of truth.
