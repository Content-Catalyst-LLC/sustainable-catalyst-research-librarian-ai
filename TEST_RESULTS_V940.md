# Research Librarian AI v9.4.0 validation

## Release gate

- Focused v9.4 scholarly publication tests: **7 passed**.
- Full Python backend regression: **230 passed**.
- WordPress/PHP contract suites: **55 passed**.
- PHP syntax: **69 files passed**.
- JavaScript syntax: **7 files passed**.
- JSON validation: **131 files passed**.
- Shell syntax: **53 scripts passed**.
- Python compileall: **passed**.
- Secret-pattern scan: **passed**.

## v9.4 integrity boundaries exercised

- Publication creation is idempotent and versioned.
- At least one human-declared author is required.
- External identifiers, including DOI, are recorded but never minted by Research Librarian.
- Accepted/published states require an explicit human decision reference; published state also requires a canonical URL.
- Citation exports preserve declared metadata and identifiers.
- Knowledge Library handoff preserves source/evidence/visual lineage and remains an explicit import-ready action.
- Frozen publication packages are content-hashed and do not imply peer-review certification, DOI registration, Core promotion, or truth determination.
- `scholarly-publication-package` is registered with the durable async runtime.

## Packaged-artifact smoke test

- Extracted repository ZIP: **230/230 Python tests passed**.
- Extracted repository ZIP: **55/55 PHP contract suites passed**.
- Packaged Git/tag script: shell syntax passed.
- Packaged Contabo deployer: shell syntax passed.
- Packaged identity: backend and WordPress report **9.4.0**.
- Packaged v9.4 API/job contract checks passed.
