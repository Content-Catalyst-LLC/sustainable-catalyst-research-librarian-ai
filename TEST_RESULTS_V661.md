# Research Librarian AI v6.6.1 Validation Report

**Release:** Cross-Product Reliability Patch  
**Full package:** `sustainable-catalyst-research-librarian-ai-v6.6.1.zip`  
**WordPress package:** `sustainable-catalyst-research-librarian-ai-wordpress-v6.6.1.zip`

## Release scope

v6.6.1 hardens the v6.6.0 typed handoff layer with destination-version compatibility checks, short-lived delivery tokens, explicit token refresh, bounded retry metadata, event idempotency, validated destination receipts, immutable artifact IDs, artifact-type and payload-size enforcement, and additive SQLite schema version 8 storage.

## Dedicated v6.6.1 verification

| Test | Result |
|---|---:|
| Cross-product reliability static contract | 90/90 passed |
| WordPress fallback delivery-token round trip | Passed |
| WordPress tamper rejection | Passed |
| Compatible/unverified/incompatible version-state checks | Passed |
| Backend compatibility, retry, refresh, receipt, and artifact tests | 6/6 passed |
| Idempotent event replay | Passed |
| Conflicting artifact replay rejection | Passed |

## Complete regression results

| Validation | Result |
|---|---:|
| WordPress/PHP suites | 16/16 passed |
| Backend tests from repository root | 57/57 passed |
| Backend tests from `backend/` | 57/57 passed |
| PHP syntax | 28 files passed |
| JavaScript syntax | 2 files passed |
| JSON validation | 56 files passed |
| Python compilation | Passed |
| Push-script Bash syntax | Passed |
| Common secret-pattern scan | No matches |

## Compatibility and migration

- Plugin and backend version: 6.6.1
- SQLite schema: 8
- Knowledge-index contract: `sc-research-librarian-knowledge-index/8.0`
- Migration from schema 7 is additive.
- Existing records, chunks, embeddings, snapshots, benchmarks, handoffs, and artifact returns remain readable.
- WordPress remains the canonical publishing and recovery layer.
- No paid vector database, message broker, or persistent Render disk is required.
- The black-and-green prompt and light answer/evidence cards remain unchanged.

## Runtime note

The packaged test suite was executed in the build environment with Python 3.13.5. Deployment remains pinned to Python 3.12.12. `PUSH_RESEARCH_LIBRARIAN_V661_PY312.sh` locates and verifies Python 3.12 before installing dependencies or running either backend test layout, preventing the Python 3.14/PyO3 failure encountered in earlier release workflows.
