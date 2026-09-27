# Research Librarian AI v11.5.0 Validation Results

## Source-tree validation
- Backend regression suite: **418/418 passed**
- Dedicated v11.5 reproduction/replication suite: **10/10 passed**
- Active WordPress/PHP contract suite: **75/75 passed**
- PHP lint: **90 files passed**
- JavaScript syntax: **7 files passed**
- JSON parse: **173 files passed**
- Shell syntax: **97 files passed**
- Python compileall: **PASS**
- Secret-pattern scan: **PASS**

`tests/live-ai-provider-contract-test.php` remains outside the active release-identity gate because it intentionally asserts a historical v7.x identity.

## v11.5 behavior verified
1. Study-protocol lineage is mandatory and validated fail-closed.
2. Statistical, causal, and simulation/model-study lineage is optional but validated for cross-layer consistency.
3. Reproduction attempts and replication studies remain distinct objects.
4. Environment fidelity and comparability criteria are explicit planning records, not inferred equivalence.
5. Deviations are recorded without automatic materiality judgment.
6. Execution receipts are provenance-bearing observations, not scholarly verdicts.
7. Reproduction/replication outcome assessments are explicitly human-authored and scope-bounded.
8. Human approval gates runtime handoffs; Research Librarian does not execute the work.
9. Platform Core candidates and immutable snapshots do not promote truth or generate replication verdicts.
10. Durable jobs, authenticated APIs, and unified-environment `reproduction-replication-plan` bindings are active.

## Governance
- automatic reproduction verdict: **disabled**
- automatic replication verdict: **disabled**
- automatic claim acceptance: **disabled**
- automatic causal inference: **disabled**
- automatic execution: **disabled**
- automatic truth promotion: **disabled**
- specialist runtimes own execution: **true**
- Platform Core remains governed research-object authority: **true**

## Exact-package smoke tests
- Repository ZIP: **418/418 backend tests passed**
- Repository ZIP: **75/75 active PHP contracts passed**
- Backend-only ZIP: **10/10 dedicated v11.5 tests passed** with `PYTHONPATH=.`
- Backend-only ZIP identity: **11.5.0**
- WordPress ZIP identity/stable tag: **11.5.0**
- WordPress ZIP PHP lint: **90/90 packaged PHP files passed**
- Final repository ZIP: **418/418 backend + 75/75 active PHP contracts passed** after embedding the package report
- Final release-bundle checksum verification: **PASS**
