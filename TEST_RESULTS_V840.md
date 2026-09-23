# Research Librarian AI v8.4.0 — Test Results

Release: **8.4.0 — Advanced Retrieval & Reranking Engine**

## Validation summary

- Python backend: **151 tests passed**.
- Python compilation: **passed** for `backend/app` and `backend/tests`.
- WordPress/PHP contract and functional suite: **42 files passed**.
- PHP syntax: **56 files passed**.
- JavaScript syntax: **7 files passed**.
- JSON validation: **105 files passed**.
- Shell syntax: **27 scripts passed**.
- Secret-pattern scan: **passed**.

## v8.4.0 coverage

The v8.4 tests verify deterministic/non-generative query planning, comparative query decomposition, metadata/taxonomy/date filters, multi-query fusion, transparent reranking, exact-title priority, canonical-URL duplicate suppression, diversity selection, `/v1/retrieval/plan`, and the advanced `/v1/retrieve/explain` diagnostics contract.

## Regression coverage

The complete prior Research Librarian Python and WordPress suites remain green, including Platform Core v3.3+ integration, durable v8.3 asynchronous document processing, Postgres/Neon index durability, hybrid retrieval/citations, governance, Library context, persistent research state, Research Rooms, federation, Workspace promotion, and research lifecycle functionality.

## Governance boundary

v8.4.0 treats ranking as retrieval relevance only. It does not convert ranking scores into evidence quality or truth judgments. Platform Core remains the authoritative governed research/evidence/reasoning layer.
