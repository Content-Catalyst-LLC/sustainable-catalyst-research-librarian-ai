# Research Librarian AI v8.5.0 validation

Release: **v8.5.0 — Document Intelligence & Scholarly Parsing**

Validation completed against the v8.4.0 repository baseline plus the v8.5.0 changes.

- Python backend tests: **157 passed**.
- WordPress/PHP contract + functional tests: **43 passed**.
- PHP syntax: **57 files passed**.
- JavaScript syntax: **7 files passed**.
- JSON validation: **107 files passed**.
- Shell syntax: **29 scripts passed**.
- Python `compileall`: passed for backend application and tests.
- Secret-pattern scan: passed.
- PDF parser smoke: passed with `pypdf` using page metadata and explicit OCR boundary.
- Document intelligence integration: Markdown/HTML structure, references, citation mentions, identifiers, figures, tables, equations, section-aware chunks, sync API, and durable async enqueue all passed.

Governance verification: document parsing remains deterministic extraction, not a truth/evidence-quality judgment; Platform Core v3.3+ remains the governed evidence/reasoning/provenance authority.
