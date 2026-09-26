# Research Librarian AI v11.1.0 Validation

## Source tree
- Backend full regression suite: **378/378 passed**.
- Dedicated v11.1 Study Protocol & Preregistration suite: **10/10 passed**.
- Active PHP/WordPress current-release contracts: **71/71 passed**.
- Legacy `live-ai-provider-contract-test.php` remains excluded from the current-release identity gate under the established release policy.
- PHP syntax: **86 files**.
- JavaScript syntax: **7 files**.
- JSON validation: **165 files**.
- Shell syntax: **89 scripts** after release-script/root-deployer assembly.
- Python compileall: **PASS**.
- Secret-pattern scan: **PASS**.

## Exact package smoke
- Repository ZIP: **378/378 backend tests passed**.
- Repository ZIP: **71/71 active PHP contracts passed**.
- Backend ZIP: **10/10 dedicated v11.1 tests passed**.
- Backend ZIP identity: **11.1.0 PASS**.
- Backend capabilities: milestone **11.1**, automatic preregistration disabled.
- WordPress ZIP identity: **Version 11.1.0 / Stable tag 11.1.0 PASS**.
- WordPress ZIP PHP lint: **14/14 packaged PHP files PASS**.
- Git push script: shell syntax **PASS**.
- Contabo deployer: shell syntax **PASS**.

## Governance assertions
- Human preregistration approval remains required.
- The preregistration baseline is immutable once frozen.
- Later amendments are append-only and linked to the baseline snapshot hash.
- Deviations are disclosed records, not automatic invalidity judgments.
- No automatic hypothesis acceptance, method selection, preregistration, amendment acceptance, deviation judgment, execution, or truth promotion.
- Research Program Intelligence remains upstream program authority; specialist runtimes retain execution; Platform Core remains governed research-object authority.
