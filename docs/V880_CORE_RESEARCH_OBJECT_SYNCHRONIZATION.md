# Research Librarian AI v8.8.0 — Core Research Object Synchronization

v8.8.0 turns the v8.2 Platform Core client and v8.7 evidence bridge into project-level synchronization. Research Librarian remains authoritative for acquisition, parsing, source identity, retrieval, local project organization, Research Rooms, and research-context UX. Platform Core remains authoritative for governed cross-product research state, immutable versions, lineage, evidence, claims, reasoning, and reproducibility.

## Synchronization model

A Librarian project first resolves to a governed Platform Core unified research-project identity. The Librarian then assembles a deterministic synchronization plan from declared local state and writes it to Core's `sc.research.project-state-versioning-reproducibility.v1` contract.

Each changed synchronization creates a new Core project-state version. The version contains bindings for the local project identity and, when requested, research contexts, Research Rooms, Library sources, project entities, open questions, and research lifecycles. Dependency edges explicitly declare how those objects are scoped to the project. The version is frozen and optionally snapshotted after the bindings are written. Repeating an unchanged synchronization is idempotent and does not create a duplicate version.

## Governance boundary

Synchronization is descriptive. Research Room state is not evidence, open questions are not facts, lifecycle state is not approval, and source inclusion is not an evidentiary judgment. v8.8.0 does not determine truth, create claims, infer stance, advance workflows, publish research, execute models, or certify reproducibility.

## API

- `GET /v1/core/research-sync/capabilities`
- `POST /v1/core/research-sync/plan`
- `POST /v1/core/research-sync/synchronize`

The planning endpoint is deterministic and performs no Core writes. The synchronization endpoint requires the private Librarian backend key and Core write credentials.
