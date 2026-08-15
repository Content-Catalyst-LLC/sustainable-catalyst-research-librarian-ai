# Sustainable Catalyst Research Librarian AI v7.5.0

A site-scoped connected research intelligence platform with Library-native research objects, bounded research contexts, persistent individual research state, collaborative Research Rooms, descriptive evidence-quality signals, Neon/Postgres durable indexing, verified retrieval, Gemini semantic search, transaction recovery, and a visible public research workspace. See `docs/V750_COLLABORATIVE_RESEARCH_ROOM_INTELLIGENCE.md`.

## v7.5.0 highlights

- Turns Research Rooms into durable collaboration objects with explicit membership and **Owner / Editor / Researcher / Viewer** roles.
- Adds room-scoped shared evidence state while preserving every Library object's original owner, scope, and provenance.
- Adds collaborative questions, participant-attributed disagreement positions, and a durable participant activity ledger.
- Adds bounded room synthesis for authenticated Librarian context without treating room metadata as verified evidence or model instructions.
- Allows active room members to retrieve sources intentionally shared by other members while keeping personal v7.4 reading/review/rejection state separate.
- Adds an authenticated **Research rooms** workspace for room creation, membership, evidence sharing, questions, disagreements, activity, synthesis, and room-to-Librarian-context promotion.
- Includes project-linked room state in portable backup/import.
- Advances the ancillary SQLite workspace store to schema 15, Connected Research API to 1.4, and public workspace to 2.4 without changing the Neon/Postgres knowledge-index schema.

## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI uses Neon/Postgres for production knowledge generations, source records, retrieval chunks, and pgvector embeddings. SQLite remains the local-development and ancillary governance/workspace/Library-context/research-state/collaboration store in v7.5.0. Generation is isolated behind `sc-generation-adapter/1.0`; deterministic retrieval and project continuity remain usable when generation is unavailable.

## Public shortcodes

- `[sustainable_catalyst_research_librarian_ai]`
- `[sc_research_librarian]`
- `[sc_connected_research_workspace]`
- `[sc_research_projects_summary]`
- `[sc_connected_research_platform_status]`
- `[sc_research_librarian_methodology]`
- `[sc_research_librarian_governance_status]`
- `[sc_research_librarian_platform_handoffs]`

## Backend resources

`/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/library/object-model`, `/v1/library/objects`, `/v1/research/contexts`, `/v1/research/contexts/{context_id}/evidence-quality`, `/v1/research/sources/evaluate`, `/v1/research/evidence/compare`, `/v1/research/evidence/gaps`, `/v1/research/state/summary`, `/v1/research/activity`, `/v1/research/object-states`, `/v1/research/questions`, `/v1/research/rooms`, `/v1/research/rooms/{room_id}`, `/v1/research/rooms/{room_id}/members`, `/v1/research/rooms/{room_id}/evidence`, `/v1/research/rooms/{room_id}/questions`, `/v1/research/rooms/{room_id}/disagreements`, `/v1/research/rooms/{room_id}/activity`, `/v1/research/rooms/{room_id}/synthesis`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- Neon-compatible PostgreSQL with pgvector for the production knowledge index
- SQLite schema 15 for local development and ancillary platform/Library/research-state/collaboration records
- Knowledge-index schema remains `sc-research-librarian-knowledge-index/13.0`
- WordPress 6.0+
- No Render persistent disk is required for the durable production knowledge index

See `docs/V750_COLLABORATIVE_RESEARCH_ROOM_INTELLIGENCE.md`, `docs/V740_PERSISTENT_RESEARCH_STATE_READING_HISTORY_OPEN_QUESTIONS.md`, `docs/V730_SOURCE_EVALUATION_EVIDENCE_COMPARISON_RESEARCH_QUALITY_SIGNALS.md`, and `docs/INSTALL.md`.
