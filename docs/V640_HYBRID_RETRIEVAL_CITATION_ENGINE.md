# Research Librarian AI v6.4.0 — Hybrid Retrieval and Citation Engine

## Purpose

v6.4.0 moves Research Librarian from record-level keyword ranking to section-aware, auditable hybrid retrieval. It preserves exact-title lookup as the strongest signal, adds BM25 lexical retrieval over durable chunks, supports optional Gemini embeddings, combines independent rankings with reciprocal-rank fusion, and verifies every generated citation against synchronized evidence before an answer is returned.

The release remains free-tier compatible. WordPress is still the canonical publishing source, SQLite remains the recoverable runtime index, and semantic retrieval can be populated gradually in bounded batches. No paid vector database or persistent Render disk is required.

## Retrieval pipeline

1. **Canonical synchronization** — WordPress sends public records, headings, structured sections, page metadata, relationships, taxonomies, and content hashes. Section extraction respects the existing include-content setting and content-character budget.
2. **Section-aware chunking** — The backend creates deterministic chunks from structured sections, PDF pages, headings, summaries, and bounded content windows.
3. **Exact-title and structural ranking** — Exact canonical titles, slugs, article maps, series, headings, and taxonomies receive explicit priority.
4. **BM25 lexical ranking** — Query terms are ranked against section-level chunks rather than only whole records.
5. **Optional semantic ranking** — Gemini embeddings can be generated in resumable batches and compared with a query embedding when configured.
6. **Reciprocal-rank fusion** — Structural, lexical, and semantic result lists are combined without allowing semantic similarity to override an exact-title match.
7. **Evidence assembly** — Results carry an evidence identifier, canonical URL, section, page, passage, retrieval reasons, and scoring diagnostics.
8. **Citation-verified synthesis** — Gemini may synthesize only from supplied evidence labels such as `[SC1]`. Unknown labels and links are rejected.
9. **Deterministic fallback** — If generation is unavailable or citation verification fails, the service returns a source-backed evidence summary instead of an unsupported answer.

## Chunk and embedding persistence

SQLite schema version 5 adds:

- `retrieval_chunks` for deterministic section and page chunks;
- content hashes so unchanged chunks keep their existing embeddings;
- embedding model and vector storage;
- `embedding_runs` for bounded, resumable processing history;
- semantic coverage reporting in status and administration screens.

Every full synchronization, incremental update, migration, and rollback rebuilds the active chunk registry. Existing embeddings are retained only when both the deterministic chunk identifier and content hash still match.

## Citation contract

Every returned source can include:

- `evidence_id` and `citation_label`;
- record and chunk identifiers;
- canonical title and URL;
- section heading;
- PDF page number when available;
- supporting passage;
- lexical, semantic, structural, and fusion scores;
- retrieval reasons and record version.

The verifier rejects:

- evidence labels that were not supplied to the model;
- generated links outside the synchronized source set;
- generated answers with no evidence citations when citations are required.

A failed verification never silently passes through to the public interface.

## API additions

- `GET /v1/knowledge/embeddings/status`
- `POST /v1/knowledge/embeddings/process`
- `POST /v1/retrieve`
- `POST /v1/retrieve/explain`

The existing `/v1/ask`, `/status`, manifest, synchronization, snapshot, maintenance, and rollback contracts remain available.

## WordPress administration

The Python Intelligence screen now shows:

- indexed chunk count;
- embedded chunk count;
- semantic coverage percentage;
- active embedding model;
- a **Process Embedding Batch** action.

A full transactional synchronization should run before the first embedding batch. Embeddings can then be processed repeatedly until the desired coverage is reached. Lexical and exact-title retrieval remain operational at zero semantic coverage.

## Compatibility and boundaries

- Upgrades in place from v6.3.1.
- Retains SQLite durability, WordPress snapshots, cold-start recovery, stalled-job repair, retry controls, rate limits, and public endpoint diagnostics.
- Retains the black-and-green question field and light answer/evidence cards.
- Does not require semantic retrieval to answer questions.
- Does not permit Gemini to invent source URLs or cite evidence absent from the synchronized index.
- Does not turn Research Librarian into a general-purpose chatbot.
