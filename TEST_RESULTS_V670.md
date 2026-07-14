# Research Librarian AI v6.7.0 Validation Report

**Release:** Research Quality and Governance Center  
**Full package:** `sustainable-catalyst-research-librarian-ai-v6.7.0.zip`  
**WordPress package:** `sustainable-catalyst-research-librarian-ai-wordpress-v6.7.0.zip`

## Release scope

v6.7.0 adds a versioned governance policy, source approval and freshness review, privacy-minimized answer traces, quality evaluations, measured release gates, retention enforcement, governance exports, and a public methodology and limitations layer. Automated checks may pass, request review, or block a release, but they cannot publish content, exclude a source, or override a failed gate without human review.

## Dedicated v6.7.0 verification

| Test | Result |
|---|---:|
| Research quality and governance static contract | 38/38 passed |
| WordPress governance defaults and methodology functional test | Passed |
| Backend governance API and persistence tests | 6/6 passed |
| Policy reviewer requirement | Passed |
| Source-exclusion reviewer requirement | Passed |
| Source exclusion removed reviewed record from retrieval | Passed |
| Privacy-minimized answer trace creation | Passed |
| Critical citation failure blocked by release gate | Passed |
| Named human release override | Passed |
| Public methodology and retention dry run | Passed |

## Complete regression results

| Validation | Result |
|---|---:|
| WordPress/PHP suites | 18/18 passed |
| Named PHP contract checks | 640 passed |
| Backend tests from repository root | 63/63 passed |
| Backend tests from `backend/` | 63/63 passed |
| PHP syntax | 31 files passed |
| JavaScript syntax | 2 files passed |
| JSON validation | 57 files passed |
| Python compilation | Passed |
| Render YAML parse | Passed |
| Push-script Bash syntax | Passed |
| Common secret-pattern scan | No matches |

## Compatibility and migration

- Plugin and backend version: 6.7.0
- SQLite schema: 9
- Knowledge-index contract: `sc-research-librarian-knowledge-index/9.0`
- Migration from schema 8 is additive.
- Existing records, chunks, embeddings, snapshots, benchmarks, handoffs, receipts, artifacts, synchronization history, and recovery state remain readable.
- WordPress remains the canonical publishing and recovery layer.
- Query and answer text are not stored in governance traces by default.
- Session references are hashed by default.
- No paid vector database, message broker, or persistent Render disk is required.
- The black-and-green prompt and light answer/evidence cards remain unchanged.

## Governance contracts

- `sc-research-governance-policy/1.0`
- `sc-research-source-review/1.0`
- `sc-research-answer-trace/1.0`
- `sc-research-quality-evaluation/1.0`
- `sc-research-quality-metrics/1.0`
- `sc-research-release-gate/1.0`
- `sc-research-methodology/1.0`
- `sc-research-governance-export/1.0`

## Runtime note

The packaged test suite was executed in the build environment with the available system Python. Deployment remains pinned to Python 3.12.12. `PUSH_RESEARCH_LIBRARIAN_V670_PY312.sh` locates and verifies Python 3.12 before installing dependencies or running either backend test layout, preserving the corrected macOS launcher safeguards from earlier releases.
