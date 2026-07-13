# Sustainable Catalyst Research Librarian AI v6.4.1

## Retrieval Calibration and Regression Patch

Research Librarian AI is the site-scoped discovery and research-guidance layer for Sustainable Catalyst. WordPress remains the canonical publishing and recovery source. FastAPI provides a restart-safe SQLite retrieval index, exact-title and section-aware BM25 ranking, optional Gemini semantic similarity, calibrated reciprocal-rank fusion, verified citations, and deterministic evidence fallback.

### v6.4.1 highlights

- Persists a sanitized retrieval profile in SQLite schema version 6.
- Exposes structural, lexical, semantic, and reciprocal-rank-fusion weights.
- Adds post-type and source weighting plus record, source, post-type, and URL-prefix exclusions.
- Adds a packaged golden-query benchmark that compares lexical-only and calibrated hybrid retrieval.
- Persists benchmark history with hit-at-1, hit-at-3, mean reciprocal rank, ambiguity, missing-result, and latency metrics.
- Detects confusing and near-duplicate titles and requests clarification instead of silently choosing.
- Blocks AI synthesis when minimum source, score, lexical, semantic, or ambiguity requirements are not met.
- Rejects unsupported paragraphs, unsupported numeric claims, unknown evidence labels, and unknown generated URLs.
- Reports active profile, score components, excluded-record counts, context estimates, and retrieval latency.
- Preserves heading-aware chunks, PDF page evidence, resumable embeddings, durable snapshots, cold-start recovery, and the black-and-green prompt with light answer cards.

## Retrieval sequence

1. WordPress synchronizes canonical records, headings, sections, page metadata, taxonomies, and relationships.
2. FastAPI creates deterministic chunks and stores them in SQLite.
3. Exclusions and source/post-type weighting are applied.
4. Exact-title and structural ranking runs first.
5. BM25 ranks matching chunks.
6. Semantic similarity participates when verified embeddings exist.
7. Reciprocal-rank fusion combines the independent rankings using the active calibration profile.
8. The minimum-evidence gate decides whether AI synthesis is permitted.
9. Generated claims, citations, numbers, and URLs are verified; otherwise deterministic evidence fallback is returned.

## Administration

Open **Research Librarian AI → Python Intelligence** to:

- synchronize and recover the durable index;
- inspect records, chunks, embeddings, snapshots, retries, and staging jobs;
- set retrieval weights, thresholds, context limits, source multipliers, and exclusions;
- run the retrieval benchmark and compare lexical and hybrid MRR;
- process bounded embedding batches;
- validate snapshots, repair stalled jobs, roll back runtime snapshots, and export operations diagnostics.

## Public shortcodes

```text
[sustainable_catalyst_research_librarian_ai]
[sc_research_librarian]
[sc_research_guidance_platform]
[sc_research_guidance_journey]
```

Historical shortcode modes remain available for route maps, index summaries, guided paths, evaluation summaries, handoff summaries, and operations views.

## Backend development

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

The Render blueprint pins Python 3.12.12. Required production secrets are `SC_RL_BACKEND_API_KEY` and `SC_RL_GEMINI_API_KEY`. A paid vector database or persistent Render disk is not required.

## Release documentation

- `docs/V641_RETRIEVAL_CALIBRATION_REGRESSION.md`
- `docs/V640_HYBRID_RETRIEVAL_CITATION_ENGINE.md`
- `docs/V631_COLD_START_RECOVERY_HARDENING.md`
- `docs/V630_DURABLE_KNOWLEDGE_INDEX_SYNC_LEDGER_RECOVERY.md`
- `docs/INSTALL.md`
- `docs/ROADMAP.md`

## v6.4.1 API additions

```text
GET  /v1/retrieval/config
POST /v1/retrieval/config
POST /v1/retrieval/benchmark
GET  /v1/retrieval/benchmark/history
```

Existing health, startup, status, synchronization, manifest, snapshot, maintenance, rollback, embedding, retrieval, related-title, and ask endpoints remain available.

## License

MIT
