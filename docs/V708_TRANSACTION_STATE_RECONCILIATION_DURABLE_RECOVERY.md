# v7.0.8 — Transaction-State Reconciliation and Durable Recovery

## Purpose

v7.0.8 repairs the reconciliation failure where an empty `missing_batches` array was treated as proof that a backend transaction was complete. An empty list can also describe a lost or empty backend transaction whose batch count is zero. WordPress now compares the backend manifest with its own expected batch count before choosing an activation or replay action.

## Deterministic reconciliation actions

The authenticated endpoint `POST /v1/knowledge/sync/jobs/{job_id}/reconcile` returns one of four actions:

- `committed` — the replacement index is already active.
- `activate` — every expected batch is retained and activation may continue.
- `replay-missing` — the transaction exists but specific batches are absent.
- `replay-all` — the transaction is missing, empty, indeterminate, or has a mismatched batch manifest.

An empty missing-batch list is accepted only when the backend batch count equals the WordPress batch count and every expected batch number is present.

## Durable recovery

WordPress preserves the complete JSONL staging file until index verification finishes. v7.0.8 records byte offsets for each synchronization batch. When the backend reports specific missing batches, WordPress replays only those batches. When backend state has disappeared or contains an empty shell, WordPress creates a fresh transaction and replays all batches without rediscovering the site.

Replay counters reset after successful reconciliation. Resuming a v7.0.7 job that stopped after exhausted reconciliation begins a new recovery generation while preserving the staging file.

## Persistent Render storage

Attach a Render persistent disk and set:

```text
SC_RL_DATA_DIR=/var/data/sc-research-librarian
```

When `/var/data` is mounted and writable, the backend automatically uses it if `SC_RL_DATA_DIR` is not explicitly set. The status response exposes the storage path, whether it is persistent, and a warning when the transaction database is still under `/tmp`.
