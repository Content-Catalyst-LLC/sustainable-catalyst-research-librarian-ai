# Sustainable Catalyst Research Librarian AI v7.3.0

A site-scoped connected research intelligence platform with Library-native research objects, bounded research contexts, descriptive source evaluation, evidence comparison, structural gap detection, Neon/Postgres durable indexing, verified retrieval, Gemini semantic search, transaction recovery, and a visible public research workspace. See `docs/V730_SOURCE_EVALUATION_EVIDENCE_COMPARISON_RESEARCH_QUALITY_SIGNALS.md`.

## v7.3.0 highlights

- Adds descriptive source profiles for source type, evidence role, publisher/institution, date, methods, citations, access, provenance, and limitations.
- Adds side-by-side evidence comparison and provider/source-mix summaries.
- Adds deterministic structural evidence-gap detection.
- Adds an authenticated **Evaluate context** workspace action for saved Library/project/Research Room contexts.
- Carries bounded source-quality metadata with authorized context objects without turning it into verified evidence.
- Explicitly forbids truth scores, credibility scores, automatic winners, and automatic source rejection.
- Persists optional comparison/gap reports through existing project entities, so no database migration is required.

## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI uses Neon/Postgres for production knowledge generations, source records, retrieval chunks, and pgvector embeddings. SQLite remains the local-development and ancillary governance/workspace/Library-context store in v7.3.0. Generation is isolated behind `sc-generation-adapter/1.0`; deterministic retrieval and project continuity remain usable when generation is unavailable.

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

`/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/library/object-model`, `/v1/library/objects`, `/v1/research/contexts`, `/v1/research/contexts/{context_id}/evidence-quality`, `/v1/research/sources/evaluate`, `/v1/research/evidence/compare`, `/v1/research/evidence/gaps`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- Neon-compatible PostgreSQL with pgvector for the production knowledge index
- SQLite schema 13 for local development and ancillary platform/Library-context records
- WordPress 6.0+
- No Render persistent disk is required

See `docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md` and `docs/INSTALL.md`.
