# Research Librarian AI v9.8.0 — Validation Results

Release: **v9.8.0 — AI Research Experiment Orchestration**

## Source validation

- Dedicated v9.8 backend tests: **8 passed**.
- Complete backend regression: **260 passed**.
- PHP/WordPress contract and functional suites: **59 passed**.
- PHP syntax checks: **73 files passed**.
- JavaScript syntax checks: **7 files passed**.
- JSON validation: **139 files passed**.
- Shell syntax checks: **61 files passed**.
- Python `compileall`: passed.
- Secret-pattern scan: passed.

## v9.8 integrity coverage

- Deterministic experiment identity and content hashing.
- Parameterized trials preserve external Core AI/model/dataset/runtime references.
- Execution handoffs are requests and never count as execution receipts.
- External run receipts preserve explicit queued/running/succeeded/failed/cancelled state without inferring success.
- v9.7 evaluation bindings require registered evaluations.
- Human-controlled experiment state transition rules are enforced.
- Experiment summaries remain descriptive and do not select/rank a winner.
- Immutable experiment snapshots and durable `ai-research-experiment-snapshot` jobs are active.
- Authenticated v9.8 API surface is registered.

## Governance

Research Librarian orchestrates AI research experiments but does not train models, execute specialist compute automatically, infer successful execution, select a best model, rank experiments, infer causality, or determine truth. Platform Core AI object references remain external and specialist execution remains in Workspace, Research Lab, Workbench, or an explicitly declared external runtime.

## Packaged-artifact smoke tests

- Extracted repository ZIP: **260/260 Python tests passed**.
- Extracted repository ZIP: **59/59 PHP/WordPress contract suites passed**.
- Extracted repository ZIP: v9.8 plugin/backend identity and both release scripts verified.
- Exact backend ZIP: **8/8 dedicated v9.8 tests passed**.
- Exact WordPress ZIP: plugin identity and PHP syntax verified.
