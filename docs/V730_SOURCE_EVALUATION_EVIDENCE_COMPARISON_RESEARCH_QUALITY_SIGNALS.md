# Research Librarian AI v7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals

## Purpose

v7.3.0 turns the v7.2.0 Library-native context model into a research-quality workspace. It evaluates the metadata and structure of sources already present in a user-authorized Library, project, or Research Room context. The release does **not** assign a truth score, credibility score, automatic winner, or automatic source rejection.

## Source evaluation

Each source profile can expose the source type, primary/secondary/tertiary role when supplied, publisher or institution, publication date, methodology availability, citation identifiers/text, access state, preserved provenance, known limitations, and missing metadata. The result is descriptive. A field marked missing means only that the current object does not provide it.

Schemas:

- `sc-source-evaluation/1.0`
- `sc-evidence-comparison/1.0`
- `sc-evidence-gap-report/1.0`
- `sc-research-quality-signals/1.0`

## Evidence comparison

The comparison contract produces side-by-side dimensions for source type, evidence role, publisher/institution, publication date, methodology, access state, and metadata state. Corpus summaries expose provider diversity and the distribution of evidence roles and methodology states. The API deliberately returns `no_automatic_winner=true` and `no_truth_score=true`.

## Evidence-gap detection

The deterministic gap detector can surface structural gaps such as:

- no sources in the selected context;
- no source explicitly identified as primary evidence;
- provider/institution concentration;
- no visible methodology;
- an undated corpus;
- missing citation metadata;
- undocumented limitations; and
- missing contrasting positions for comparison-oriented questions when stance metadata is absent.

These are research prompts, not proof that a corpus is weak or incorrect. The absence of a detected gap is not proof that the corpus is complete.

## Context integration

Resolved v7.2 contexts now carry a bounded `quality_signals` object with each prompt object. These signals are explicitly labeled as descriptive metadata and are never promoted to verified evidence. The existing verified retrieval and citation pipeline remains authoritative for generated answers.

The authenticated Connected Research Workspace adds **Evaluate context**, which calls the server-authorized context-quality endpoint and renders source profiles, source-mix summaries, and structural gaps without exposing another user's objects.

## API additions

- `GET /v1/research/contexts/{context_id}/evidence-quality`
- `POST /v1/research/sources/evaluate`
- `POST /v1/research/evidence/compare`
- `POST /v1/research/evidence/gaps`

WordPress exposes owner-authorized bridge routes under `/wp-json/sc-research-librarian-ai/v1/platform/v7/...`. Non-admin users cannot create Library objects in the official `sustainable-catalyst-collection` source scope through this bridge; that editorial identity is reserved for administrators.

The connected API advances to `sc-connected-research-api/1.2`; the public workspace contract advances to `sc-research-librarian-public-workspace/2.2`.

## Persistence and migration

No Postgres or SQLite schema migration is required. Optional persisted source-evaluation, comparison, and gap reports use the existing `research_project_entities` store and therefore remain part of project backup/export behavior. SQLite remains schema 13 for ancillary connected-workspace data.

## Compatibility

- v7.2.0 Library objects and saved contexts are preserved.
- v7.1.2 Neon/Postgres fail-closed indexing and timeout-safe activation are preserved.
- Unauthenticated/public Research Librarian use remains unchanged unless an authenticated context is explicitly selected.
- Personal recommendations remain distinct from Sustainable Catalyst editorial recommendations.
- Quality metadata cannot override citation verification, source governance, or human publication review.
