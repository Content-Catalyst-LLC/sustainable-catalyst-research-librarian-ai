# v3.3.1 — Gemini Embedding Diagnostics and Request Format Fix

This build fixes the observability gap from v3.3.0 where embedding generation could fail with only the message `Some records failed to embed.`

## Purpose

The Research Librarian already had a healthy knowledge index and source-aware routing layer. v3.3.1 focuses on making the Gemini embedding layer diagnosable and easier to repair.

## Added

- Single-record embedding test.
- Admin diagnostics panel.
- Admin-only diagnostics JSON endpoint.
- Improved Gemini request body.
- API key sent in the `x-goog-api-key` header rather than query string.
- Model normalization for names with or without the `models/` prefix.
- Optional output dimensionality setting.
- Early-stop failure limit.
- Raw response excerpt for setup debugging.

## Admin workflow

1. Save settings.
2. Rebuild the Knowledge Index.
3. Set Embedding Source Limit to 1 or 5.
4. Click **Test Single Gemini Embedding**.
5. If the test passes, click **Generate Gemini Embeddings**.
6. Check `/wp-json/sc-research-librarian-ai/v1/retrieval/status`.

A healthy response should show `embedded_records` greater than 0 and `embedding_dimensions` greater than 0.

## Failure interpretation

- HTTP 401 / 403: API key or permission issue.
- HTTP 404: model name or model access issue.
- HTTP 429: quota or rate limit issue.
- HTTP 0: server transport/outbound request issue.
- Empty vector: response parsing or unexpected response shape.
