# Research Librarian AI v8.7.0 — Validation Results

## Release

**Version:** 8.7.0  
**Release:** Core Evidence Bridge

## Functional scope validated

- Canonical Research Librarian sources promote to governed Platform Core source snapshots.
- Passage-level evidence promotes only after the corresponding source snapshot is synchronized.
- Citation-only source stubs fail closed and cannot be promoted as evidence-bearing snapshots.
- Evidence promotion defaults to `neutral`, `unreviewed`, and no inferred confidence.
- No automatic claim creation, claim stance inference, truth judgment, or confidence inference is performed by the Librarian bridge.
- Librarian↔Core bindings are durable and immutable after synchronization.
- Existing v8.3 durable jobs, v8.4 retrieval, v8.5 document intelligence, and v8.6 source-identity functionality remain covered by regression tests.

## Working-tree validation

- Python backend: **171 passed**
- WordPress contract/functional suites: **45 passed**
- PHP syntax: **59 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **111 files passed**
- Shell syntax: **33 scripts passed**
- Python bytecode compilation: **PASS**
- Release secret scan: **PASS**
- v8.7 push/deployment script syntax: **PASS**

## Packaged repository smoke validation

- Repository ZIP independently extracted: **PASS**
- Python backend from packaged repository: **171 passed**
- WordPress contract/functional suites from packaged repository: **45 passed**
- Packaged release identity / v8.7 bridge presence: **PASS**
- ZIP integrity checks: **PASS**
