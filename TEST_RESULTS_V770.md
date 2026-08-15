# Research Librarian AI v7.7.0 — Certification Results

Release: **v7.7.0 — Global Library Discovery & Federated Research**

## Automated regression

- Backend tests from repository root: **128/128 passed**
- Backend tests from `backend/`: **128/128 passed**
- WordPress contract/functional test files: **38/38 passed**
- Dedicated v7.7.0 federation contract: **98/98 checks passed**
- Focused v7.7.0 backend federation tests: **4/4 passed**

The v7.7.0 coverage includes fixed provider selection, OpenAlex/Crossref/Europe PMC/Open Library/arXiv normalization, DOI/ISBN/arXiv-aware deduplication, provider identity preservation, partial-provider failure state, persistent federated search snapshots, explicit Library import, project backup inclusion, owner boundaries, and non-HTTP(S) provider-link rejection.

## Static validation

- PHP syntax: **52 files passed**
- JavaScript syntax: **6 files passed**
- JSON parsing: **100 files passed**
- Python compilation: **passed**
- v7.7.0 macOS push-script shell syntax: **passed**
- Secret scan: **0 hits**

## Release boundaries

- Research Librarian AI: **7.7.0**
- Connected Research API: **sc-connected-research-api/1.6**
- Public workspace: **sc-research-librarian-public-workspace/2.6**
- Ancillary SQLite: **schema 17**
- Durable knowledge index: **sc-research-librarian-knowledge-index/13.0**
- **No Neon/Postgres knowledge-index migration is required for v7.7.0.**

External discovery is not Sustainable Catalyst editorial material and is not verified evidence. Search terms are sent only to selected external providers. WordPress user identity is not forwarded. Saving is explicit and creates a private `external-reference` Library object from the stored search snapshot.
