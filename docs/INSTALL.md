# Install Research Librarian AI v6.7.0

## 1. Push the repository

Use `PUSH_RESEARCH_LIBRARIAN_V670_PY312.sh`. The script requires and verifies Python 3.12, clears macOS launcher overrides, validates both Python import layouts, runs every WordPress release contract, verifies the research-quality governance manifest, and creates tag `v6.7.0`.

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

Upload `sustainable-catalyst-research-librarian-ai-wordpress-v6.7.0.zip`, replace the installed plugin, and activate it. Existing settings, snapshots, records, chunks, embeddings, calibration profiles, benchmarks, ledgers, and queued editorial changes are retained.

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

- all eight research-mode controls are visible and operable with Arrow keys, Home, and End;
- title suggestions remain focused in the question field while Arrow keys update the active option;
- Enter chooses an active title suggestion and Escape closes the list;
- status, progress, result availability, and suggestion counts are announced;
- the feedback form opens as a labeled dialog without browser prompts;
- reduced-motion and forced-colors modes remain usable;
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


## 8. v6.5.1 performance verification

Confirm that repeated title queries can return `X-SC-RL-Suggestion-Cache: HIT`, stale suggestion requests are cancelled while typing, duplicate answer submissions do not create duplicate in-flight requests, and the FastAPI response headers indicate gzip compression for sufficiently large responses when the client requests it.

## 9. v6.6.0 platform-handoff verification

1. Open **Settings → Research Librarian Handoffs** and confirm each intended destination has an enabled state, URL, and declared version.
2. Open the public Research Librarian and ask one calculation, decision, country-indicator, and experiment question.
3. Confirm only configured destinations appear.
4. Prepare and download a typed handoff, then validate it through the WordPress bridge.
5. Confirm the payload contains `sc-research-handoff/2.0`, a destination contract, verified evidence, and a provenance fingerprint.
6. Test an artifact return against the original handoff in a staging environment.
7. Export the administrator handoff ledger and confirm it contains no provider or integration secrets.


## 10. v6.7.0 governance verification

1. Open **Settings → Research Quality & Governance**.
2. Confirm the active profile is `public-trust-v6.7.0`.
3. Keep query-text and answer-text retention disabled unless there is a documented need.
4. Save the policy with the authenticated administrator as reviewer.
5. Ask a public Research Librarian question and confirm the response provenance contains an answer trace ID and quality summary.
6. Review `/v1/governance/traces` through the authenticated backend or governance export.
7. Approve one test record, place one record under review, and confirm an excluded test record is removed from retrieval.
8. Run a release gate with passing metrics and one with a critical citation failure; confirm the latter is blocked.
9. Run retention first with `dry_run=true` and review candidate counts before deletion.
10. Publish `[sc_research_librarian_methodology]` on the public methodology or Research Librarian page.
