# Research Librarian AI v9.1.0 Validation

Release: **v9.1.0 — Research Automation & Durable Workflow Engine**

## Results
- Python backend: **210 passed**
- Dedicated v9.1 workflow tests: **6 passed**
- WordPress/PHP contract suites: **52 passed**
- PHP syntax: **66 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **125 files passed**
- Shell syntax: **47 scripts passed**
- Python compileall: **passed**
- Secret-pattern scan: **passed**

## v9.1 coverage
- idempotent durable workflow creation
- Postgres workflow/event/checkpoint schema with SQLite local fallback
- dependency-aware stage scheduling
- idempotent v9.0 unified-runtime stage jobs
- pause/resume/cancel/retry controls
- explicit reviewer approvals for gated stages
- durable workflow-advance automation job
- append-only audit events
- reproducibility checkpoints
- no automatic Platform Core writes
- no automatic truth promotion
