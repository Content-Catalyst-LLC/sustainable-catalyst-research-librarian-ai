# Research Librarian AI v10.9.0 — Computational Research Planning

v10.9.0 converts human-reviewed dataset fitness into reproducible computational research plans without turning the Research Librarian into an execution engine.

## Core capabilities

- Durable computational research plans bound to v10.8 dataset-fitness projects.
- Explicit runtime targets for Workspace, Research Lab, Workbench, Python, R, Julia, Fortran, Rust, C/C++, Haskell, SQL, or other specialist runtimes.
- Human-authored analysis steps with dataset/variable bindings, method family, parameters, preprocessing, dependencies, expected outputs, validation checks, limitations, and reproducibility notes.
- Human step decisions (`approved-for-execution`, `revise`, `rejected`) separate from truth/scientific-validity judgments.
- Deterministic dependency graph and cycle detection.
- Reproducibility-requirement and computational-constraint registries.
- Non-writing execution handoff packets and Platform Core candidates.
- Immutable snapshots and durable async snapshot jobs.
- Unified v10 environment binding as `computational-research-plan`.

## Governance

A computational plan is a reviewable execution specification, not an executed analysis. The Librarian does not automatically choose a method, choose a runtime, execute code, certify outputs, interpret results, or promote findings as truth. Specialist runtimes own execution; Platform Core remains the governed research-object authority.
