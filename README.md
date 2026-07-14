# Sustainable Catalyst Research Librarian AI v6.6.1

## Cross-Product Reliability Patch

Research Librarian AI is the site-scoped discovery and research-guidance layer for Sustainable Catalyst. WordPress remains the canonical publishing and recovery source. FastAPI provides durable calibrated retrieval, verified citations, deterministic fallback, destination capability discovery, and versioned typed handoffs.

v6.6.1 hardens the typed handoffs introduced in v6.6.0 with destination-version compatibility checks, short-lived delivery tokens, bounded retry metadata, idempotent event handling, intake receipts, and immutable artifact returns. Existing retrieval, recovery, accessibility, and public-workspace behavior remains intact.

## v6.6.1 highlights

- Adds compatibility states and minimum supported versions for every connected destination.
- Adds short-lived HMAC delivery tokens with explicit refresh and bounded retry operations.
- Adds idempotency protection for preparation, retry, receipt, and artifact-return events.
- Adds destination intake receipts bound to handoff ID, fingerprint, token, and status.
- Adds artifact type, size, destination, and fingerprint validation with immutable artifact IDs.
- Adds SQLite schema version 8 receipts, event ledger, retry state, token expiry, and artifact fingerprints.
- Adds public Retry delivery and Refresh token controls while preserving explicit human confirmation.
- Preserves the black-and-green prompt, light evidence cards, free-tier deployment, calibrated retrieval, and durable recovery.

## v6.6.0 foundation

- Adds `sc-research-handoff/2.0`, `sc-research-route/2.0`, and `sc-research-artifact-return/1.0` contracts.
- Adds capability discovery for Workbench, Decision Studio, Site Intelligence, Lab, and Feature Suggestions.
- Adds destination-specific task contracts for calculations, decisions, place-based intelligence, experiments, and platform requests.
- Adds prepared-handoff and returned-artifact ledgers in additive SQLite schema version 7.
- Adds provenance fingerprints, source IDs, URLs, evidence labels, sections, pages, assumptions, uncertainty, and chain history.
- Adds authenticated prepare, validate, log, artifact-return, and artifact-list backend endpoints.
- Adds a nonce-protected WordPress bridge and administrator capability configuration.
- Adds typed handoff previews and explicit preparation/download controls to the public workspace.
- Preserves v6.5.1 accessibility/performance behavior, the black-and-green prompt, and light evidence cards.

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
