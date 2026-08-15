# Research Librarian AI v7.4.0 — Test Results

Release: **v7.4.0 — Persistent Research State, Reading History & Open Questions**

## Certification summary

- Backend regression suite: **115 passed / 115 total**
- Backend suite repeated from `backend/`: **115 passed / 115 total**
- WordPress contract + functional test files: **35 passed / 35 total**
- Dedicated v7.4.0 persistent-research-state contract: **79 passed / 79 checks**
- PHP syntax validation: **49 files passed**
- JavaScript syntax validation: **3 files passed**
- JSON parse validation: **97 files passed**
- Python bytecode compilation: **passed**
- v7.4.0 push-script shell syntax: **passed**
- Secret-pattern scan: **0 hits**

## New v7.4.0 coverage

The release tests verify:

- durable research activity for saved-context searches and explicit workflow actions;
- per-object `unread`, `reading`, `reviewed`, and `rejected` state;
- derived unread visibility for context objects that do not yet have an explicit ledger row;
- contradiction flags and explicit resolution state;
- open-question creation, resolution, deferral, and owner scoping;
- explicit governance that research state is workflow memory rather than factual evidence;
- bounded research-state prompt context that does not make prior searches or open questions citable support;
- rejected objects retained in provenance but removed from context-priority retrieval unless revisited;
- automatic search-history events for saved authenticated contexts;
- owner-authorized WordPress state routes and existing-question ownership verification;
- source-level Reading / Reviewed / Reject / Flag contradiction controls in the authenticated workspace;
- project backup/import of research activity, object state, and open questions;
- preservation of v7.3 source-quality/no-truth-score contracts, v7.2 Library-context behavior, and v7.1.2 Neon/Postgres durability.

## Storage and migration

The ancillary SQLite workspace store advances to **schema 14** with additive `research_activity_events`, `research_object_states`, and `research_open_questions` tables. The production Neon/Postgres knowledge-index schema remains **`sc-research-librarian-knowledge-index/13.0`**. No Neon/Postgres knowledge-index migration is required for v7.4.0.

## Release contracts

- Plugin/backend version: `7.4.0`
- Connected Research API: `sc-connected-research-api/1.3`
- Public workspace: `sc-research-librarian-public-workspace/2.3`
- Research activity: `sc-research-activity-event/1.0`
- Research object state: `sc-research-object-state/1.0`
- Open question: `sc-research-open-question/1.0`
- Research-state summary: `sc-research-state-summary/1.0`
- Research-state prompt: `sc-research-state-prompt/1.0`
