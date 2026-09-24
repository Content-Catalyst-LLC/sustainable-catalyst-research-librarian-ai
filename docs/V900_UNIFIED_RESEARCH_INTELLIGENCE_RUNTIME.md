# Research Librarian AI v9.0.0 — Unified Research Intelligence Runtime

v9.0.0 is the milestone release that composes the v8.2–v8.12 research subsystems into a single governed research-run contract.

## Runtime stages

1. discovery
2. ingestion
3. document intelligence
4. canonical source identity and citation graph
5. retrieval
6. evidence governance
7. finding/claim research intelligence
8. argument/contradiction synthesis
9. statistical analysis planning and specialist-runtime handoff
10. visual research intelligence
11. Platform Core project-state synchronization
12. reproducibility packaging/readiness

Every stage declares its authority owner, dependencies, execution mode, gate, endpoint, and expected output. The runtime emits a deterministic run id, plan hash, stage result hashes, and a final run fingerprint.

## Safe execution boundary

`POST /v1/core/unified-research/execute` executes only non-promoting planning/extraction functions. It may build a retrieval query plan, candidate findings/claims, argument plan, statistical plan, visual plan, or dry project-state synchronization plan when the corresponding payload is supplied.

It does **not** perform automatic Platform Core writes. Existing explicit promotion/synchronization endpoints remain authoritative and retain their human-review requirements.

## Durable execution

The async job runtime adds `unified-research-runtime`. Durable Postgres-backed jobs can execute the same safe orchestration path and persist the resulting run manifest with retry/idempotency semantics inherited from the v8.3 async runtime.

## Governance

- Research Librarian owns source acquisition, parsing, source intelligence, retrieval, orchestration, and candidate/planning logic.
- Platform Core owns promoted evidence, findings, claims, arguments, statistical reasoning, visual reasoning, project state, provenance, lineage, and reproducibility.
- Analytics R, Workspace, Lab, Workbench, or an explicitly declared validated external runtime retain specialist computation authority.
- The unified runtime does not determine truth, accept claims, resolve contradictions, infer causality, rank arguments, interpret statistical significance, or infer visual meaning automatically.
