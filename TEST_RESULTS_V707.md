# Research Librarian v7.0.7 Validation Report

**Release:** v7.0.7 — Durable Incremental Index Activation  
**Validation date:** 2026-07-21

## Repair target

v7.0.6 could stage all WordPress source batches but delegated replacement-index activation to an in-process FastAPI background task. A backend restart or process recycle could discard that task and return activation to `queued · 0%`.

v7.0.7 replaces that task with a durable SQLite-backed activation state machine. WordPress advances one authenticated, bounded backend step at a time. Every step persists its cursor, counters, heartbeat, and shadow-index state before returning.

## Automated validation

- PHP syntax: **43/43 files passed**
- WordPress/PHP suites: **29/29 passed**
- Reported WordPress/PHP contract checks: **795 passed, 0 failed**
- JavaScript syntax: **3/3 files passed**
- JSON parsing: **80/80 files passed**
- Python compilation: **passed**
- Backend tests from repository root: **78/78 passed**
- Backend tests from Render-style `backend/` working directory: **78/78 passed**
- Secret-pattern scan: **passed**

## Durable activation coverage

The v7.0.7 regression suite verifies:

- no FastAPI in-process background task is required for index activation;
- existing v7.0.6 `queued` and `activating` jobs upgrade in place;
- replacement records are copied to shadow tables in bounded batches;
- retrieval chunks are built in bounded record groups;
- checksums are advanced and persisted incrementally;
- the previous active index remains readable until final verification;
- each activation step can survive reopening the SQLite database;
- the final active-index switch is one database-local transaction;
- missing backend state can still be recovered from the WordPress staging file.

## Manual restart simulation

A manual simulation repeatedly closed and reopened the `KnowledgeStore` between activation steps. A 235-record replacement completed through copy, chunk, checksum, and switch phases while the previous active index remained available until the final transaction.

## Operational note

For strongest durability on Render, attach persistent storage and configure:

```text
SC_RL_DATA_DIR=/var/data/sc-research-librarian
```

When backend storage remains ephemeral, WordPress retains the complete source staging file and can replay the transaction after backend state loss.
