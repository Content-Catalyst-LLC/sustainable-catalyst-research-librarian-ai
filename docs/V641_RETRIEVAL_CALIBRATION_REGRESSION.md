# Research Librarian AI v6.4.1 — Retrieval Calibration and Regression Patch

## Purpose

v6.4.1 turns the v6.4.0 hybrid retrieval engine into a measurable and adjustable production system. It adds persistent retrieval profiles, a bounded golden-query benchmark, near-duplicate-title protection, minimum-evidence gates, unsupported-answer detection, source weighting, exclusions, context budgets, and latency diagnostics.

The patch does not replace exact-title, BM25, semantic, or reciprocal-rank retrieval. It calibrates those signals, records the active configuration, and blocks weak or unsupported responses before public delivery.

## Persistent calibration profile

SQLite schema version 6 stores the active retrieval configuration in backend metadata. The profile includes:

- structural, lexical, semantic, and reciprocal-rank-fusion weights;
- the RRF constant;
- minimum evidence score and source-count requirements;
- optional lexical and semantic support thresholds;
- ambiguity margin and near-duplicate-title similarity threshold;
- unsupported-claim overlap and citation-coverage thresholds;
- maximum source, context, and passage budgets;
- post-type and source multipliers;
- record, post-type, source, and URL-prefix exclusions.

All values are bounded and sanitized by the backend. Updating the profile does not rebuild the knowledge index or embeddings.

## Retrieval calibration behavior

The calibrated ranking pipeline preserves exact canonical titles as the strongest result. For non-exact matches, the engine applies:

1. structural ranking over titles, slugs, headings, taxonomies, series, article maps, and parents;
2. BM25 lexical scoring over section-aware chunks;
3. optional semantic similarity over available embeddings;
4. reciprocal-rank fusion with administrator-controlled weights;
5. post-type and source multipliers;
6. explicit record and source exclusions;
7. minimum-evidence filtering and ambiguity checks.

Diagnostics report the active profile, excluded-record counts, score components, query intent, ambiguity candidates, estimated context size, and lexical, semantic, and total retrieval latency.

## Golden-query benchmark

The packaged benchmark contains bounded queries for exact titles, concepts, section matches, and platform routes. The benchmark endpoint compares lexical-only and calibrated hybrid retrieval using:

- hit at 1;
- hit at 3;
- mean reciprocal rank;
- missing expected records;
- ambiguous cases;
- per-case result ranks and latency.

Persisted benchmark runs are retained in SQLite with the profile name and metrics so ranking changes can be compared over time. The benchmark is diagnostic and does not automatically rewrite production weights.

## Near-duplicate-title protection

When similarly titled records rank within the configured ambiguity margin and exceed the title-similarity threshold, the engine marks the result ambiguous. The public answer path then asks which record should be prioritized rather than silently choosing among confusing titles.

Exact canonical-title matches remain eligible even when general score thresholds are raised, unless the record is explicitly excluded.

## Minimum-evidence gate

Before Gemini synthesis, the backend checks:

- whether at least the configured number of sources was retrieved;
- whether the best non-exact result clears the minimum score;
- whether optional lexical or semantic support floors are met;
- whether near-duplicate-title ambiguity remains unresolved.

A failed gate prevents AI generation and returns deterministic verified evidence or a focused clarification.

## Unsupported-answer detection

Citation verification now checks more than citation labels and URLs. It also evaluates:

- citation coverage across substantive paragraphs;
- token overlap between each claim and its cited evidence;
- numeric claims absent from the cited passages;
- unknown citation labels;
- unknown generated URLs;
- missing required citations.

Low-overlap paragraphs or unsupported numbers cause generated synthesis to be discarded. The public response falls back to verified evidence rather than returning persuasive but unsupported prose.

## API additions

- `GET /v1/retrieval/config`
- `POST /v1/retrieval/config`
- `POST /v1/retrieval/benchmark`
- `GET /v1/retrieval/benchmark/history`

The existing retrieval, ask, embedding, synchronization, recovery, snapshot, and maintenance endpoints remain compatible.

## WordPress administration

The Python Intelligence screen now includes controls for:

- profile name and ranking weights;
- RRF constant;
- minimum score, source count, and ambiguity margin;
- citation coverage and unsupported-claim overlap;
- maximum sources, context size, and passage size;
- post-type and source weights;
- excluded post types, sources, and URL prefixes;
- running the packaged retrieval benchmark;
- viewing the latest lexical and hybrid MRR.

Saving the screen applies the sanitized configuration to the backend. The operations export includes the active profile and benchmark history without exporting API keys.

## Compatibility and boundaries

- Upgrades in place from v6.4.0.
- SQLite schema version 6 is additive and preserves records, chunks, embeddings, snapshots, ledgers, and benchmark history.
- No paid vector database or persistent Render disk is required.
- Semantic retrieval remains optional.
- Benchmark results remain advisory and require human review before weight changes.
- Exclusions affect retrieval but do not delete canonical WordPress content.
- The black-and-green question field and light answer/evidence cards remain unchanged.
