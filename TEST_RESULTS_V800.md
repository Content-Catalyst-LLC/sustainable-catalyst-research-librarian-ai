# Research Librarian AI v8.0.0 — Certification Results

Release: **v8.0.0 — Unified Research Intelligence & Research Lifecycle Orchestration**

## Certification summary

- Backend regression: **132/132 passed** (run twice)
- WordPress/PHP contract and functional suites: **39/39 passed**
- Dedicated v8.0.0 lifecycle release contract: **88/88 passed**
- Focused v8.0.0 backend lifecycle tests: **4/4 passed**
- PHP syntax: **53 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **101 files passed**
- Python compilation: **passed**
- macOS release/push script syntax: **passed**
- Secret-pattern scan: **0 hits**
- Postgres migration count: **3 (unchanged)**

## Release boundaries verified

- Ancillary SQLite workspace schema advances to **18**.
- Production knowledge index remains `sc-research-librarian-knowledge-index/13.0`.
- Postgres schema remains **3**; no new Neon/Postgres migration is required.
- Connected Research API advances to `sc-connected-research-api/2.0`.
- Public research workspace advances to `sc-research-librarian-public-workspace/3.0`.
- Lifecycle stages are Frame, Discover, Evaluate, Organize, Collaborate, Synthesize, Promote, and Preserve.
- Readiness is deterministic and inspectable but never advances stages automatically.
- Lifecycle transitions require explicit human confirmation.
- Checkpoints are fingerprinted workflow snapshots, not evidence, publication, editorial approval, or truth judgments.
- Federated external discovery still requires explicit Save to My Library.
- Workspace promotion still requires explicit Workspace import.
- Historical v7.7.0 federated release evidence remains unchanged.

## Packaged artifact verification

The generated repository ZIP was re-extracted and tested independently:

- Full packaged backend regression: **132/132 passed**
- Packaged WordPress/PHP suites: **39/39 passed**
- Focused packaged v8 lifecycle backend suite: **4/4 passed**
- Packaged dedicated v8 lifecycle contract: **88/88 passed**
- Repository ZIP integrity: **passed**
- WordPress ZIP integrity: **passed**
- WordPress package boundary: **passed** (no backend, tests, Render config, or push tooling)
