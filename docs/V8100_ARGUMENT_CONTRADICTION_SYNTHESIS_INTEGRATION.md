# Research Librarian AI v8.10.0 — Argument, Contradiction & Synthesis Integration

v8.10.0 connects the Research Librarian's reviewed findings, claims, and evidence to Platform Core's governed `sc.research.argument-evidentiary-synthesis.v1` contract.

## Responsibilities

Research Librarian Python may assemble a deterministic argument plan from explicitly supplied, already-reviewed research objects; preserve researcher-declared support, contradiction, qualification and dependency relations; inspect Core contradiction candidates; register reviewer-declared tensions; and hand a researcher-authored synthesis to Core.

Platform Core remains authoritative for the governed argument graph, nodes, edges, counterarguments/tensions, evidentiary syntheses, immutable histories and downstream conclusion governance.

## Review boundary

Plans default to `pending`. Core promotion requires `review_decision=approved` and an explicit `reviewer_ref`. The Librarian does not infer relations, rank arguments, choose a best interpretation, resolve tensions, generate synthesis prose, create conclusions, or determine truth.

## API

- `GET /v1/core/argument-synthesis/capabilities`
- `POST /v1/core/argument-synthesis/plan`
- `GET /v1/core/argument-synthesis/contradictions/{core_project_id}`
- `POST /v1/core/argument-synthesis/promote`

## Durable jobs

`argument-synthesis-plan` runs the plan-construction phase through the existing Postgres-backed durable queue. Promotion remains an explicit reviewed write operation and is not performed automatically by the worker.
