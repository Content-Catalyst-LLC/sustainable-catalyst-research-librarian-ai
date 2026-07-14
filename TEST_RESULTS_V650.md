# Research Librarian AI v6.5.0 Validation Report

**Release:** Production Public Research Workspace  
**Validation date:** 2026-07-13  
**Package:** `sustainable-catalyst-research-librarian-ai-v6.5.0.zip`

## Release scope verified

- Eight explicit research modes: auto, title, subject, path, evidence, analyze, compare, and decision.
- Responsive two-pane production workspace with one-column tablet/mobile fallback.
- Black question field with green monospace text, green caret, subdued green placeholder, and accessible focus state.
- Light answer, evidence, citation, source, path, related-record, and action surfaces.
- Answer-first workspace header with active mode, response kind, and source count.
- Accessible indexed-title suggestions with Arrow Up, Arrow Down, Escape, and `aria-expanded` handling.
- Short site-scoped follow-up continuity, suggested follow-up prompts, and explicit session reset.
- Copy, Markdown, JSON, research-note, print, saved-session, feedback, and typed-handoff actions.
- Cold-start and recovery progress with verified WordPress fallback messaging.
- WordPress-to-FastAPI `research_mode`, `workspace`, `follow_up_prompts`, and `session_turns` normalization.
- `POST /v1/session/reset` backend endpoint.
- Existing calibrated hybrid retrieval, evidence gates, citation verification, durable indexing, and recovery behavior preserved.

## WordPress and release-contract validation

- **11/11 PHP release suites passed.**
- **373 named PHP contract checks passed; 0 failed.**
- v6.5.0 production-workspace contract: **97/97 checks passed.**
- Snapshot round-trip, recovery retry, alert suppression, endpoint reliability, provider compatibility, hybrid retrieval, and calibration contracts remained green.
- **22 PHP files** passed syntax validation.

## Backend validation

- **44/44 backend tests passed** from the repository root.
- **44/44 backend tests passed** from `backend/`.
- Tests cover explicit and auto-detected research modes, workspace response schema, follow-up prompts, session reset, retrieval calibration, citation verification, transactional indexing, recovery, and rollback.
- Python source and tests passed `compileall` validation.
- Local artifact validation ran under Python 3.13.5; the included release script explicitly requires and verifies Python 3.12 before installation or testing, matching Render's Python 3.12.12 runtime.

## Asset and package validation

- **2 JavaScript files** passed `node --check`.
- **53 JSON files** parsed successfully.
- `PUSH_RESEARCH_LIBRARIAN_V650_PY312.sh` passed Bash syntax validation.
- Push-safe secret-pattern scan passed.
- The exact ZIP was extracted into a clean directory and the complete validation set was rerun successfully.
- The final ZIP is accompanied by a SHA-256 checksum.

## Compatibility

- Upgrades in place from v6.4.1.
- SQLite remains at additive schema version 6; no workspace-specific data migration is required.
- Existing records, chunks, embeddings, calibration profiles, benchmark history, snapshots, ledgers, and editorial queues are retained.
- Semantic retrieval remains optional.
- No paid vector database or persistent Render disk is required.
- The separate Research Library page's Browse by Topic accordion and Featured Knowledge Pathways layout are outside this plugin release.
