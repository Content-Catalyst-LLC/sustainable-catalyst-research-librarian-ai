# Research Librarian AI v10.4.0 — Validation Results

Release: **v10.4.0 — Systematic Review & Evidence Synthesis Intelligence**

## Source-tree release gate

- Python backend: **312 passed**
- Dedicated v10.4 tests: **9 passed**
- PHP/WordPress current-release contract suites: **64 passed**
- Historical `live-ai-provider-contract-test.php`: intentionally excluded from the current-release identity gate, consistent with the v10.3 release process.
- PHP syntax: **79 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **151 files passed**
- Shell syntax: **73 scripts passed**
- Python compileall: **PASS**
- Secret-pattern scan: **PASS**

## v10.4 coverage

Validated behaviors include search-protocol inheritance, deterministic candidate registration, reviewer-attributed title/abstract and full-text screening, review-flow accounting, structured study extraction, source-locator provenance, reviewer-recorded risk-of-bias domains, reviewer-recorded evidence-certainty grades, synthesis planning, human approval gates, non-executing specialist-runtime handoffs, governed Platform Core candidate preparation, immutable snapshots, durable snapshot jobs, authenticated APIs, and v10 unified-environment bindings.

## Governance verified

- Human screening decisions remain explicit and attributable.
- Risk-of-bias judgments are not inferred automatically.
- Evidence-certainty grades are not assigned automatically.
- Meta-analysis or other synthesis computation is not executed automatically.
- Knowledge Library remains source-ingestion/retrieval authority.
- Platform Core remains governed research/evidence object authority.
- Automatic truth promotion remains disabled.

## Packaged artifact smoke

- Extracted repository ZIP: **312/312 Python tests passed**.
- Extracted repository ZIP: **64/64 current-release PHP/WordPress contract suites passed**.
- Repository plugin/backend identity: **10.4.0 PASS**.
- Exact backend ZIP dedicated v10.4 suite: **9/9 passed**.
- Backend ZIP identity: **10.4.0 PASS**.
- WordPress ZIP plugin identity: **10.4.0 PASS**.
- WordPress ZIP PHP syntax: **14 files passed**.
- Git push script shell syntax: **PASS**.
- Contabo deployer shell syntax: **PASS**.
- Final release bundle checksum verification: **PASS**.
