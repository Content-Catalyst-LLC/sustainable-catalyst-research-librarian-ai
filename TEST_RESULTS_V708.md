# Research Librarian v7.0.8 Validation Report

**Release:** v7.0.8 — Transaction-State Reconciliation and Durable Recovery  
**Validation date:** 2026-07-21

## Repair target

v7.0.7 could preserve and incrementally activate a complete backend transaction, but WordPress could still stop after exhausted replay attempts when the backend returned an empty `missing_batches` list. That list was ambiguous: it could mean either every expected batch was retained or the backend transaction had disappeared and retained zero batches.

v7.0.8 makes reconciliation deterministic by comparing the WordPress-owned expected batch count with the backend batch manifest before choosing activation or replay.

## Reconciliation states covered

- **Committed:** the replacement index is already active.
- **Complete:** the backend retained every expected batch; continue directly to durable activation.
- **Incomplete:** specific numbered batches are absent; replay only those batches from saved WordPress byte offsets.
- **Missing or empty:** the backend transaction disappeared or retained zero batches; create a fresh recovery generation and replay the full WordPress staging file.
- **Batch-count mismatch or indeterminate:** create a new backend transaction and perform a controlled full replay.

The zero-batch transaction case is explicitly rejected by the backend activation endpoint so an empty `missing_batches` list can never be mistaken for a complete transaction.

## Automated validation

- Backend tests from repository layout: **83/83 passed**
- Backend tests from Render-style `backend/` layout: **83/83 passed**
- WordPress/PHP suites: **30/30 passed**
- Explicitly reported contract checks: **821 passed, 0 failed**, plus functional workflow suites
- PHP syntax: **44/44 files passed**
- JavaScript syntax: **3/3 files passed**
- JSON parsing: **83/83 files passed**
- Python compilation: **passed**
- Secret-pattern scan: **passed**; no embedded API keys, GitHub tokens, or private keys were found

## Durable recovery coverage

The v7.0.8 regression suite verifies:

- an empty missing-batch list is accepted only when the backend batch count and complete received-batch manifest match WordPress;
- a missing or zero-batch backend transaction produces `replay-all` rather than a false activation state;
- a partial transaction produces `replay-missing` with concrete batch numbers;
- a complete 24/24 transaction proceeds directly to activation;
- zero-batch activation is refused;
- exhausted v7.0.7 replay state resets into a new recovery generation without deleting the WordPress staging file;
- saved per-batch byte offsets support bounded replay of only missing batches;
- replay counters reset after successful reconciliation;
- admin diagnostics expose transaction state, recovery action, transaction ID, generation, and replay attempt.

## Persistent Render storage

For strongest restart durability, attach a Render persistent disk and configure:

```text
SC_RL_DATA_DIR=/var/data/sc-research-librarian
```

When `/var/data` is mounted and writable, v7.0.8 automatically selects it if `SC_RL_DATA_DIR` is not explicitly set. The status response reports the storage path, persistence state, and a warning when backend transaction data still resides under `/tmp`.
