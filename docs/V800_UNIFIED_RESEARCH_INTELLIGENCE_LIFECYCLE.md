# Research Librarian AI v8.0.0 — Unified Research Intelligence & Research Lifecycle Orchestration

v8.0.0 turns the capabilities built across v7.2–v7.7 into one inspectable research lifecycle. It does not replace the Library, Research Rooms, research state, federated discovery, evidence quality, or Workspace promotion contracts. It coordinates them.

## Lifecycle

The persistent lifecycle has eight stages: **Frame → Discover → Evaluate → Organize → Collaborate → Synthesize → Promote → Preserve**. Collaboration is available when useful rather than being a mandatory gate.

Each stage exposes deterministic readiness signals, blockers, and recommended next actions. Readiness is workflow guidance only. **The system never advances a lifecycle stage automatically.** A stage transition is stored only after an explicit authenticated human confirmation, together with the actor, prior stage, target stage, reason, and any blockers acknowledged at the time.

## Checkpoints and lineage

Researchers can create immutable, SHA-256-fingerprinted lifecycle checkpoints. A checkpoint records the lifecycle fingerprint and an inspectable summary snapshot at that point in the investigation. Checkpoints are included with lifecycle events in project backup/export.

A checkpoint is not publication, editorial approval, or a truth judgment. Lifecycle metadata is never converted into evidence.

## Existing boundaries remain intact

Federated records discovered through v7.7 still require an explicit **Save to My Library** action before becoming Library objects. Workspace promotion from v7.6 still produces a governed handoff packet and requires an explicit Workspace import. Personal research state and Research Room shared state remain separate and attributable.

## Storage and deployment

v8.0.0 advances the ancillary SQLite workspace schema from 17 to **18** for `research_lifecycles`, `research_lifecycle_events`, and `research_lifecycle_checkpoints`.

The production knowledge index remains `sc-research-librarian-knowledge-index/13.0`, with Postgres schema version 3. **No Neon/Postgres knowledge-index migration is required for v8.0.0.**

The Connected Research API advances to `sc-connected-research-api/2.0`; the public workspace contract advances to `sc-research-librarian-public-workspace/3.0`.

For WordPress compatibility, the existing `/platform/v7/` REST route namespace is intentionally retained while its runtime contract advances to v8.0.0.
