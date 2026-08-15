# Research Librarian AI v7.4.0 — Persistent Research State, Reading History & Open Questions

## Purpose

v7.4.0 gives the Library-native research context model durable, inspectable research continuity. It records what a researcher searched, what source objects are unread, in progress, reviewed, or rejected, which objects have an unresolved contradiction flag, and which research questions remain open, deferred, or resolved.

This is **workflow memory, not chat memory and not evidence**. Research state is stored as explicit user/project records that can be inspected, changed, exported, and restored. The model is not allowed to silently transform prior searches, rejected material, or open questions into factual assumptions.

## Research-state ledger

The release separates three durable record classes:

1. **Research activity** — searches and explicit workflow actions such as save, open, read, review, reject, restore, contradiction flag/resolution, question state changes, and notes.
2. **Object reading/review state** — per-Library-object state for `unread`, `reading`, `reviewed`, or `rejected`, plus `none`, `flagged`, or `resolved` contradiction state.
3. **Open-question register** — explicit questions with `open`, `resolved`, `deferred`, or `dismissed` status, optional linked Library object IDs, and an optional resolution.

Schemas:

- `sc-research-activity-event/1.0`
- `sc-research-object-state/1.0`
- `sc-research-open-question/1.0`
- `sc-research-state-summary/1.0`
- `sc-research-state-prompt/1.0`

## Librarian integration

When an authenticated saved context is active, a successful or failed Librarian research request can leave an inspectable `search` activity event with the query and bounded diagnostic metadata. The active context can then expose recent searches, the review queue, rejected objects, contradiction flags, and unresolved questions.

A bounded `sc-research-state-prompt/1.0` view may accompany an authenticated Librarian request. Its boundary is explicit:

- prior searches are not evidence and cannot be cited as factual support;
- open questions are questions, not facts or assumptions;
- resolved questions are not silently reopened;
- rejected objects remain in provenance but are not preferred during context-priority retrieval unless the researcher explicitly revisits them; and
- contradiction flags indicate review work, not an automatic conclusion that a source is false.

The verified retrieval and citation pipeline remains authoritative for generated answers.

## Connected Research Workspace

The authenticated workspace adds **Research state** alongside **Evaluate context**. For a saved Library/project/Research Room context, the researcher can:

- inspect research activity counts and recent searches;
- see unread/reading items waiting for review, including context objects with no explicit ledger row yet as a derived (non-persisted) unread state;
- mark evaluated source objects **Reading**, **Reviewed**, or **Rejected**;
- flag or resolve a contradiction state;
- add open research questions; and
- resolve or defer open questions.

The source-evaluation cards from v7.3.0 are reused as the object-action surface, so research quality signals and workflow state remain connected without being conflated.

## Privacy and ownership

WordPress remains the authenticated ownership boundary. State bridge routes force the current WordPress `owner_ref` and verify access to supplied context, project, Library object, and existing question IDs before forwarding writes to FastAPI.

A user may attach private workflow state to an official Sustainable Catalyst editorial object they can read, but this does not grant permission to edit the editorial object or change its source scope. Personal, project, Research Room, and editorial provenance remain distinct.

## API additions

FastAPI:

- `GET /v1/research/state/summary`
- `GET /v1/research/activity`
- `POST /v1/research/activity`
- `GET /v1/research/object-states`
- `POST /v1/research/object-states`
- `GET /v1/research/questions`
- `POST /v1/research/questions`

WordPress exposes owner-authorized bridge routes under `/wp-json/sc-research-librarian-ai/v1/platform/v7/state...`.

The connected API advances to `sc-connected-research-api/1.3`; the public workspace contract advances to `sc-research-librarian-public-workspace/2.3`.

## Persistence and migration

v7.4.0 advances the **ancillary SQLite workspace store** from schema 13 to schema 14 with three additive tables:

- `research_activity_events`
- `research_object_states`
- `research_open_questions`

There is **no Neon/Postgres knowledge-index migration** in this release. The production knowledge index remains `sc-research-librarian-knowledge-index/13.0`. When Neon/Postgres owns the durable knowledge index, existing store delegation continues to use the ancillary SQLite workspace store for research-state records.

Project backup/export now includes research activity, object state, and open questions. Import restores those records within the project owner/project boundary.

## Compatibility

- v7.3.0 source evaluation, evidence comparison, structural gap detection, and no-truth-score governance are preserved.
- v7.2.0 Library objects and saved research contexts are preserved.
- v7.1.2 Neon/Postgres fail-closed indexing and timeout-safe activation are preserved.
- Public Librarian questions without a saved authenticated context remain unchanged.
- Rejected objects are never deleted by the research-state system.
- Research state never overrides verified evidence, citation verification, source governance, or human publication review.
