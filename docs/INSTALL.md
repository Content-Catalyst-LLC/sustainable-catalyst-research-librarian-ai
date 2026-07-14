# Install Research Librarian AI v6.5.0

## 1. Push the repository

Use `PUSH_RESEARCH_LIBRARIAN_V650_PY312.sh`. The script requires and verifies Python 3.12, clears macOS launcher overrides, validates both Python import layouts, runs every WordPress release contract, verifies the public-workspace manifest, and creates tag `v6.5.0`.

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

Recommended settings remain:

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

No paid vector database or persistent Render disk is required.

## 3. Install the WordPress plugin

Upload `sustainable-catalyst-research-librarian-ai-v6.5.0.zip`, replace the installed plugin, and activate it. Existing settings, snapshots, records, chunks, embeddings, calibration profiles, benchmarks, ledgers, and queued editorial changes are retained.

## 4. Synchronize and verify

Open **Research Librarian AI → Python Intelligence**, save the backend URL and shared key, then run:

1. **Test Backend**
2. **Validate Snapshots**
3. **Transactional Full Sync**
4. Confirm WordPress and backend counts and checksums match
5. Confirm indexed chunks are present
6. Process embedding batches to the desired semantic coverage
7. Run the retrieval benchmark once with the default `balanced-v6.5.0` profile

## 5. Verify the public workspace

Open a page containing `[sustainable_catalyst_research_librarian_ai]` and confirm:

- all eight research-mode controls are visible and keyboard operable;
- the question field remains black with green monospace text and a green focus state;
- answer, evidence, source, path, and action cards remain light;
- an exact title suggestion can be selected with the keyboard;
- the selected mode reaches the backend and appears in the answer header;
- follow-up prompts remain scoped to the current research session;
- **Reset session** clears conversational continuity;
- Markdown, JSON, research-note, print, and handoff actions work;
- cold-start progress is visible while verified fallback remains available;
- mobile layouts collapse to one column without horizontal overflow.

## 6. Verify evidence behavior

Confirm that:

- exact canonical titles remain first;
- similarly titled records produce an ambiguity clarification when appropriate;
- excluded records do not appear;
- weak evidence does not trigger AI synthesis;
- unsupported numeric claims are rejected;
- generated citation labels and URLs map to synchronized evidence;
- deterministic evidence fallback remains available when verification fails.

## 7. Recovery operations

The v6.3.x recovery controls remain available:

- **Repair Stalled Jobs**
- **Recover Empty Backend**
- **Validate Snapshots**
- **Clear Pending Retries**
- **Export Sync and Recovery Log**
- **Rollback Runtime Index** after integrity validation
