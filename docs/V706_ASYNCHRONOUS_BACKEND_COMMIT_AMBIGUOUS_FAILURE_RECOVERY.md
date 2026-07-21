# v7.0.6 — Asynchronous Backend Commit and Ambiguous-Failure Recovery

## Purpose

v7.0.6 removes durable-index activation from the final WordPress synchronization request. WordPress now stages every source batch, queues activation through a short authenticated request, and polls durable backend status until the replacement index is committed.

## Production failure repaired

The prior workflow accepted batches 1–23 normally, then used batch 24 to stage the remaining records and synchronously snapshot, activate, rechunk, checksum, and commit the entire replacement index. On a large corpus, a proxy or application timeout could return an empty 5xx response even though all source records had reached the transaction boundary.

## New transaction lifecycle

1. WordPress discovers and validates the source collection in bounded steps.
2. Every synchronization request includes `defer_commit: true`.
3. The final batch returns `ready-to-commit` without rebuilding the active index.
4. WordPress calls `POST /v1/knowledge/sync/jobs/{job_id}/commit`.
5. FastAPI returns immediately and activates the replacement in a background task.
6. WordPress polls `GET /v1/knowledge/sync/jobs/{job_id}`.
7. The existing active index remains available until the background transaction completes.
8. WordPress verifies the committed index, writes its ledger and recovery snapshot, and starts semantic indexing.

## Durable backend states

- `staging`
- `ready-to-commit`
- `commit-queued`
- `committing`
- `commit-stalled`
- `completed`
- `completed-with-rejections`
- `failed`

The status response also reports commit phase, progress, timestamps, activated records, activation total, indexed chunks, received batches, and missing batches.

## Ambiguous-response recovery

If the final staging request returns a transport error or an empty 5xx response, WordPress checks the backend transaction before failing. When all batches are retained, the workflow moves directly to backend activation. Missing batches continue through the bounded transaction-reconciliation path.

If a Render process restarts while activation is marked `committing`, a heartbeat older than five minutes is reported as `commit-stalled`. WordPress can safely queue the idempotent commit operation again without rediscovering the source collection.

## Interface changes

The asynchronous rebuild panel now distinguishes:

- source batches staged;
- backend activation phase;
- activation progress;
- activated records;
- retrieval chunks rebuilt;
- transaction reconciliation.

The interface explains that all source batches are safe while backend activation runs independently of the browser request.

## Safety boundaries

- The previous committed index remains active until the replacement commits.
- The WordPress JSONL staging file remains available until verification succeeds.
- Commit queueing is idempotent.
- Missing batches block activation.
- A failed activation preserves staged source data for retry.
- Gemini generation and embedding credentials are not involved in durable record activation.
