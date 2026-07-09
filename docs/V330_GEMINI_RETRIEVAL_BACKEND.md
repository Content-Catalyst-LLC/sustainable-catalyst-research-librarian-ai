# v3.3.0 — Gemini Retrieval Backend with Embeddings

v3.3.0 adds an optional semantic retrieval layer to the Research Librarian.

## Purpose

The Research Librarian should not rely only on generative AI text. It needs a source-aware retrieval layer that can match visitor questions to Sustainable Catalyst records, pages, modules, and handoff paths.

v3.3.0 keeps deterministic route rules and keyword matching, then adds optional Gemini embeddings for semantic source matching.

## Retrieval flow

```text
visitor question
→ deterministic route match
→ keyword/source search over the knowledge index
→ optional Gemini query embedding
→ cosine similarity against embedded source records
→ hybrid score
→ route confidence + source records + handoffs
→ optional Gemini/OpenAI answer with matched source context
→ exportable route note
```

## Admin setup

1. Go to Settings → Research Librarian.
2. Add the Gemini API key.
3. Select Gemini as AI Provider if desired.
4. Set Embeddings Provider to Gemini embeddings.
5. Keep Gemini Embedding Model as `gemini-embedding-001` unless deliberately changing models.
6. Click Rebuild Knowledge Index.
7. Click Generate Gemini Embeddings.
8. Test `/retrieval/status` and `/retrieval/query`.

## New endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/retrieval/status
POST /wp-json/sc-research-librarian-ai/v1/retrieval/query
POST /wp-json/sc-research-librarian-ai/v1/index/embed
```

## What is stored

Embeddings are generated server-side and stored in the WordPress knowledge index option with record metadata:

```text
embedding
embedding_model
embedding_updated_utc
```

The plugin also stores an embedding status option with the last embedding run, failure counts, and last error.

## Fallback behavior

If Gemini embeddings are disabled, missing, or fail, the plugin uses keyword/source routing and deterministic route rules. The Research Librarian remains usable without embeddings.

## Boundary

This is retrieval infrastructure, not truth verification or professional advice. It improves source matching over the Sustainable Catalyst site map; it does not certify content, validate external facts, or replace expert review.
