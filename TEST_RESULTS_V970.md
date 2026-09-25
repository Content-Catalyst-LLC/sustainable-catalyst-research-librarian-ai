# Research Librarian AI v9.7.0 Validation

Release: **v9.7.0 — RAG Evaluation & Evidence-Grounding Framework**

## Final release gate

- Python backend: **252 passed**
- Dedicated v9.7 tests: **8 passed**
- PHP/WordPress contract suites: **58 passed**
- PHP syntax: **72 files passed**
- JavaScript syntax: **7 files passed**
- JSON validation: **137 files passed**
- Shell syntax: **59 files passed**
- Python compileall: passed
- Secret-pattern scan: passed

## v9.7 integrity coverage

- deterministic evaluation identity linked to immutable v9.6 context hashes
- retrieval-run ownership validation against the selected AI research context
- precision@k, recall@k, reciprocal rank, and nDCG@k from declared relevance sets
- explicit human claim-grounding assessments
- explicit human citation-correctness assessments
- descriptive unsupported/conflicting claim and citation rates
- latency/token/cost metadata retained without composite quality scoring
- side-by-side evaluation comparison without ranking or winner selection
- immutable evaluation snapshots
- durable `rag-evaluation-snapshot` job
- authenticated v9.7 API surface
- no automatic truth judgment, model ranking, quality grade, or claim acceptance

## Packaged repository smoke test

The extracted `sustainable-catalyst-research-librarian-ai-v9.7.0-repository.zip` independently passed:

- **252/252 Python tests**
- **58/58 PHP contract suites**
- v9.7 Git push script shell syntax
- v9.7 Contabo deployer shell syntax
- packaged v9.7 runtime identity, migration, and durable-job verification

The exact backend ZIP also passed the dedicated **8/8 v9.7 tests** after extraction.
