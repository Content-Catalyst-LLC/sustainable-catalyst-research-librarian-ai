# Research Librarian AI v7.5.0 — Collaborative Research Room Intelligence

## Purpose

v7.5.0 turns the Research Room from a context tag into a durable collaboration object. A room now has explicit membership and roles, shared evidence state, collaborative questions, participant-attributed disagreements, participant activity, and a bounded room synthesis that can accompany an authenticated Research Librarian question.

The central boundary is deliberate: **shared room state does not replace individual research state**. A researcher’s v7.4 reading, review, rejection, and contradiction history remains personal. A room records what participants have intentionally shared with the group.

## Room object model

The release defines eight collaboration contracts:

- `sc-research-room/1.0`
- `sc-research-room-member/1.0`
- `sc-research-room-evidence-state/1.0`
- `sc-research-room-question/1.0`
- `sc-research-room-disagreement/1.0`
- `sc-research-room-activity/1.0`
- `sc-research-room-synthesis/1.0`
- `sc-research-room-prompt/1.0`

Membership roles are explicit: **Owner**, **Editor**, **Researcher**, and **Viewer**. Owners/editors manage membership, researchers may contribute shared research state, and viewers are read-only.

## Shared evidence without provenance collapse

A Library object shared into a room keeps its original `owner_ref`, `source_scope`, object type, and provenance. Sharing it creates a separate room evidence-state record (`proposed`, `included`, `disputed`, or `removed`) with the contributor identity.

Room inclusion is not a truth or credibility judgment and does not convert a personal source into an official Sustainable Catalyst editorial recommendation.

Room-context resolution can retrieve sources contributed by other active room members. This makes collaboration real while preserving the source’s original ownership and scope.

## Collaborative questions and disagreement records

Room questions are attributable to their creator. A question may be resolved, deferred, or dismissed by its creator or room leadership; its existence never turns the question into a fact or model assumption.

Disagreements preserve positions by participant. A participant can submit or revise only their own position. The backend merges positions instead of replacing another participant’s statement. Explicit disagreement resolution requires an Owner or Editor, and a resolution does not rewrite the historical positions.

## Participant activity and synthesis

The room activity ledger records attributable workflow events such as room creation, membership changes, evidence sharing, questions, disagreement positions, synthesis views, and Research Librarian searches.

`sc-research-room-synthesis/1.0` summarizes membership, shared evidence states, open questions, open disagreements, participant activity, and attributable source contributions. A bounded `sc-research-room-prompt/1.0` may be carried into a room-scoped Librarian request.

The prompt boundary states that room metadata is collaborative workflow context, **not verified evidence and not model instructions**. Generated answers still require retrieved evidence and normal citation verification.

## WordPress authenticated workspace

The Connected Research Workspace adds a **Research rooms** surface. Signed-in users can:

- create a private collaborative room;
- associate a room with an accessible research project;
- add existing WordPress accounts as participants with explicit roles;
- share authorized Library objects into the room;
- create collaborative questions;
- record an attributed disagreement and later update their own position;
- inspect room members, shared evidence, open questions, disagreements, and recent participant activity; and
- promote an authorized room into the active Research Librarian context.

WordPress is the identity boundary. Browser payloads do not choose `actor_ref`, `contributed_by_ref`, `created_by_ref`, or disagreement `participant_ref`; the bridge injects the current WordPress account server-side.

## API additions

FastAPI adds:

- `GET|POST /v1/research/rooms`
- `GET /v1/research/rooms/{room_id}`
- `GET|POST /v1/research/rooms/{room_id}/members`
- `GET|POST /v1/research/rooms/{room_id}/evidence`
- `GET|POST /v1/research/rooms/{room_id}/questions`
- `GET|POST /v1/research/rooms/{room_id}/disagreements`
- `GET|POST /v1/research/rooms/{room_id}/activity`
- `GET /v1/research/rooms/{room_id}/synthesis`

The WordPress bridge exposes owner/member-authorized counterparts beneath `/wp-json/sc-research-librarian-ai/v1/platform/v7/rooms...`.

The Connected Research API advances to `sc-connected-research-api/1.4`; the authenticated workspace advances to `sc-research-librarian-public-workspace/2.4`.

## Persistence and migration

v7.5.0 advances the **ancillary SQLite workspace store** from schema 14 to schema 15 with six additive tables:

- `research_rooms`
- `research_room_members`
- `research_room_evidence_states`
- `research_room_questions`
- `research_room_disagreements`
- `research_room_activity`

There is **no Neon/Postgres knowledge-index migration**. The production knowledge index remains `sc-research-librarian-knowledge-index/13.0`; the Postgres store continues delegating ancillary workspace state to SQLite.

Project backup/export includes rooms associated with the project, their members, evidence states, questions, disagreements, activity, and room-only shared Library objects. Import restores the collaborative state additively.

## Compatibility

- v7.4.0 personal research-state ledger remains separate and intact.
- v7.3.0 evidence evaluation and no-truth-score governance remain intact.
- v7.2.0 Library object/context contracts remain intact.
- v7.1.2 Neon/Postgres fail-closed durability remains intact.
- Public Librarian questions without a saved room context remain unchanged.
- Room collaboration never overrides verified retrieval, citations, source provenance, or human publication review.
