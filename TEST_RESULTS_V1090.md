# Research Librarian AI v10.9.0 — Validation Results

## Source-tree release gate

- Backend regression suite: **358 passed**
- Dedicated v10.9 Computational Research Planning suite: **10 passed**
- Active PHP/WordPress contract suites: **69 passed**
- Historical `live-ai-provider-contract-test.php`: intentionally excluded from the current-release identity gate, consistent with v10.3+ release practice.
- PHP syntax: **84 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **161 files passed**
- Shell syntax: **83 scripts passed**
- Python compileall: **PASS**
- Secret-pattern scan: **PASS**

## Dedicated v10.9 coverage

The dedicated suite verifies v10.8 dataset-fitness lineage, idempotent runtime-target and analysis-step registration, dataset/variable/runtime validation, dependency graphs, human step decisions, reproducibility requirements, blocking constraints, non-executing specialist-runtime handoffs, Platform Core candidates, immutable snapshots, authenticated APIs, durable async jobs, and unified-environment binding.

## Governance checks

- Human method/runtime approval required: **PASS**
- Upstream dataset fitness inherited rather than silently re-judged: **PASS**
- Automatic method selection disabled: **PASS**
- Automatic runtime selection disabled: **PASS**
- Automatic execution disabled: **PASS**
- Automatic result interpretation disabled: **PASS**
- Automatic truth promotion disabled: **PASS**
- Specialist runtimes retain execution authority: **PASS**
- Platform Core remains governed research-object authority: **PASS**

## Exact-package smoke tests

- Initial repository ZIP: **358/358 backend tests passed**
- Initial repository ZIP: **69/69 active PHP/WordPress contracts passed**
- Backend-only ZIP: **10/10 dedicated v10.9 tests passed**
- Backend-only ZIP identity: **10.9.0 PASS**
- WordPress ZIP identity: **10.9.0 PASS**
- WordPress ZIP PHP syntax: **14/14 files passed**
- Git push script syntax: **PASS**
- Contabo deployer syntax: **PASS**
- Final repository ZIP re-smoke: **PASS**
- SHA-256 manifest verification: **PASS**
