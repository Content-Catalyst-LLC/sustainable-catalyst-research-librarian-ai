# v7.0.7 — Durable Incremental Index Activation

## Problem repaired

v7.0.6 staged every WordPress source batch successfully, but it delegated the entire replacement activation to a FastAPI in-process background task. A Render restart, process recycle, memory limit, or long SQLite operation could terminate that task after it reported `queued` or `activating`. WordPress would then observe the transaction return to `queued · 0%` even though all source batches remained staged.

## Durable activation state machine

v7.0.7 removes FastAPI `BackgroundTasks` from index activation. WordPress advances one authenticated, bounded backend step per scheduled job iteration through:

`POST /v1/knowledge/sync/jobs/{job_id}/commit/step`

Every step commits its cursor and heartbeat before returning:

1. `preparing`
2. `copying-records`
3. `building-chunks`
4. `checksumming`
5. `ready-to-switch`
6. `switching`
7. `completed`

The active `records` and `retrieval_chunks` tables are not modified while the shadow index is being copied, chunked, or verified. The final switch is one database-local SQLite transaction. If that transaction is interrupted, SQLite rollback preserves the previous active index.

## Restart recovery

The backend stores activation cursors, counts, checksum progress, and shadow records in SQLite. A new FastAPI process can reopen the same database and continue from the next record. Existing v7.0.6 jobs in `queued` or `activating` state are upgraded in place without requiring WordPress source rediscovery.

When backend ephemeral state is lost completely, the existing WordPress JSONL staging file remains the canonical replay source. WordPress starts a fresh backend transaction and replays the already-discovered records.

## Bounded controls

- `SC_RL_ACTIVATION_RECORD_BATCH_LIMIT` — shadow records copied per step; default 100
- `SC_RL_ACTIVATION_CHUNK_RECORD_BATCH_LIMIT` — records chunked per step; default 20
- `SC_RL_ACTIVATION_CHECKSUM_BATCH_LIMIT` — records verified per step; default 250
- `SC_RL_ACTIVATION_SNAPSHOT_RECORD_LIMIT` — maximum active records for an in-process runtime snapshot before switch; default 500

## Persistent storage

For strongest restart durability, attach persistent storage to the backend and set:

```text
SC_RL_DATA_DIR=/var/data/sc-research-librarian
```

The release still retains WordPress replay and canonical snapshots when backend storage is ephemeral.

## Human control and safety

- The previous active index remains available until the replacement verifies.
- Pause and cancel controls remain in WordPress.
- No provider call is required for source activation.
- Gemini embedding begins only after the durable index is committed and verified.
- No autonomous publication or external action is introduced.
