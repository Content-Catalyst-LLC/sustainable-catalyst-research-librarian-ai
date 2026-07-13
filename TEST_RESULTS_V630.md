# Research Librarian AI v6.3.0 Validation Report

**Release:** Durable Knowledge Index, Sync Ledger, and Recovery  
**Validation date:** July 13, 2026

## Release outcomes

- WordPress remains the canonical source and stores private compressed recovery snapshots.
- FastAPI uses a transactional SQLite runtime index with schema version 3.
- Full synchronization stages all expected batches before atomically replacing the active index.
- Incremental upserts, deletions, content hashes, tombstones, idempotent jobs, runtime snapshots, rollback, and legacy JSON migration are implemented.
- An empty ephemeral backend can be rehydrated from the latest verified WordPress snapshot.
- The v6.2.1 endpoint reliability controls and black-and-green terminal prompt remain intact.

## Validation results

| Validation | Result |
|---|---:|
| PHP syntax | 17 files passed |
| JavaScript syntax | 2 files passed |
| JSON parsing | 46 files passed |
| WordPress/PHP contract suites | 6 suites passed |
| Durable-index static contract | 38/38 checks passed |
| Private snapshot round trip | Passed |
| FastAPI/backend tests from repository root | 14 passed |
| FastAPI/backend tests from `backend/` | 14 passed |
| Python compile validation | Passed |
| Push-script Bash syntax | Passed |
| Push-safe secret-pattern scan | Passed |

## Backend tests covered

- Atomic two-batch replacement
- Out-of-order batch completion
- Completed-job idempotency
- Duplicate-batch handling
- Incremental upsert and deletion
- Deletion tombstones
- Unchanged content-hash detection
- Runtime safety snapshot rollback
- Legacy v6.2.x JSON-index migration
- Manifest and runtime snapshot endpoints
- Authentication enforcement
- Invalid batch-position rejection
- Exact-title retrieval after synchronization

## Snapshot validation

The functional PHP test created the private WordPress snapshot directory, verified Apache/IIS/index protections, wrote a compressed snapshot, checked its SHA-256, validated the canonical record checksum, and read the record back with its generated content hash.

## Runtime note

The build environment executed the Python suite under Python 3.13.5. The project runtime remains pinned to Python 3.12.12 in `backend/runtime.txt` and `render.yaml`. `PUSH_RESEARCH_LIBRARIAN_V630_PY312.sh` explicitly locates Python 3.12, clears macOS launcher and virtual-environment overrides, verifies the resulting test environment, requires binary dependency wheels, and runs the tests from both supported working directories before pushing.

## Release artifacts

- `sustainable-catalyst-research-librarian-ai-v6.3.0.zip`
- `PUSH_RESEARCH_LIBRARIAN_V630_PY312.sh`
- `sustainable-catalyst-research-librarian-ai-v6.3.0.zip.sha256`
