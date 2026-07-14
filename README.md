# Sustainable Catalyst Research Librarian AI v6.5.0

## Production Public Research Workspace

Research Librarian AI is the site-scoped discovery and research-guidance layer for Sustainable Catalyst. WordPress remains the canonical publishing and recovery source. FastAPI provides a restart-safe SQLite retrieval index, exact-title and section-aware BM25 ranking, optional Gemini semantic similarity, calibrated reciprocal-rank fusion, verified citations, and deterministic evidence fallback.

v6.5.0 turns that retrieval foundation into a finished public workspace. Visitors can choose a research mode, receive a readable answer before diagnostics, inspect verified evidence and related records, continue a bounded research session, and export the result without turning the Librarian into an unrestricted chatbot.

## v6.5.0 highlights

- Adds eight explicit public research modes: auto-detect, title, subject, path, evidence, analysis, comparison, and decision preparation.
- Introduces a responsive two-pane workspace with a focused prompt surface and a larger answer/evidence surface.
- Preserves the black prompt, green monospace text, green caret, subdued green placeholder, and accessible focus state.
- Keeps answer, evidence, citation, source, path, and action cards light and readable.
- Adds answer-first workspace headers, source counts, active-mode labels, and generated-versus-deterministic response status.
- Adds short site-scoped follow-up continuity, suggested next questions, and an explicit session reset.
- Adds accessible live title suggestions with keyboard navigation and automatic title-mode selection.
- Adds copy, Markdown, JSON, research-note, print, session, feedback, and typed-handoff controls.
- Adds visible startup and recovery progress while verified WordPress fallback remains available.
- Preserves v6.4.1 retrieval calibration, v6.4.0 citation verification, and v6.3.x durability and recovery controls.

## Public workspace sequence

1. Choose a research mode or leave mode selection on auto-detect.
2. Enter a question, exact title, evidence need, comparison, analytical task, path request, or decision task.
3. Research Librarian retrieves synchronized Sustainable Catalyst records before generation.
4. The evidence gate determines whether generated synthesis is allowed.
5. The workspace presents the primary answer, verified evidence, related records, research path, and controlled actions separately.
6. Suggested follow-ups remain scoped to the active evidence and short session history.
7. Export or hand off the result without silently changing another workspace.

## Administration

Open **Research Librarian AI → Python Intelligence** to:

- synchronize and recover the durable index;
- inspect records, chunks, embeddings, snapshots, retries, and staging jobs;
- set retrieval weights, thresholds, context limits, source multipliers, and exclusions;
- run the retrieval benchmark and compare lexical and hybrid MRR;
- process bounded embedding batches;
- validate snapshots, repair stalled jobs, roll back runtime snapshots, and export operations diagnostics.

## Public shortcodes

```text
[sustainable_catalyst_research_librarian_ai]
[sc_research_librarian]
[sc_research_guidance_platform]
[sc_research_guidance_journey]
```

Historical shortcode modes remain available for route maps, index summaries, guided paths, evaluation summaries, handoff summaries, and operations views.

## Backend development

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

The Render blueprint pins Python 3.12.12. Required production secrets are `SC_RL_BACKEND_API_KEY` and `SC_RL_GEMINI_API_KEY`. A paid vector database or persistent Render disk is not required.

## Release documentation

- `docs/V650_PRODUCTION_PUBLIC_RESEARCH_WORKSPACE.md`
- `docs/V641_RETRIEVAL_CALIBRATION_REGRESSION.md`
- `docs/V640_HYBRID_RETRIEVAL_CITATION_ENGINE.md`
- `docs/V631_COLD_START_RECOVERY_HARDENING.md`
- `docs/V630_DURABLE_KNOWLEDGE_INDEX_SYNC_LEDGER_RECOVERY.md`
- `docs/INSTALL.md`
- `docs/ROADMAP.md`

## v6.5.0 API addition

```text
POST /v1/session/reset
```

The ask response now includes `research_mode`, `follow_up_prompts`, `workspace`, and `session_turns`. Existing health, startup, status, synchronization, manifest, snapshot, maintenance, rollback, embedding, retrieval, benchmark, related-title, and ask endpoints remain available.

## License

MIT
