# Sustainable Catalyst Research Librarian AI v7.4.0

A site-scoped connected research intelligence platform with Library-native research objects, bounded research contexts, descriptive evidence-quality signals, persistent research state, Neon/Postgres durable indexing, verified retrieval, Gemini semantic search, transaction recovery, and a visible public research workspace. See `docs/V740_PERSISTENT_RESEARCH_STATE_READING_HISTORY_OPEN_QUESTIONS.md`.

## v7.4.0 highlights

- Adds a durable research activity ledger for searches and explicit workflow actions.
- Adds per-object **Unread / Reading / Reviewed / Rejected** state and contradiction flags.
- Adds an explicit open-question register with resolution and deferral states.
- Adds an authenticated **Research state** workspace action for saved Library/project/Research Room contexts.
- Records saved-context Librarian searches as inspectable workflow history.
- Carries only a bounded state summary into Librarian questions; research state is never factual evidence.
- Keeps rejected objects in provenance while removing them from context-priority retrieval unless revisited.
- Includes research activity, object state, and open questions in project backup/import.
- Advances the ancillary SQLite workspace store to schema 14 without changing the Neon/Postgres knowledge-index schema.

## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI uses Neon/Postgres for production knowledge generations, source records, retrieval chunks, and pgvector embeddings. SQLite remains the local-development and ancillary governance/workspace/Library-context/research-state store in v7.4.0. Generation is isolated behind `sc-generation-adapter/1.0`; deterministic retrieval and project continuity remain usable when generation is unavailable.

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

`/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/library/object-model`, `/v1/library/objects`, `/v1/research/contexts`, `/v1/research/contexts/{context_id}/evidence-quality`, `/v1/research/sources/evaluate`, `/v1/research/evidence/compare`, `/v1/research/evidence/gaps`, `/v1/research/state/summary`, `/v1/research/activity`, `/v1/research/object-states`, `/v1/research/questions`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- Neon-compatible PostgreSQL with pgvector for the production knowledge index
- SQLite schema 14 for local development and ancillary platform/Library/research-state records
- Knowledge-index schema remains `sc-research-librarian-knowledge-index/13.0`
- WordPress 6.0+
- No Render persistent disk is required for the durable production knowledge index

See `docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md`, `docs/V730_SOURCE_EVALUATION_EVIDENCE_COMPARISON_RESEARCH_QUALITY_SIGNALS.md`, and `docs/INSTALL.md`.
