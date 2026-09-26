# Research Librarian AI v10.3.0 — Validation Results

Release: **v10.3.0 — Evidence Search Strategy Engine**

## Source-tree release gate

- Python backend tests: **303 passed**
- Dedicated v10.3 tests: **9 passed**
- Current-release PHP/WordPress contract suites: **63 passed**
- PHP syntax: **78 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **149 files passed**
- Shell syntax: **71 scripts passed**
- Python compileall: **PASS**
- Secret-pattern scan: **PASS**

One historical `live-ai-provider-contract-test.php` suite is excluded from the current-release gate because it intentionally hard-codes the legacy 7.x plugin identity rather than the active release identity. It is retained in the repository for historical compatibility reference and is not rewritten to manufacture a current-version pass.

## v10.3 coverage

Validated behaviors include:
- deterministic search-strategy identity and durable persistence;
- v10.1 research-question and v10.2 methodology-plan integration;
- variable/population/context concept scaffolding;
- Knowledge Library and federated-discovery source targets;
- reproducible Boolean query construction and filters;
- inclusion/exclusion protocol criteria;
- evidence-requirement-to-query coverage mapping;
- idempotent concept, target, query, and execution-receipt handling;
- explicit human search-protocol approval before handoff;
- search handoff packets that do not execute or import automatically;
- Platform Core `evidence-search-protocol` candidates without automatic promotion;
- immutable strategy snapshots and the durable `evidence-search-strategy-snapshot` job;
- authenticated v10.3 API surface;
- v10 unified-environment binding as `evidence-search-strategy-plan`.

## Governance verified

- Knowledge Library remains responsible for source ingestion, parsing, indexing, retrieval, connectors, and document intelligence.
- Platform Core remains the governed evidence/research object authority.
- Search strategy coverage does not claim evidence sufficiency.
- Search receipts do not imply source acceptance or evidence validation.
- Human protocol approval is required before execution handoff.
- Automatic external search execution is disabled.
- Automatic source import is disabled.
- Automatic source acceptance is disabled.
- Automatic evidence-quality judgment is disabled.
- Automatic truth promotion is disabled.

Packaged-artifact smoke results are appended after exact ZIP validation.
