# Sustainable Catalyst Research Librarian AI v6.7.0

WordPress remains the canonical publishing, administration, governance, recovery, and public-interface layer. FastAPI provides durable hybrid retrieval, citation-verified synthesis, typed platform handoffs, answer traceability, quality evaluation, and release gates.

## v6.7.0 highlights

- Versioned research-governance policy
- Source approval, exclusion, expiration, and freshness review
- Privacy-minimized answer traces with model, prompt, index, policy, citation, and evidence provenance
- Quality evaluations and release-readiness gates
- Human-reviewed overrides and immutable audit events
- Configurable retention enforcement and governance export
- Public methodology and limitations shortcodes
- Additive SQLite schema version 9

## Trust boundary

Research Librarian may retrieve, rank, synthesize, evaluate, and propose routes. It cannot autonomously publish content, exclude sources, approve ranking changes, or override a failed release gate. Query and answer text are not stored in governance traces unless an administrator explicitly enables those fields.

## Current architecture

- WordPress owns canonical public records and compressed recovery snapshots.
- SQLite provides the recoverable runtime index, chunks, embeddings, traces, reviews, evaluations, and gate history.
- Gemini synthesis is permitted only after retrieval and evidence gates pass.
- Citation and unsupported-claim verification can replace generated prose with deterministic evidence fallback.
- Typed handoffs preserve verified evidence and require explicit user action.

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

- `docs/V660_PLATFORM_INTELLIGENCE_TYPED_HANDOFFS.md`
- `docs/V651_ACCESSIBILITY_PERFORMANCE_INTERFACE_RELIABILITY.md`
- `docs/V650_PRODUCTION_PUBLIC_RESEARCH_WORKSPACE.md`
- `docs/V641_RETRIEVAL_CALIBRATION_REGRESSION.md`
- `docs/V640_HYBRID_RETRIEVAL_CITATION_ENGINE.md`
- `docs/V631_COLD_START_RECOVERY_HARDENING.md`
- `docs/V630_DURABLE_KNOWLEDGE_INDEX_SYNC_LEDGER_RECOVERY.md`
- `docs/INSTALL.md`
- `docs/ROADMAP.md`

## v6.6.0 API and response notes

```text
GET  /v1/platform/capabilities
POST /v1/handoffs/prepare
POST /v1/handoffs/validate
GET  /v1/handoffs/logs
POST /v1/handoffs/artifacts/return
GET  /v1/handoffs/artifacts
POST /v1/session/reset
```

The ask response retains `research_mode`, `follow_up_prompts`, `workspace`, and `session_turns`, and adds `capabilities`, `typed_handoffs`, and `provenance`. The workspace schema is `sc-research-librarian-public-workspace/1.2`. Existing accessibility profiles remain `wcag-focused-v6.5.1` and `staged-v6.5.1` because v6.6.0 preserves that interface contract.

## License

MIT
