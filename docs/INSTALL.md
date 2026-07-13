# Install Research Librarian AI v6.4.0

## 1. Push the repository

Use `PUSH_RESEARCH_LIBRARIAN_V640_PY312.sh`. The script requires and verifies Python 3.12, clears macOS launcher overrides, validates both Python import layouts, runs all WordPress release contracts, and creates tag `v6.4.0`.

## 2. Deploy or update Render

Use `render.yaml` or configure:

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`
- Python: `3.12.12`

Required secrets:

```text
SC_RL_BACKEND_API_KEY=<shared WordPress/backend secret>
SC_RL_GEMINI_API_KEY=<Gemini key>
```

Recommended v6.4.0 settings:

```text
SC_RL_SEMANTIC_ENABLED=true
SC_RL_SEMANTIC_QUERY_EMBEDDINGS=true
SC_RL_CHUNK_MAX_WORDS=220
SC_RL_CHUNK_OVERLAP_WORDS=35
SC_RL_EMBEDDING_BATCH_LIMIT=20
SC_RL_CITATION_REQUIRED=true
SC_RL_STARTUP_WARMUP_SECONDS=12
SC_RL_STALLED_JOB_SECONDS=1800
SC_RL_MAX_REJECTION_DETAILS=100
SC_RL_MAX_RUNTIME_SNAPSHOTS=5
```

No paid vector database or persistent Render disk is required. WordPress remains the canonical snapshot source; SQLite and embeddings are recoverable runtime assets.

## 3. Install the WordPress plugin

Upload `sustainable-catalyst-research-librarian-ai-v6.4.0.zip`, replace the installed plugin, and activate it. Existing settings, recovery snapshots, ledgers, and queued editorial changes are retained.

## 4. Build the retrieval index

Open **Research Librarian AI → Python Intelligence**, save the backend URL and shared key, then run:

1. **Test Backend**
2. **Validate Snapshots**
3. **Transactional Full Sync**
4. Confirm WordPress and backend record counts and checksums match
5. Confirm the backend reports indexed chunks
6. Select **Process Embedding Batch** repeatedly until the desired semantic coverage is reached

Exact-title and BM25 retrieval work before embeddings are processed. Semantic retrieval activates progressively as coverage increases.

## 5. Verify public behavior

Ask one exact-title question and one conceptual question. Confirm:

- the exact title appears first for the title query;
- conceptual results identify a matching section or page where available;
- evidence cards show citation labels and supporting passages;
- retrieval diagnostics identify the active mode;
- an unverified generated citation cannot appear publicly;
- the answer falls back to verified evidence if Gemini is unavailable.

## 6. Recovery operations

Keep automatic cold-start recovery enabled. Existing v6.3.1 controls remain available:

- **Repair Stalled Jobs**
- **Recover Empty Backend**
- **Validate Snapshots**
- **Clear Pending Retries**
- **Export Sync and Recovery Log**
- **Rollback Runtime Index** after integrity validation
