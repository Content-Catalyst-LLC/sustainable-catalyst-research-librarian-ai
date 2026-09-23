# Research Librarian AI v8.4.0 — Advanced Retrieval & Reranking Engine

v8.4.0 upgrades Research Librarian retrieval from a single-query hybrid ranker to an inspectable research-grade orchestration layer while preserving the v8.2 Platform Core governance boundary and v8.3 durable Python processing runtime.

## Responsibility boundary

Research Librarian Python owns retrieval relevance: query planning, source filtering, lexical/semantic candidate discovery, rank fusion, reranking, duplicate suppression, and result diversity. Platform Core remains authoritative for governed evidence objects, claim/evidence relationships, provenance, lineage, research reasoning, reproducibility, statistical reasoning, and visual reasoning. Retrieval score is not an evidence-quality or truth score.

## Pipeline

1. Classify the research intent.
2. Build deterministic variants from the user's own query text only.
3. Apply typed post-type, source, series, record, URL-prefix, taxonomy, and modified-date filters before ranking.
4. Run the existing exact-title + BM25 + optional semantic + reciprocal-rank-fusion retriever over each bounded query variant.
5. Fuse candidate ranks across variants.
6. Apply transparent reranking using query coverage, title coverage, phrase alignment, multi-query consensus, and lexical/semantic support.
7. Suppress canonical-URL, content-hash, and high-similarity duplicate records.
8. Apply bounded maximum-marginal-relevance-style diversity selection.
9. Reassign stable SC citation labels after final selection.
10. Return a complete diagnostics object describing the plan and every selection stage.

## Query planning safety

The query planner is deterministic and non-generative. It derives quoted phrases, explicit comparison components, clauses, and stopword-reduced keyword forms from the user's query. It does not invent synonyms, entities, facts, or research assumptions.

## API

- `POST /v1/retrieval/plan` — inspect the deterministic query plan.
- `POST /v1/retrieve` — advanced retrieval is enabled by default and remains response-compatible with the prior endpoint.
- `POST /v1/retrieve/explain` — returns matches, evidence citations, filters, query runs, duplicate removals, diversity decisions, and ranking diagnostics.
- `GET|POST /v1/retrieval/config` — now includes the `advanced` tuning block.

The retrieval request remains backward-compatible. New optional fields are `include_semantic`, `advanced`, `max_queries`, `candidate_pool`, and `filters`.

## Filters

Filters can constrain `post_types`, `sources`, `series`, `record_ids`, `url_prefixes`, `taxonomies`, `modified_from_utc`, and `modified_to_utc`. Filtering occurs before candidate ranking and is surfaced in diagnostics.

## Configuration defaults

The `advanced-v8.4.0` profile enables multi-query retrieval, a bounded 20-record candidate pool, rank fusion, deterministic reranking, near-duplicate suppression, and diversity selection. Limits remain bounded by the existing maximum-source contract.

## Non-goals

v8.4.0 does not make evidence-quality judgments, create Core claims automatically, infer truth from ranking scores, or use an LLM to rewrite the user's search intent. Those boundaries are intentional.
