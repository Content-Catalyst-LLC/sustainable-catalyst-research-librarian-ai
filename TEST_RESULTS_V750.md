# Research Librarian AI v7.5.0 — Test Results

Release: **v7.5.0 — Collaborative Research Room Intelligence**

## Certification summary

- Backend regression suite: **121 passed / 121 total**
- Backend suite repeated from `backend/`: **121 passed / 121 total**
- WordPress contract + functional test files: **36 passed / 36 total**
- Dedicated v7.5.0 collaborative-room contract: **104 passed / 104 checks**
- PHP syntax validation: **50 files passed**
- JavaScript syntax validation: **4 files passed**
- JSON parse validation: **98 files passed**
- Python bytecode compilation: **passed**
- v7.5.0 push-script shell syntax: **passed**
- Secret-pattern scan: **0 hits**

## New v7.5.0 coverage

The release tests verify:

- durable Research Room objects with explicit Owner, Editor, Researcher, and Viewer membership roles;
- active-room membership authorization for reads, writes, room-context selection, and management actions;
- viewer read-only behavior and owner/editor membership-management boundaries;
- server-side WordPress actor resolution so browser payloads cannot impersonate contributors, creators, or disagreement participants;
- shared evidence state with contributor attribution while preserving the Library object's original owner, source scope, object type, and provenance;
- cross-member room-context retrieval of intentionally shared Library objects;
- collaborative open questions with creator attribution and creator/leadership disposition controls;
- disagreement positions merged by participant rather than overwritten, with participants restricted to their own position;
- owner/editor-only disagreement resolution;
- attributable participant activity for room creation, membership, evidence, questions, disagreement activity, synthesis, and Librarian searches;
- bounded room synthesis and room prompt context explicitly separated from verified evidence and model instructions;
- room-scoped Librarian ask provenance marked with participant attribution and `not_evidence` governance;
- project backup/import of room membership, shared evidence, questions, disagreements, activity, and room-only shared Library objects;
- preservation of the v7.4 personal research-state ledger, v7.3 evidence-quality/no-truth-score contracts, v7.2 Library context behavior, and v7.1.2 Neon/Postgres durability.

## Storage and migration

The ancillary SQLite workspace store advances from **schema 14 to schema 15** with additive tables:

- `research_rooms`
- `research_room_members`
- `research_room_evidence_states`
- `research_room_questions`
- `research_room_disagreements`
- `research_room_activity`

The production Neon/Postgres knowledge-index schema remains **`sc-research-librarian-knowledge-index/13.0`**. **No Neon/Postgres knowledge-index migration is required for v7.5.0.**

## Release contracts

- Plugin/backend version: `7.5.0`
- Connected Research API: `sc-connected-research-api/1.4`
- Public workspace: `sc-research-librarian-public-workspace/2.4`
- Research Room: `sc-research-room/1.0`
- Research Room member: `sc-research-room-member/1.0`
- Shared evidence state: `sc-research-room-evidence-state/1.0`
- Collaborative question: `sc-research-room-question/1.0`
- Disagreement: `sc-research-room-disagreement/1.0`
- Participant activity: `sc-research-room-activity/1.0`
- Room synthesis: `sc-research-room-synthesis/1.0`
- Room prompt: `sc-research-room-prompt/1.0`

## Governance boundary

Room collaboration is workflow context, not verified evidence. Sharing a source does not make it editorial, jointly authored, true, or endorsed. Questions are not facts; disagreements are not verdicts; room synthesis is not factual verification. Generated answers remain governed by verified retrieval, citations, provenance, and human publication review.
