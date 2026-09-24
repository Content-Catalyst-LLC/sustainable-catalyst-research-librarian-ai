# Research Librarian AI v8.11.0 — Statistical & Analytical Research Integration

v8.11.0 connects research context and evidence held by the Research Librarian to Platform Core's `sc.core.statistical-reasoning-object-model.v1` contract and specialist computation runtimes.

## Responsibility boundary

The Librarian plans and routes analyses. It does not execute arbitrary statistical analyses, infer statistical significance or causality, rank models, certify scientific validity, or determine truth. Specialist runtimes compute. Platform Core stores governed statistical reasoning evidence and snapshots.

## Flow

1. Build a deterministic analysis plan from project context, governed evidence references, datasets, methods, assumptions, outputs, and limitations.
2. Human review approves the plan and selects a specialist runtime such as Catalyst Analytics R, Workspace, Research Lab, Workbench, or an external validated runtime.
3. The specialist runtime returns an analytical result plus a validation bundle conforming to `sc.analytics-r.statistical-diagnostics-validation.v1` when using the Core v3.3 ingestion contract.
4. The Librarian orchestrates ingestion into Core statistical reasoning.
5. Coefficients and intervals may be registered as evidence objects. Interpretations are only accepted as explicitly human-authored.
6. Core retains immutable reasoning snapshots and governance boundaries.

## API

- `GET /v1/core/statistical-research/capabilities`
- `GET /v1/core/statistical-research/readiness`
- `POST /v1/core/statistical-research/plan`
- `POST /v1/core/statistical-research/promote-validation`
- `POST /v1/core/statistical-research/coefficients`
- `POST /v1/core/statistical-research/intervals`
- `POST /v1/core/statistical-research/interpretations`

Durable async planning uses job type `statistical-analysis-plan`.
