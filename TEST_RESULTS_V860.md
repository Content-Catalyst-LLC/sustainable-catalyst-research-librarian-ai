# Research Librarian AI v8.6.0 validation

Release: **v8.6.0 — Source Identity, Deduplication & Citation Graph**

Validation completed against the v8.5.0 repository baseline plus the v8.6.0 changes.

## Release validation

- Python backend tests: **165 passed**
- WordPress contract/functional test files: **44 passed**
- PHP syntax: **58 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **109 files passed**
- Shell syntax: **31 files passed**
- Python compileall: **passed**
- Secret scan: **passed**

## v8.6-specific validation

- Stable DOI/arXiv/PMID/ISBN/URL normalization: passed
- Bibliographic fingerprint deduplication: passed
- Fail-closed conflicting identifier resolution: passed
- Citation stub creation and later hydration: passed
- Bibliography identifiers excluded from citing-work identity: passed
- Multiple source instances attached to one canonical work: passed
- Authenticated source identity API contract: passed
- Citation graph read contract: passed
- Durable `source-identity` job registration: passed
- Postgres migration contract `005_source_identity_citation_graph.sql`: passed
- Platform Core v3.3+ governance boundary preserved: passed

## Packaged-repository smoke validation

The generated repository ZIP was independently extracted and validated:

- Python backend tests from packaged ZIP: **165 passed**
- WordPress contract/functional tests from packaged ZIP: **44 passed**
- v8.6 push-script shell syntax: passed
- v8.6 Contabo deployer shell syntax: passed
- Packaged release/plugin/backend identity: passed
- ZIP integrity: passed for repository, backend, WordPress, and release bundle inputs
