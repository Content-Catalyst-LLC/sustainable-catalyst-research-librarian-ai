# Research Librarian AI v8.2.0 — Python Service Architecture & Platform Core Client

## Purpose

v8.2.0 makes the Research Librarian Python backend the authoritative acquisition/retrieval/document-intelligence runtime and Platform Core v3.3.0+ the authoritative governed research/reasoning runtime.

## Ownership boundary

### Research Librarian Python owns

- source ingestion and connectors
- normalization and parsing
- chunking and embeddings
- indexing and hybrid retrieval
- federated discovery
- document intelligence
- research workflow orchestration
- Platform Core client orchestration

### Platform Core owns

- governed research objects
- source/evidence provenance and lineage
- claims, findings, arguments, and conclusions
- cross-study synthesis
- reproducibility packages
- statistical reasoning objects
- visual reasoning objects
- cross-product exchange

Platform Core does not become an arbitrary research-code execution service and v8.2.0 does not enable automatic truth promotion.

## New private API

All routes require `X-SC-RL-Key`.

- `GET /v1/core/architecture`
- `GET /v1/core/readiness`
- `GET /v1/core/bindings`
- `GET /v1/core/bindings/{local_kind}/{local_id}`
- `POST /v1/core/research-objects/promote`
- `POST /v1/core/research-projects/synchronize`
- `GET /v1/core/research-projects/{core_project_id}/bundle`
- `POST /v1/core/exchange/packages`

## Core connectivity

The VPS default is `http://sc-core:8090`, resolved over the shared `sc-internal` Docker network. Core writes use `X-SC-API-Key`; the Research Librarian never exposes that credential to WordPress or public clients.

Required production variables:

```text
SC_RL_CORE_ENABLED=true
SC_RL_CORE_BASE_URL=http://sc-core:8090
SC_RL_CORE_WRITE_API_KEY=<same secret as SC_CORE_WRITE_API_KEY>
SC_RL_CORE_MINIMUM_VERSION=3.3.0
SC_RL_CORE_SUPPORTED_MAJOR=3
```

## Reliability model

Each Librarian-to-Core write records a durable binding containing local identity, Core identity, contract version, payload hash, idempotency key, sync state, timestamps, and the latest error/result. Deterministic Core IDs plus conflict recovery protect against duplicate creation after ambiguous network failures.

Transient Core failures (408/425/429/5xx) are retried with bounded exponential backoff. Application-level 4xx responses are not silently retried.

Successful v8.2 bindings are immutable. Re-submitting the same payload is an idempotent replay; reusing the same Librarian identity with different content returns a binding conflict so governed Core state cannot be silently overwritten. A changed research object/project must be represented as an explicit revised Librarian object.

## Database change

Ancillary SQLite schema: **19**.

New table: `platform_core_bindings`.

The Postgres/pgvector knowledge-index schema remains unchanged at Postgres schema 3 / `sc-research-librarian-postgres-index/1.2`.
