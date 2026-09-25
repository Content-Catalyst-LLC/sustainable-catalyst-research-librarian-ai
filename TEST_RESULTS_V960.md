# Research Librarian AI v9.6.0 Validation

Release: **v9.6.0 — AI-Aware Retrieval & Research Context Engineering**

## Final release gate

- Python backend: **244 passed**
- Dedicated v9.6 tests: **7 passed**
- PHP/WordPress contract suites: **57 passed**
- PHP syntax: **71 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **135 files passed**
- Shell syntax: **57 files passed**
- Python compileall: passed
- Secret-pattern scan: passed

## v9.6 integrity coverage

- deterministic context identity and immutable context hashes
- external Core model/prompt/version references preserved
- retrieved evidence receipts with rank/score/content lineage
- duplicate evidence references rejected within a run
- unknown contexts fail closed
- context lineage reconstructs exact retrieval runs
- immutable AI context snapshots
- durable `ai-research-context-snapshot` job
- authenticated v9.6 API surface
- no automatic model registration, training, grounding certification, or quality ranking

## Packaged repository smoke test

The extracted `sustainable-catalyst-research-librarian-ai-v9.6.0-repository.zip` independently passed:

- **244/244 Python tests**
- **57/57 PHP contract suites**
- v9.6 Git push script shell syntax
- v9.6 Contabo deployer shell syntax
- packaged v9.6 runtime identity/migration/job verification

## Release-engineering repair
- Corrected v9.6 Git preflight to retain v9.5 graph artifact names (`test_v950_*`, `V950_*`, v9.5 manifest/contract/release manifest) instead of incorrectly renaming them to v9.6.
- Corrected v9.6 commit/tag metadata to `AI-Aware Retrieval & Research Context Engineering`.
- Extended the v9.6 Contabo preflight to require both the v9.5 graph layer and v9.6 AI-context layer.
- Added explicit durable `ai-research-context-snapshot` verification and corrected the production success label.
- Both repaired shell scripts pass `bash -n`.
