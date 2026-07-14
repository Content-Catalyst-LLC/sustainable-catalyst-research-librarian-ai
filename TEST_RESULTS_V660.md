# Research Librarian AI v6.6.0 Validation Report

**Release:** Platform Intelligence and Typed Research Handoffs  
**Full package:** `sustainable-catalyst-research-librarian-ai-v6.6.0.zip`  
**WordPress package:** `sustainable-catalyst-research-librarian-ai-wordpress-v6.6.0.zip`

## Release contract

v6.6.0 adds a versioned connection layer between verified Research Librarian evidence and Sustainable Catalyst Workbench, Decision Studio, Site Intelligence, Lab, and Feature Suggestions.

Validated release elements include:

- `sc-research-handoff/2.0` common handoff envelopes;
- `sc-research-route/2.0` destination routes;
- `sc-research-artifact-return/1.0` provenance-preserving artifact returns;
- destination-specific Workbench, Decision Studio, Site Intelligence, Lab, and Feature Suggestions payloads;
- capability discovery and unavailable-destination suppression;
- human-confirmation boundaries and tamper-evident SHA-256 fingerprints;
- authenticated FastAPI handoff endpoints;
- nonce-protected WordPress preparation, validation, artifact-return, and export routes;
- additive SQLite schema version 7 handoff and artifact ledgers;
- public workspace schema `sc-research-librarian-public-workspace/1.2`;
- preservation of v6.5.1 accessibility/performance behavior and all earlier retrieval and recovery contracts.

## Automated validation

| Validation | Result |
|---|---:|
| v6.6.0 platform intelligence static contract | 82/82 passed |
| WordPress fallback handoff and tamper functional test | Passed |
| Total WordPress/PHP suites | 14/14 passed |
| Total named PHP checks and functional assertions | 525 passed |
| Backend tests from repository root | 51/51 passed |
| Backend tests from `backend/` | 51/51 passed |
| PHP syntax validation | 26 files passed |
| JavaScript syntax validation | 2 files passed |
| JSON validation | 55 files passed |
| Python compilation | Passed |
| Push-script Bash syntax | Passed |
| Secret-pattern scan | Passed |

## Functional behaviors verified

- Capability discovery exposes configured Workbench, Decision Studio, Site Intelligence, Lab, and Feature Suggestions contracts.
- Query and mode signals infer typed destinations.
- Workbench handoffs preserve equations, units, evidence, validation requirements, and requested outputs.
- Altering a signed handoff causes fingerprint validation to fail.
- WordPress can prepare a reviewable local fallback handoff when FastAPI is temporarily unavailable.
- WordPress fallback validation also rejects a handoff altered after signing.
- FastAPI persists prepared handoffs when requested.
- Artifact returns require a stored original handoff and matching destination.
- Returned artifacts inherit the original handoff fingerprint and provenance chain.
- Public ask responses contain capability, typed-handoff, and provenance fields.
- Public action cards are generated only from currently available capabilities.

## Compatibility

- SQLite upgrades additively from schema 6 to schema 7.
- Existing records, chunks, embeddings, snapshots, tombstones, synchronization history, retrieval configuration, benchmark history, and recovery data are preserved.
- WordPress remains the canonical publishing and recovery source.
- No paid vector database or persistent Render disk is required.
- The black-and-green question field and light answer/evidence/source cards are preserved.
- v6.5.1 keyboard, screen-reader, reduced-motion, forced-colors, mobile, caching, and request-cancellation behavior remains active.

## Packaging boundary

The WordPress ZIP contains only the installable plugin runtime: the main plugin file, includes, browser assets, data manifests, knowledge files, license, and WordPress readme. It excludes FastAPI, pytest, Render configuration, repository tests, development documentation, and GitHub push scripts.

The full repository ZIP contains the WordPress plugin, FastAPI backend, Render blueprint, tests, documentation, release manifests, and the Python 3.12-safe GitHub push script.
