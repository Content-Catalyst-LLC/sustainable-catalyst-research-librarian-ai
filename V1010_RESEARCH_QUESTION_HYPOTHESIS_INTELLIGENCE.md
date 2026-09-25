# Research Librarian AI v10.1.0 — Research Question & Hypothesis Intelligence

v10.1.0 adds a durable research-design layer immediately above the v10.0 unified scholarly/AI environment. It converts an explicit broad research question into a reviewable structured plan containing scope, constructs, variables, subquestions, evidence requirements, assumptions, falsification criteria, and candidate hypotheses.

## What v10.1 adds

- Durable Postgres/SQLite research-question plan registry with deterministic identifiers and record hashes.
- Structured question framing across question type, population, context, geography, time horizon, constructs, and typed variables.
- Deterministic candidate subquestion scaffolding for evidence landscape, measurement/operationalization, and boundary conditions.
- Candidate null/alternative hypothesis scaffolding when the researcher supplies a hypothesis-relevant question type plus driver/outcome variable roles.
- Explicit evidence-requirement, assumption, and falsification-criteria registries.
- Human review states: `draft`, `under-review`, `approved`, and `rejected`.
- Structural readiness that distinguishes “ready for review” from “human-approved candidate handoff.”
- Platform Core candidate packets for research-question and hypothesis objects without automatic Core writes.
- Immutable question/hypothesis snapshots and durable `research-question-hypothesis-snapshot` jobs.
- First-class binding into the v10.0 unified research environment as `research-question-plan`.

## Governance boundary

Research Librarian owns discovery, structuring, context, and research-planning intelligence. Platform Core remains the governed authority for canonical research-question/hypothesis objects and their provenance after explicit promotion. v10.1 does not accept or reject hypotheses, infer causality, determine scientific validity, promote truth, select statistical methods as final decisions, or execute specialist computation.

Generated scaffolds are candidates only. Human scholarly judgment remains required before any governed handoff.

## API surface

- `GET /v1/core/research-question-hypothesis/capabilities`
- `POST /v1/core/research-question-hypothesis/plans`
- `GET /v1/core/research-question-hypothesis/plans/{plan_id}`
- `POST /v1/core/research-question-hypothesis/plans/{plan_id}/subquestions`
- `POST /v1/core/research-question-hypothesis/plans/{plan_id}/hypotheses`
- `POST /v1/core/research-question-hypothesis/plans/{plan_id}/evidence-requirements`
- `POST /v1/core/research-question-hypothesis/plans/{plan_id}/review-state`
- `GET /v1/core/research-question-hypothesis/plans/{plan_id}/readiness`
- `GET /v1/core/research-question-hypothesis/plans/{plan_id}/core-candidates`
- `POST /v1/core/research-question-hypothesis/snapshots/freeze`
