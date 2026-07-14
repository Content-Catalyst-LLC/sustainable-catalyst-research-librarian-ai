# Sustainable Catalyst Research Librarian AI v6.5.1

## Accessibility, Performance, and Interface Reliability

Research Librarian AI is the site-scoped discovery and research-guidance layer for Sustainable Catalyst. WordPress remains the canonical publishing and recovery source. FastAPI provides a restart-safe SQLite retrieval index, exact-title and section-aware BM25 ranking, optional Gemini semantic similarity, calibrated reciprocal-rank fusion, verified citations, and deterministic evidence fallback.

v6.5.1 hardens the production public workspace for keyboard, screen-reader, reduced-motion, forced-colors, mobile, and WordPress-theme use. It also reduces duplicate REST traffic, caches title suggestions, cancels superseded requests, stages answer rendering, and replaces browser prompts with an accessible feedback dialog.

## v6.5.1 highlights

- Adds roving-tabindex radio behavior and complete arrow-key navigation for all eight research modes.
- Upgrades title suggestions to a combobox/listbox pattern with active-descendant navigation and result-count announcements.
- Adds progressbar semantics, result focus management, accessible failure focus, reduced-motion support, and forced-colors support.
- Replaces browser prompt feedback with a labeled, keyboard-operable feedback dialog.
- Coalesces and caches health and route requests across shortcode instances.
- Adds five-minute browser and WordPress title-suggestion caches tied to the canonical index checksum.
- Cancels superseded suggestion, answer, and guided-path requests and prevents duplicate in-flight questions.
- Stages direct-answer and evidence rendering, defers the WordPress script, and enables FastAPI gzip responses.
- Adds clipboard fallback, safer download cleanup, theme-scoped controls, admin-bar-aware sticky positioning, and stronger mobile behavior.
- Preserves the black-and-green prompt, light answer/source cards, v6.5.0 research modes, v6.4.x retrieval, and v6.3.x recovery controls.

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

- `docs/V651_ACCESSIBILITY_PERFORMANCE_INTERFACE_RELIABILITY.md`
- `docs/V650_PRODUCTION_PUBLIC_RESEARCH_WORKSPACE.md`
- `docs/V641_RETRIEVAL_CALIBRATION_REGRESSION.md`
- `docs/V640_HYBRID_RETRIEVAL_CITATION_ENGINE.md`
- `docs/V631_COLD_START_RECOVERY_HARDENING.md`
- `docs/V630_DURABLE_KNOWLEDGE_INDEX_SYNC_LEDGER_RECOVERY.md`
- `docs/INSTALL.md`
- `docs/ROADMAP.md`

## v6.5.1 API and response notes

```text
POST /v1/session/reset
```

The ask response retains `research_mode`, `follow_up_prompts`, `workspace`, and `session_turns`. The workspace schema is now `sc-research-librarian-public-workspace/1.1` and advertises accessibility and staged-rendering profiles. Existing health, startup, status, synchronization, manifest, snapshot, maintenance, rollback, embedding, retrieval, benchmark, related-title, and ask endpoints remain available.

## License

MIT
