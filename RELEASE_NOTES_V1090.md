# Research Librarian AI v10.9.0 — Computational Research Planning

v10.9.0 converts v10.8 human-reviewed dataset fitness into a durable, reproducible computational research plan without moving execution authority into the Research Librarian.

## Added
- Durable computational research plans bound to v10.8 dataset-fitness projects and fingerprints.
- Runtime target registry for Workspace, Research Lab, Workbench, Python, R, Julia, Fortran, Rust, C/C++, Haskell, SQL, and other specialist runtimes.
- Human-authored analysis steps with dataset/variable bindings, method family, parameters, preprocessing, dependencies, expected outputs, validation checks, limitations, and reproducibility notes.
- Human step decisions with explicit `approved-for-execution`, `revise`, and `rejected` states.
- Declared dependency graphs with cycle detection.
- Reproducibility-requirement and computational-constraint registries.
- Non-writing execution handoff packets and Platform Core candidates.
- Immutable snapshots and durable async snapshot jobs.
- Unified v10 environment binding as `computational-research-plan`.
- Postgres migration `024_computational_research_planning.sql`.

## Governance
Planning is not execution. Method and runtime approval remain human-controlled. v10.8 dataset-fitness judgments are inherited rather than silently re-judged. Specialist runtimes retain computation/execution authority, Platform Core remains governed-object authority, and the Librarian performs no automatic method selection, runtime selection, execution, result interpretation, or truth promotion.
