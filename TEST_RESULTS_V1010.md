# Research Librarian AI v10.1.0 — Validation Results

Release: **v10.1.0 — Research Question & Hypothesis Intelligence**

## Release gate

- Python backend tests: **285 passed**
- Dedicated v10.1 tests: **9 passed**
- PHP/WordPress contract suites: **62 passed**
- PHP syntax: **76 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **145 files passed**
- Shell syntax: **67 scripts passed**
- Python compileall: **PASS**
- Secret-pattern scan: **PASS**

## v10.1 coverage

Validated behaviors include deterministic research-question plan creation, structured scope/construct/variable modeling, candidate subquestion generation, hypothesis scaffolding only for hypothesis-relevant designs with explicit driver/outcome roles, evidence requirements, assumptions and falsification criteria, idempotent additions, human review state, structural readiness distinct from approval, Platform Core candidate packets without promotion, immutable snapshots, durable snapshot jobs, authenticated v10.1 API routes, and v10.0 unified-environment binding through `research-question-plan`.

## Governance verified

- Research Librarian owns question structuring and research-planning intelligence.
- Platform Core remains the governed authority for canonical research-question/hypothesis objects after explicit promotion.
- Candidate hypotheses are not accepted as scientific findings.
- Causality is not inferred automatically.
- Automatic truth promotion is disabled.
- Automatic Core writes are disabled.
- Human scholarly judgment and approval are preserved.
- Specialist computation remains delegated to the appropriate runtime/application.

Packaged-artifact smoke results are appended after repository/backend/WordPress package verification.

## Packaged artifact smoke

- Extracted repository ZIP: **285/285 Python tests passed**.
- Extracted repository ZIP: **62/62 PHP/WordPress contract suites passed**.
- Repository plugin/backend identity: **10.1.0 PASS**.
- Git push script shell syntax: **PASS**.
- Contabo deployer shell syntax: **PASS**.
- Exact backend ZIP dedicated v10.1 suite: **9/9 passed** with the backend package root on `PYTHONPATH`, matching its application import layout.
- Backend ZIP identity: **10.1.0 PASS**.
- WordPress ZIP plugin identity: **10.1.0 PASS**.
- WordPress ZIP PHP syntax: **14 files passed**.
- Release bundle SHA-256 verification: **PASS**.
- Release bundle flat-root/deploy layout: **PASS**.
