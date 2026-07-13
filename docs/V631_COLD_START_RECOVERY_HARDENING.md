# Research Librarian AI v6.3.1 — Cold-Start and Recovery Hardening

## Release objective

v6.3.1 makes temporary Render cold starts, interrupted synchronization jobs, malformed source records, and damaged recovery snapshots observable and recoverable without creating endless retry loops or replacing a known-good index.

## Startup contract

The backend reports `startup_state`, `startup_phase`, `startup_progress`, `service_started_utc`, `uptime_seconds`, and `ready` through `/health`, `/startup`, and `/status`. WordPress preserves these fields in its public-safe status response. The browser shows phase and percentage while retaining deterministic WordPress fallback.

## Retry contract

Full synchronization and cold-start recovery use capped exponential backoff. Attempt count, maximum attempts, last error, next run, phase, and progress are persisted. On exhaustion, no new cron event is created. Administrators can clear pending retries after correcting a permanent configuration failure.

## Stalled-job contract

A staging job older than `SC_RL_STALLED_JOB_SECONDS` is reported as stalled. `/v1/knowledge/maintenance` can mark it failed and optionally purge staged rows. The active index is never replaced by an incomplete transaction.

## Failed-record isolation

Raw synchronization records are validated individually. Valid records continue, rejected records are logged with bounded details, and the response reports `rejected_records`. During replacement, an invalid incoming record ID protects the previous valid record from deletion.

## Snapshot-integrity contract

WordPress verifies compressed-file SHA-256, declared record count, required record fields, duplicate IDs, each record content hash, and the canonical checksum. The backend verifies runtime snapshot payload checksum and record count before rollback. Invalid snapshots are reported and cannot be used for recovery or rollback.

## Public-notice contract

Cold-start and transient connection failures produce one visible notice per configured suppression window. Repeated identical events update occurrence and suppression metadata without repeatedly inserting public warning cards. Configuration, authentication, quota, empty-index, and integrity failures remain visible.

## Audit and export

The administrator JSON export includes backend status and manifest, WordPress ledger, sync report and history, recovery state and history, retry state, alert state, incremental queue, cron diagnostics, and snapshot-validation results. Secrets and raw API keys are not exported.

## Compatibility

v6.3.1 retains the v6.3.0 SQLite schema through an additive schema migration, preserves WordPress option names and private snapshots, retains all v6.2.x REST and shortcode behavior, and requires no paid database or persistent Render disk.
