# Research Librarian AI v6.3.0 — Durable Knowledge Index, Sync Ledger, and Recovery

## Release purpose

v6.3.0 prevents a backend restart, interrupted batch, duplicate retry, or WordPress deletion from silently corrupting the Research Librarian index. It remains compatible with free Render infrastructure and does not require PostgreSQL, a paid vector database, or a persistent disk.

## Authority model

WordPress is the canonical publishing and recovery authority. It collects public records, calculates content hashes, maintains the incremental change ledger, and stores private compressed snapshots. FastAPI maintains a high-performance SQLite runtime index for retrieval and synthesis.

The SQLite file may be ephemeral. Its loss does not remove the canonical knowledge snapshot.

## Transactional synchronization

A full synchronization has one job ID and an expected batch count. FastAPI stages records and deletions without changing the active index. The commit occurs only after all distinct batches arrive. Batches may arrive out of order. Repeated batches and completed-job retries are idempotent.

Before each commit, FastAPI creates a runtime safety snapshot. A failed or incomplete job leaves the previous active index unchanged.

## Runtime SQLite schema

The schema stores:

- active records and canonical payloads
- content hashes and update timestamps
- index metadata and checksums
- staging records and deletions
- synchronization jobs and received-batch state
- deletion tombstones
- runtime rollback snapshots

Legacy JSON runtime data is migrated when present.

## Incremental change ledger

WordPress observes saved posts, publication-status transitions, trash operations, and permanent deletions. It records an upsert or delete operation in a bounded queue. The incremental worker sends only changed records and explicit deletions. Unchanged content hashes do not rewrite the record.

A complete transactional sync periodically reconciles the entire public source set and removes stale backend records.

## Canonical WordPress snapshots

Full synchronization creates a gzip JSON snapshot in a private uploads subdirectory. The directory includes Apache, IIS, and index-file protections against direct browsing. Snapshot metadata includes:

- schema and release version
- source site
- creation time
- record count
- canonical record checksum
- compressed-file SHA-256
- records and content hashes

Retention is configurable from one to twenty snapshots.

## Automatic recovery

When WordPress can reach FastAPI but the backend manifest reports zero records, automatic recovery may schedule a single rehydration job. WordPress verifies the latest snapshot checksum, expands it, and submits it as a transactional replacement with a recovery reason. FastAPI records the recovery time and creates a new runtime index version.

Recovery does not run when the backend is merely unreachable; it waits until connectivity returns.

## Rollback

FastAPI retains a bounded set of runtime safety snapshots. An administrator can select a snapshot and invoke the authenticated rollback endpoint. Rollback replaces active records transactionally, updates the manifest and checksum, and records the rollback timestamp.

WordPress canonical snapshots and backend runtime snapshots serve different purposes: WordPress snapshots recover ephemeral loss; runtime snapshots revert a recently committed bad synchronization.

## Administrator controls

The Python Intelligence screen provides:

- Test Backend
- Transactional Full Sync
- Process Incremental Queue
- Create WordPress Snapshot
- Recover Empty Backend
- Repair and Resynchronize
- Runtime Rollback
- Reset Public Rate Limits

It also displays backend storage/schema/index versions, checksums, staging jobs, snapshot counts, incremental queue state, WordPress ledger state, and recovery history.

## API additions

```text
GET  /v1/knowledge/manifest
GET  /v1/knowledge/snapshots
POST /v1/knowledge/rollback
```

`POST /v1/knowledge/sync` now accepts replace, upsert, and delete modes with job ID, batch position, expected batch count, deleted IDs, and synchronization reason.

## Compatibility

v6.3.0 preserves existing option names, the public shortcode, REST request flow, endpoint diagnostics, provider integration, and v6.2.x compatibility aliases. Existing users can upgrade without re-entering settings. The black-and-green public question field and light answer/source-card surfaces remain unchanged.
