# Research Librarian AI v6.4.1 Validation Report

## Release

- **Version:** 6.4.1
- **Release:** Retrieval Calibration and Regression Patch
- **Backend storage:** SQLite
- **Knowledge index schema:** `sc-research-librarian-knowledge-index/6.0`
- **Python production pin:** 3.12.12
- **Local build validation interpreter:** Python 3.13.5
- **WordPress remains the canonical publishing and recovery source.**

## v6.4.1 release contract

The dedicated retrieval-calibration contract passed **79/79 checks** covering:

- current WordPress, module, and backend version markers;
- SQLite schema version 6 and knowledge-index contract 6.0;
- bounded structural, lexical, semantic, and RRF weights;
- evidence, ambiguity, citation-coverage, and context thresholds;
- post-type/source weights and explicit exclusions;
- calibration models and API payloads;
- calibration-aware ranking and latency diagnostics;
- near-duplicate-title detection;
- minimum-evidence gating;
- unsupported paragraph and numeric-claim verification;
- configuration and benchmark persistence;
- retrieval configuration and benchmark endpoints;
- WordPress calibration controls and benchmark action;
- packaged documentation, release manifest, and benchmark dataset;
- free-tier compatibility.

## Inherited WordPress contracts

All **10/10** WordPress release and functional suites passed.

| Suite | Result |
|---|---:|
| v6.4.1 retrieval calibration and regression | 79/79 |
| v6.4.0 hybrid retrieval and citation | 62/62 |
| v6.3.1 cold-start and recovery hardening | 51/51 |
| v6.3.0/v6.2.1 endpoint and durable-index reliability | 38/38 |
| Live AI/provider integration | 25/25 |
| Knowledge-intelligence contract | Passed |
| Gemini authorization-key compatibility | Passed |
| Collision-safe bootstrap registration | Passed |
| Durable snapshot round trip | Passed |
| Recovery backoff and duplicate-alert suppression | Passed |

## Backend tests

The complete backend suite passed in both supported import layouts:

```text
Repository root: 40 passed
backend/:       40 passed
```

Coverage includes:

- atomic multi-batch synchronization and idempotency;
- upsert, delete, tombstone, rollback, and legacy JSON migration;
- malformed-record isolation and stalled-job repair;
- snapshot-integrity validation;
- exact-title, section-aware BM25, semantic, and RRF retrieval;
- citation and generated-link verification;
- persisted retrieval profiles;
- post-type weighting and record exclusions;
- near-duplicate-title ambiguity;
- exact-title priority under confusing-title competition;
- minimum-evidence thresholds;
- unsupported paragraphs and numeric claims;
- context-budget limits;
- lexical-versus-hybrid benchmark execution and history.

## Syntax and static validation

- **21** PHP files passed `php -l`.
- **2** JavaScript files passed `node --check`.
- **50** JSON files parsed successfully.
- Python application and test modules passed `compileall`.
- `PUSH_RESEARCH_LIBRARIAN_V641_PY312.sh` passed Bash syntax validation.
- The push-safe secret-pattern scan found no matching private keys or common provider/token formats.

## macOS release workflow safeguards

The push script retains the corrected release workflow from v6.2.1 and later:

- explicitly locates Python 3.12;
- clears `__PYVENV_LAUNCHER__`, virtual-environment, Conda, and Pyenv overrides;
- creates the isolated environment with copied binaries;
- verifies the environment reports Python 3.12 before dependency installation;
- requires binary dependency wheels;
- runs pytest from both the repository root and `backend/`;
- refuses to push when the repository is dirty or the v6.4.1 tag already exists.

## Exact packaged-artifact retest

The delivered ZIP was extracted into a clean directory and independently retested:

- 10/10 WordPress suites passed.
- 40/40 backend tests passed from the extracted repository root.
- 40/40 backend tests passed from the extracted `backend/` directory.
- 21 PHP, 2 JavaScript, and 50 JSON files passed validation.
- Python compilation, Bash syntax validation, release markers, secret scan, and SHA-256 verification passed.

## Release conclusion

**PASS — Research Librarian AI v6.4.1 is ready for repository push, Render deployment, WordPress installation, retrieval benchmarking, and human-reviewed calibration.**
