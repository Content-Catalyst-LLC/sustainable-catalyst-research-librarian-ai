# Research Librarian v12.0.3 — Persistent Research Session & Conversation Runtime

v12.0.3 replaces ephemeral research-conversation continuity with a durable Python/PostgreSQL session runtime.

## Durable session model

A research session can persist:
- title and opaque client reference;
- project binding;
- Integrated Computational Research Scientist Environment binding;
- saved research-context reference;
- ordered user, assistant, system, tool, and research-note turns;
- source, evidence, artifact, answer-trace, model/provider, and provenance references;
- state transitions;
- context-binding history;
- immutable frozen conversation snapshots.

Each turn includes a record hash and previous-turn hash so conversation order and lineage can be inspected.

## Independent API

New API v1 routes under `/v1/research-librarian/sessions` support session create/list/read, turn create/read, context binding, state changes, reset, summary, and frozen snapshots.

## Legacy compatibility

The existing `/v1/ask` compatibility endpoint now reads and writes the same persistent session store instead of the process-local `_sessions` dictionary. Backend restarts therefore no longer erase conversation history.

The existing `/v1/session/reset` route clears persisted turns while retaining the session record and reset lineage.

## Identity boundary

`client_ref` is an opaque continuity hint only. It is not an authenticated identity and grants no access. v12.0.3 continues to use the backend-key trust boundary introduced for Independent API v1. End-user identity, session authentication, and access control remain planned for v12.0.5.

## WordPress

WordPress stores no canonical conversation turns. It remains an optional interface adapter. Removing WordPress does not remove backend research sessions.

## Persistence

Migration 038 adds PostgreSQL session, turn, and snapshot tables. SQLite provides the same contract for local/test operation.

The next decoupling release is v12.0.4 — Independent Web App Foundation.
