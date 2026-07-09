# Sustainable Catalyst Research Librarian v3.3.1

**Gemini Embedding Diagnostics and Request Format Fix**

v3.3.1 is a diagnostic and reliability build for the Gemini retrieval backend. It keeps the v3.3.0 knowledge index and hybrid retrieval architecture, but improves the embedding request format, exposes clearer diagnostics, and adds a single-record test path before running a full embedding job.

## What changed in v3.3.1

- Uses the Gemini embedding endpoint with a server-side `x-goog-api-key` header.
- Normalizes model names so both `gemini-embedding-001` and `models/gemini-embedding-001` are handled safely.
- Sends `model`, `content`, and `embedContentConfig` in the embedding request body.
- Adds optional output dimensionality control.
- Adds an early-stop failure limit so broken setup does not repeatedly attempt hundreds of failed records.
- Adds a single-record Gemini embedding test button.
- Adds admin diagnostics for HTTP status, error code, first failed source, raw response excerpt, and recommended next step.
- Adds a diagnostics REST endpoint for logged-in administrators.

## New endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/retrieval/diagnostics
POST /wp-json/sc-research-librarian-ai/v1/retrieval/test-embedding
```

The diagnostics endpoint is admin-only and does not expose the API key.

## Recommended setup check

1. Save settings with Gemini as the AI provider.
2. Set Embeddings Provider to Gemini.
3. Use `gemini-embedding-001` as the embedding model.
4. Set Embedding Source Limit to 1 or 5 while testing.
5. Click **Test Single Gemini Embedding**.
6. If the test passes, click **Generate Gemini Embeddings**.

---

# Sustainable Catalyst Research Librarian v3.3.0

The Sustainable Catalyst Research Librarian is the routing, indexing, and retrieval layer for the Sustainable Catalyst platform. It helps visitors choose the right Sustainable Catalyst starting point: Knowledge Library, Platform, Platform Demos, Decision Studio, Workbench, Catalyst Canvas, Catalyst Data, Analytics R, Global Impact Catalyst, Narrative Risk, Catalyst Finance, Catalyst Grit, Methodology, Feature Suggestions, or GitHub repositories.

v3.3.0 adds a Gemini retrieval backend with embeddings on top of the v3.2.0 Knowledge Indexer. The system remains usable in deterministic keyword/source mode, but can now generate server-side Gemini embeddings for indexed Sustainable Catalyst records and use hybrid semantic + keyword retrieval for source-aware route recommendations.

## What it does

- Provides deterministic route recommendations with confidence, reason codes, source support, and handoffs.
- Maintains a curated route map and local knowledge index from seed records plus WordPress pages/posts.
- Supports optional Gemini or OpenAI generation while keeping answers scoped to Sustainable Catalyst.
- Adds optional Gemini embeddings for indexed records using `gemini-embedding-001` by default.
- Uses hybrid retrieval: route rules + keyword scoring + indexed metadata + semantic similarity when embeddings are available.
- Tracks embedded records, embedding model, last embedding run, and retrieval status.
- Exposes retrieval status/query endpoints plus index embedding endpoint.
- Produces exportable route notes and route JSON with matched source records and retrieval mode metadata.

## v3.3.0 endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/retrieval/status
POST /wp-json/sc-research-librarian-ai/v1/retrieval/query
POST /wp-json/sc-research-librarian-ai/v1/index/embed
```

Existing index endpoints remain:

```text
GET  /wp-json/sc-research-librarian-ai/v1/index/summary
GET  /wp-json/sc-research-librarian-ai/v1/index/records
POST /wp-json/sc-research-librarian-ai/v1/index/rebuild
GET  /wp-json/sc-research-librarian-ai/v1/index/export
```

Existing routing endpoints remain:

```text
POST /wp-json/sc-research-librarian-ai/v1/ask
GET  /wp-json/sc-research-librarian-ai/v1/routes
GET  /wp-json/sc-research-librarian-ai/v1/sources
POST /wp-json/sc-research-librarian-ai/v1/grounded-route
GET  /wp-json/sc-research-librarian-ai/v1/health
```

## Shortcodes

```text
[sustainable_catalyst_research_librarian_ai]
[sc_research_librarian title="Sustainable Catalyst Research Librarian"]
[sc_research_librarian mode="landing" title="Sustainable Catalyst Research Librarian"]
[sc_research_librarian mode="route-map" title="Research Librarian Route Map"]
[sc_research_librarian mode="index-summary" title="Research Librarian Knowledge Index"]
[sc_research_librarian mode="retrieval-status" title="Gemini Retrieval Backend"]
```

## Admin workflow

Go to **Settings → Research Librarian**.

Recommended setup:

1. Save a Gemini API key.
2. Set **Embeddings Provider** to `Gemini embeddings`.
3. Keep **Gemini Embedding Model** as `gemini-embedding-001` unless you intentionally change models.
4. Click **Rebuild Knowledge Index** after major site updates.
5. Click **Generate Gemini Embeddings** to embed indexed source records.
6. Test with the Research Librarian or `/retrieval/query` endpoint.

The admin page now includes:

- Knowledge Indexer and Crawl Dashboard
- Gemini retrieval status
- embedded record count
- embedding model and last embedding run
- index rebuild/reset/export controls
- Generate Gemini Embeddings action
- indexed source table with embedding status

## Boundaries

The Research Librarian is educational routing infrastructure. It does not provide legal, financial, medical, tax, engineering, compliance, assurance, ESG/SDG certification, or regulated-information advice.

MIT-licensed.
