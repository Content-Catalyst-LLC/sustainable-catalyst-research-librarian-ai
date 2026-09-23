# Research Librarian AI v8.3.0 — Asynchronous Ingestion & Document Processing Runtime

## Purpose

v8.3.0 introduces a durable Python work queue so ingestion and document-processing operations can survive HTTP disconnects, process restarts, and transient provider/database failures. The queue is an operational layer; it does not replace Platform Core's governed research/evidence model.

## Runtime boundary

Research Librarian Python owns acquisition, normalization, parsing, chunking, embedding, indexing, retrieval, connectors, and document-processing jobs. Platform Core v3.3+ remains authoritative for governed evidence, claims, findings, arguments, conclusions, provenance/lineage, statistical/visual reasoning, reproducibility packages, and cross-product exchange.

## Queue contract

The production queue is stored in Postgres/Neon tables `sc_rl_async_jobs` and `sc_rl_async_job_events`. Workers claim one eligible row with `FOR UPDATE SKIP LOCKED`, assign a lease, increment the attempt count, and persist a worker identity. Local/test operation uses a separate SQLite queue with `BEGIN IMMEDIATE` claim serialization.

Each job records:

- job ID and type
- state and stage
- priority
- idempotency key and SHA-256 input fingerprint
- payload and result
- attempt/max-attempt counts
- progress
- worker lease and heartbeat
- available/start/update/completion timestamps
- bounded error text

Job states are `queued`, `retry_wait`, `running`, `succeeded`, `failed`, and `cancelled`.

## Retry and recovery

A failed attempt is returned to `retry_wait` until `max_attempts` is exhausted. Retry delay uses bounded exponential backoff. A process crash leaves a worker lease; subsequent workers reclaim expired leases as retryable jobs. Successful jobs are terminal and do not automatically re-run.

## v8.3 document-processing executor

`document-process` and `ingestion` jobs perform:

1. payload normalization and KnowledgeRecord validation
2. durable knowledge-index staging
3. restart-safe activation through the existing sync-generation state machine
4. optional embeddings when explicitly requested and configured
5. post-activation read-back validation

This preserves the v7.1.x Postgres generation/activation guarantees rather than creating a parallel index writer.

The queue also reserves the job types `embedding`, `index`, `validation`, and `connector-run`. v8.3 provides a validation executor and the document/ingestion executor; the remaining types are registered for subsequent specialized executors and fail visibly if dispatched prematurely.

## API

Authenticated with `X-SC-RL-Key`:

- `GET /v1/jobs/runtime`
- `GET /v1/jobs`
- `POST /v1/jobs`
- `POST /v1/jobs/documents`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/events`
- `POST /v1/jobs/{job_id}/retry`
- `DELETE /v1/jobs/{job_id}`

## Operational settings

- `SC_RL_ASYNC_JOBS_ENABLED=true`
- `SC_RL_ASYNC_JOB_POLL_SECONDS=1.0`
- `SC_RL_ASYNC_JOB_LEASE_SECONDS=120`
- `SC_RL_ASYNC_JOB_RECLAIM_INTERVAL_SECONDS=60`
- `SC_RL_ASYNC_JOB_RETRY_BASE_SECONDS=5.0`
- `SC_RL_ASYNC_JOB_RETRY_MAX_SECONDS=900`

The worker starts and stops through the FastAPI lifespan handler. Multi-worker safety comes from durable database claim semantics rather than process-local locks.

## Governance constraints

A document being successfully processed means only that it was normalized and indexed. It does not imply source credibility, truth, editorial approval, evidence acceptance, or a Platform Core finding/claim. Promotion into governed research objects remains an explicit Core integration operation.
