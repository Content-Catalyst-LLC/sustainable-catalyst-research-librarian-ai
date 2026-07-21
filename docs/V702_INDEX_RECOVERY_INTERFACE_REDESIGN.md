# Research Librarian AI v7.0.2

## Knowledge Index Recovery and Interface Redesign

v7.0.2 turns the Research Librarian administration experience into a four-stage readiness workflow: Python connection, WordPress source discovery, durable knowledge synchronization, and semantic indexing.

The release adds a single **Build Knowledge Index** operation that tests the authenticated backend, discovers eligible published content, performs a transactional sync, verifies that the Python runtime committed records, attempts snapshot recovery if the runtime remains empty, and starts a bounded resumable embedding queue.

Source discovery now includes registered content types that are public, publicly queryable, or published through a REST-and-rewrite document surface. This repairs the prior assumption that every public Sustainable Catalyst document product uses `public => true`.

The public workspace no longer exposes raw provider/model plumbing as its main status. It reports research-service availability, source-index updates, verified retrieval, and fallback availability in visitor-facing language.

Advanced calibration, maintenance, rollback, and transaction diagnostics remain available but are collapsed by default.
