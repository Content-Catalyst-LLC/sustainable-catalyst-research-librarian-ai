# Research Librarian v12.1.0 — Neural Research Intelligence Foundation

v12.1.0 opens the Research Librarian neural-intelligence line after the v12.0.x WordPress-independence program.

## Architectural role

Research Librarian does **not** become the neural execution runtime.

The authority split remains:

- **Platform Core** — governed neural model, dataset, representation, inference, provenance, and cross-platform object contracts.
- **Research Librarian** — research context, literature/evidence linkage, neural research registries, provenance assembly, review, snapshots, and runtime handoff preparation.
- **Workspace / Research Lab / Workbench** — specialist computation, training, fine-tuning, inference, evaluation, explainability, representation analysis, and other execution.
- **WordPress** — optional compatibility/presentation only; no neural authority and no neural execution.

## New durable research objects

v12.1.0 introduces:

- neural research projects;
- model references;
- dataset references;
- representation / embedding references;
- inference receipts;
- execution handoff packets;
- provenance lineage views;
- Platform Core candidate packets;
- immutable research snapshots.

The Librarian stores references, hashes, parameters, metrics, execution receipts, and provenance metadata. It does not store model weights in this foundation and does not store runtime secrets.

## Runtime handoffs

The Librarian can prepare explicit handoff packets for:

- Workspace;
- Research Lab;
- Workbench;
- external specialist runtimes.

Supported operation classes include training, fine-tuning, inference, embedding generation, evaluation, explainability, representation analysis, and benchmarking.

A handoff packet is a request/plan only. `execution_performed=false` until a specialist runtime supplies an external receipt.

## Governance

v12.1.0 does not:

- automatically train or fine-tune models;
- automatically run inference;
- automatically select a model;
- automatically rank models;
- infer scientific validity;
- treat metrics as truth;
- write governed Platform Core objects automatically;
- store model weights;
- store credentials or runtime secrets.

## Persistence

Migration `041_neural_research_intelligence_foundation.sql` creates:

- `sc_rl_neural_research_projects`
- `sc_rl_neural_research_events`
- `sc_rl_neural_research_snapshots`

Production remains PostgreSQL. SQLite is retained for local/test fallback.

## Backend API

Prefix:

`/v1/research-librarian/neural-research`

Key routes include:

- `GET /manifest`
- `GET /capabilities`
- `GET|POST /projects`
- `GET /projects/{id}`
- `POST /projects/{id}/models`
- `POST /projects/{id}/datasets`
- `POST /projects/{id}/representations`
- `POST /projects/{id}/inference-receipts`
- `POST /projects/{id}/handoffs`
- `GET /projects/{id}/lineage`
- `GET /projects/{id}/readiness`
- `GET /projects/{id}/core-candidate`
- `POST /projects/{id}/state`
- `POST /snapshots/freeze`

All stateful neural routes require normal Independent API authentication.

## WordPress

The WordPress v12.1.0 layer is passive and exposes:

`GET /wp-json/sc-research-librarian-ai/v1/neural-research-foundation`

It reports the architecture boundary only. It does not proxy neural state, hold neural credentials, or perform execution.

## Next boundary

v12.2.0 — Multilingual & Cross-Language Research Intelligence.
