# Research Librarian AI v6.3.1 Validation Report

## Release

- **Version:** 6.3.1
- **Title:** Cold-Start and Recovery Hardening
- **Backend runtime:** Python 3.12.12
- **Storage:** SQLite schema 4 with WordPress canonical snapshots
- **Deployment boundary:** Free Render-compatible; no paid database or persistent disk required

## WordPress and release contracts

Eight PHP release suites passed:

1. Collision-safe bootstrap and registration
2. v6.3.1 cold-start and recovery hardening contract
3. Private snapshot round-trip and tamper rejection
4. Endpoint, transactional index, and recovery reliability
5. Gemini authorization-key compatibility
6. Knowledge-intelligence contract
7. Live AI provider and routing contract
8. Retry/backoff and alert-suppression functional test

Key results:

- **51/51** v6.3.1 hardening contract checks passed.
- **38/38** inherited endpoint and durable-index checks passed.
- Snapshot creation, decompression, record hash verification, and tamper rejection passed.
- Retry delays validated at 10, 20, 40, and capped 40 seconds.
- Retry exhaustion stopped scheduling after the configured ceiling.
- The first transient alert remained visible and the repeated alert was suppressed.
- Permanent configuration alerts were not suppressed.

## FastAPI and SQLite tests

- **20/20** backend tests passed from the repository root.
- **20/20** backend tests passed from `backend/`, validating Render import behavior.
- Covered startup state, isolated record rejection, prior-record protection, atomic synchronization, out-of-order batches, duplicate batches, stale-job repair, snapshot integrity, rollback blocking, manifest output, maintenance endpoints, retrieval, and API authentication.

## Static validation

- **19** PHP files passed syntax validation.
- **2** JavaScript files passed syntax validation.
- **47** JSON files passed parsing validation.
- Python compile validation passed for `backend/app` and `backend/tests`.
- `PUSH_RESEARCH_LIBRARIAN_V631_PY312.sh` passed Bash syntax validation.
- Version markers passed for WordPress, readme, and FastAPI.
- Common GitHub, OpenAI, Gemini, and private-key patterns were not detected.

## v6.3.1 release gates

- Startup state, phase, progress, uptime, and readiness are exposed.
- Synchronization and recovery use bounded exponential backoff.
- Retry exhaustion creates a manual-review state and no endless cron loop.
- Stalled staging jobs are detectable and repairable.
- Malformed records are isolated while valid records commit.
- A malformed replacement cannot delete the prior valid record.
- WordPress snapshots verify file hash, record count, duplicate IDs, record hashes, and canonical checksum.
- Runtime snapshots are verified before rollback.
- Public duplicate transient notices are suppressed within a configurable window.
- Administrator operations-log export excludes raw API keys and provider secrets.
- The terminal-style black question field and light answer/source-card surfaces remain intact.

## Packaged-artifact verification

The final ZIP was extracted into a clean directory and the complete PHP, JavaScript, JSON, Python, backend-test, WordPress-contract, compile, and release-marker validation sequence was repeated against the extracted artifact.
