# Research Librarian AI v11.0.0 — Validation Report

## Source-tree gates

- Backend regression suite: **368/368 passed**.
- Dedicated v11.0 Research Program Intelligence suite: **10/10 passed**.
- Active PHP/WordPress contract suites: **70/70 passed**.
- Historical `live-ai-provider-contract-test.php` remains excluded from the current-release identity gate because it intentionally preserves an older provider/plugin identity contract.
- PHP syntax: **85 files passed**.
- JavaScript syntax: **7 files passed**.
- JSON parsing: **163 files passed**.
- Shell syntax: **86 scripts passed**.
- Python compileall: **PASS**.
- Secret-pattern scan: **PASS**.

## v11.0 coverage

The dedicated suite verifies computational-plan lineage, research-program creation, idempotent workstreams and component bindings, milestone dependency graphs, explicit human milestone decisions, program approval/readiness, deliverables, blocking constraints, descriptive portfolio summaries, non-writing handoffs, Platform Core candidates without promotion, immutable snapshots, authenticated APIs, durable snapshot jobs, fail-closed unknown computational plans, and unified-environment `research-program` binding.

## Governance gates

Verified as explicit and disabled-by-default where applicable:
- automatic research prioritization: false
- automatic resource allocation: false
- automatic milestone completion: false
- automatic scientific judgment: false
- automatic execution: false
- automatic truth promotion: false
- component authority remains with source systems
- specialist runtimes retain execution authority
- Platform Core remains governed research-object authority

## Exact-package smoke

- Extracted repository ZIP: **368/368 backend tests passed**.
- Extracted repository ZIP: **70/70 active PHP/WordPress contracts passed**.
- Extracted backend ZIP: **10/10 dedicated v11.0 tests passed**.
- Extracted backend ZIP identity: **11.0.0 PASS**.
- Extracted WordPress ZIP identity: **11.0.0 PASS**.
- Extracted WordPress ZIP PHP syntax: **14/14 passed**.
- Push script shell syntax: **PASS**.
- Contabo deployer shell syntax: **PASS**.

Final repository ZIP re-smoke after embedding this report: **368/368 backend tests and 70/70 active PHP/WordPress contracts passed**.
