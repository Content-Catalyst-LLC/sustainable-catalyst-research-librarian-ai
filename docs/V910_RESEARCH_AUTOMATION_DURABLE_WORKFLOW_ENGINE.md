# Research Librarian AI v9.1.0 — Research Automation & Durable Workflow Engine

v9.1.0 turns the v9.0 Unified Research Intelligence Runtime into a persistent, resumable research workflow system.

## Added
- Postgres workflow persistence with SQLite local/test fallback.
- Dependency-aware stage reconciliation and scheduling.
- Idempotent bindings from workflow stages to durable v9.0 unified-runtime jobs.
- Explicit human approvals for gated stages.
- Pause, resume, cancel, and retry-failed controls.
- Append-only audit events and immutable workflow checkpoints.
- Durable `research-workflow-advance` automation job.

## Governance boundary
The workflow engine schedules safe local planning/extraction work and records workflow state. It does not automatically promote evidence, accept findings or claims, resolve contradictions, interpret statistical significance, infer visual truth, or perform automatic Platform Core writes. Existing explicit human-gated promotion APIs remain authoritative.
