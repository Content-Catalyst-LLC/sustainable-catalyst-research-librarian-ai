# Sustainable Catalyst Research Librarian AI v6.4.0

## Hybrid Retrieval and Citation Engine

Research Librarian AI is the site-scoped discovery and research-guidance layer for Sustainable Catalyst. WordPress remains the canonical publishing and recovery source. The FastAPI service builds a durable SQLite retrieval index, ranks exact titles and article sections, optionally adds Gemini semantic similarity, and permits generated synthesis only when citations verify against synchronized evidence.

### v6.4.0 highlights

- Exact canonical titles remain the strongest retrieval signal.
- Public records are divided into deterministic, heading-aware chunks.
- PDF and document sections can retain page numbers.
- BM25 ranks query terms against article sections rather than only entire records.
- Optional Gemini embeddings are generated through bounded, resumable batches.
- Structural, lexical, semantic, relationship, and route signals are combined with reciprocal-rank fusion.
- Every source can include an evidence ID, citation label, section, page, supporting passage, retrieval reasons, and score diagnostics.
- Gemini is instructed to use only supplied `[SC#]` evidence labels.
- Unknown citation labels and generated URLs are rejected.
- A deterministic evidence summary remains available when Gemini, embeddings, or citation verification are unavailable.
- The restart-safe SQLite index, WordPress snapshots, cold-start recovery, bounded retries, stalled-job repair, and transient-notice suppression from v6.3.x remain active.
- The public black-and-green question field remains paired with light answer and source cards.

## Retrieval sequence

1. WordPress synchronizes canonical records, headings, structured sections, page metadata, taxonomies, and relationships.
2. FastAPI creates deterministic chunks and stores them in SQLite schema version 5.
3. Exact-title and structural ranking runs first.
4. BM25 ranks matching chunks.
5. Semantic similarity participates when verified embeddings exist.
6. Reciprocal-rank fusion combines the independent rankings.
7. Retrieved evidence is supplied to Gemini with fixed citation labels.
8. The generated answer is verified before release; otherwise deterministic fallback is used.

## Administration

Open **Research Librarian AI → Python Intelligence** to:

- test the backend;
- run a transactional full synchronization;
- process incremental editorial changes;
- inspect record, chunk, and semantic-coverage totals;
- process a bounded embedding batch;
- validate and create WordPress snapshots;
- recover an empty backend;
- repair stalled jobs;
- roll back a verified runtime snapshot;
- export synchronization and recovery diagnostics.

Lexical and exact-title retrieval work immediately after synchronization. Repeatedly use **Process Embedding Batch** to increase semantic coverage; a paid vector database is not required.

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

The Render blueprint pins Python 3.12.12. Required production secrets are `SC_RL_BACKEND_API_KEY` and `SC_RL_GEMINI_API_KEY`.

## Release documentation

- `docs/V640_HYBRID_RETRIEVAL_CITATION_ENGINE.md`
- `docs/V631_COLD_START_RECOVERY_HARDENING.md`
- `docs/V630_DURABLE_KNOWLEDGE_INDEX_SYNC_LEDGER_RECOVERY.md`
- `docs/INSTALL.md`
- `docs/ROADMAP.md`

## Current API additions

```text
GET  /v1/knowledge/embeddings/status
POST /v1/knowledge/embeddings/process
POST /v1/retrieve
POST /v1/retrieve/explain
```

Existing health, startup, status, synchronization, manifest, snapshot, maintenance, rollback, related-title, and ask endpoints remain available.

## License

MIT
