# Research Librarian AI v7.0.4 Validation Report

Release: **v7.0.4 — Asynchronous Index Rebuild and Recovery**  
Validation date: **2026-07-21**

## Release objective

The release moves full knowledge-index rebuilding out of the synchronous WordPress admin request. It introduces a persistent, resumable job that discovers sources, stages a transactional Python replacement index, verifies the committed index, streams a private recovery snapshot, and then starts semantic embedding.

## Validated recovery behavior

- Starting a rebuild returns after creating a persistent job.
- Source discovery runs in bounded pages and persists its cursor.
- Backend replacement synchronization sends one bounded batch per worker pass.
- The previous durable index remains active until the final replacement batch commits.
- Private JSONL staging supports file-cursor resume without loading the full corpus into memory.
- Recovery snapshots are streamed to JSON or gzip output.
- Pause, resume, cancel, manual next-batch, stale-lock recovery, and retry scheduling are present.
- Permanent configuration or credential failures stop safely.
- Retryable 429, 5xx, timeout, temporary, unreachable, and cold-start errors use bounded backoff.
- Semantic embedding starts only after the durable index reports nonzero records.

## Automated validation

| Validation | Result |
|---|---:|
| PHP syntax | 39 files passed |
| JavaScript syntax | 3 files passed |
| JSON parsing | 68 files passed |
| WordPress contract/functional suites | 25 of 25 passed |
| Reported WordPress assertions | 721 passed |
| Backend tests from repository root | 71 passed |
| Backend tests from Render-style `backend/` directory | 71 passed |
| Python bytecode compilation | Passed |
| Secret-pattern scan | Passed |

## Validation environment

- Python 3.13.5 for release validation; Render remains configured for Python 3.12.12.
- PHP 8.4.16 CLI.
- Node.js 22.16.0.

## New regression coverage

- `tests/v703-asynchronous-index-rebuild-contract-test.php`
- `tests/v703-asynchronous-index-lifecycle-functional-test.php`
- Existing v7.0.2 source-discovery and interface contracts retained.
- Existing backend transactional replacement, retrieval, governance, handoff, and recovery tests retained.

## Production boundary

The automated tests validate contracts, state transitions, packaging, and backend behavior. A production WordPress installation must still have a functioning WP-Cron runner or a real server cron request to `wp-cron.php`. The admin screen provides **Run Next Batch Now** when automatic cron execution is unavailable.

## Package-level checks

- Full repository ZIP integrity: passed.
- WordPress plugin ZIP integrity: passed.
- Full package PHP syntax after extraction: 39 files passed.
- WordPress package PHP syntax after extraction: 14 files passed.
- Package root folders and required v7.0.4 files: passed.
- Cache, bytecode, and test-generated SQLite artifacts excluded.
- Self-contained installer embedded payload checksum: passed.
- Self-contained installer `--self-test`: passed.
- Installer preamble Bash syntax: passed.
- Installer contains no `/usr/bin/cat`, `mapfile`, or `readarray` dependency.
