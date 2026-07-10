# Research Librarian v3.4.0 — Retrieval Evaluation, Confidence Tuning, and Failure Logs

v3.4.0 adds a reliability and evaluation layer to the Research Librarian.

## Purpose

The Research Librarian can now test whether it routes standard Sustainable Catalyst questions to the expected product, module, or knowledge path. This is the layer that turns retrieval from a working feature into a measurable system.

## What it evaluates

- Expected route vs recommended route
- Confidence level and confidence score
- Source count and weak source coverage
- Top source keyword score
- Top source semantic score
- Retrieval mode
- Score margin between top source matches
- Low-confidence and route-mismatch warnings

## Admin workflow

1. Rebuild Knowledge Index.
2. Generate Gemini Embeddings.
3. Run Retrieval Evaluation.
4. Review accuracy, low-confidence cases, weak source matches, and route mismatches.
5. Export Evaluation JSON when needed.

## Endpoints

- `GET /wp-json/sc-research-librarian-ai/v1/evaluation/suite`
- `POST /wp-json/sc-research-librarian-ai/v1/evaluation/run`
- `POST /wp-json/sc-research-librarian-ai/v1/evaluation/query`
- `GET /wp-json/sc-research-librarian-ai/v1/evaluation/logs`
- `GET /wp-json/sc-research-librarian-ai/v1/evaluation/export`

## Shortcode

`[sc_research_librarian mode="evaluation-summary" title="Research Librarian Retrieval Evaluation"]`

## Notes

The suite is intentionally small and platform-specific. It is meant to catch obvious routing failures after index, route-map, embedding, or confidence-weight changes.
