# Sustainable Catalyst Research Librarian v3.6.0

**Saved Route Sessions and Admin Analytics**

v3.6.0 adds a saved-session and analytics layer on top of the v3.5.0 handoff payload system. The Research Librarian can now preserve useful route notes, summarize common routes and handoff targets, expose route-session exports, and provide lightweight admin analytics for improving retrieval quality and product routing.

## What changed in v3.6.0

- Added saved route sessions from public assistant results.
- Added Save session button to the assistant UI.
- Added session logs that preserve the question, recommended route, confidence, source count, handoff target, next step, and structured route note.
- Added admin route analytics: total sessions, unique routes, common handoff targets, confidence distribution, top route, top target, and recent saved sessions.
- Added public session and analytics summary shortcode modes.
- Added REST endpoints for saving sessions, exporting session logs, and reading analytics summaries.
- Added session log limit setting and admin clear/export actions.
- Preserved v3.5.0 Workbench and Decision Studio handoff payload behavior.

## New shortcodes

```text
[sc_research_librarian mode="session-summary" title="Research Librarian Route Sessions"]
[sc_research_librarian mode="analytics-summary" title="Research Librarian Route Analytics"]
```

## New endpoints

```text
POST /wp-json/sc-research-librarian-ai/v1/session/save
GET  /wp-json/sc-research-librarian-ai/v1/session/logs
GET  /wp-json/sc-research-librarian-ai/v1/session/export
GET  /wp-json/sc-research-librarian-ai/v1/analytics/summary
```

## Recommended workflow

1. Ask the Research Librarian a route question.
2. Review the recommended route, sources, confidence, and handoff payload.
3. Click **Save session** when the route is useful.
4. Use the admin analytics panel to see route patterns, handoff targets, confidence distribution, and recent sessions.
5. Export session analytics JSON when you want to review routing behavior outside WordPress.

---

# Sustainable Catalyst Research Librarian v3.4.0

**Gemini Embedding Diagnostics and Request Format Fix**

v3.4.0 is a diagnostic and reliability build for the Gemini retrieval backend. It keeps the v3.3.0 knowledge index and hybrid retrieval architecture, but improves the embedding request format, exposes clearer diagnostics, and adds a single-record test path before running a full embedding job.

## What changed in v3.4.0

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


## v3.4.0 Notes

This release adds a safer Gemini embedding queue with resumable batches, request delay controls, retry handling for rate limits, and saved-key diagnostics. For stable setup, test one embedding first, then run batches of 5, 10, 25, 50, and 100 before full coverage.


## v3.4.0 Gemini key persistence hotfix

v3.4.0 fixes the setup pattern where a Gemini key could pass a single embedding test and then fail during a later batch after settings were saved. API keys now use protected replacement fields, blank fields preserve the existing key, masked/autofilled/incomplete values are rejected, and diagnostics show saved-key and last-run fingerprints without exposing secrets.


## v3.4.0 — Retrieval Evaluation, Confidence Tuning, and Failure Logs

This release adds a reliability layer for the Research Librarian retrieval system. The plugin now includes a built-in evaluation suite for common Sustainable Catalyst routing prompts, expected-route comparison, confidence and source-coverage summaries, keyword/semantic score breakdowns, low-confidence warnings, route-mismatch labels, and exportable evaluation reports.

New admin tools:

- Run Retrieval Evaluation
- Clear Evaluation Logs
- Export Evaluation JSON
- View route accuracy, low-confidence cases, weak source matches, and quality labels
- Inspect per-case expected route, recommended route, confidence score, keyword score, semantic score, and top source

New endpoints:

- `GET /wp-json/sc-research-librarian-ai/v1/evaluation/suite`
- `POST /wp-json/sc-research-librarian-ai/v1/evaluation/run`
- `POST /wp-json/sc-research-librarian-ai/v1/evaluation/query`
- `GET /wp-json/sc-research-librarian-ai/v1/evaluation/logs`
- `GET /wp-json/sc-research-librarian-ai/v1/evaluation/export`

New shortcode:

- `[sc_research_librarian mode="evaluation-summary" title="Research Librarian Retrieval Evaluation"]`


## v3.5.0 — Workbench and Decision Studio Handoff Payloads

Research Librarian now turns route results into structured handoff payloads. A visitor question can produce a route note plus a machine-readable handoff object for:

- Sustainable Catalyst Workbench analysis tasks
- Sustainable Catalyst Decision Studio Decision Packet seeds
- Catalyst module artifact workflows
- Feature Suggestions for missing capabilities
- Knowledge-route follow-up when the request is still broad

New endpoints:

- `GET /wp-json/sc-research-librarian-ai/v1/handoff/schema`
- `POST /wp-json/sc-research-librarian-ai/v1/handoff/prepare`
- `GET /wp-json/sc-research-librarian-ai/v1/handoff/logs`
- `GET /wp-json/sc-research-librarian-ai/v1/handoff/export`

New shortcode:

`[sc_research_librarian mode="handoff-summary" title="Research Librarian Handoff Layer"]`


## v3.8.0 Feedback and Triage Layer

Research Librarian v3.8.0 adds a human review loop for retrieval quality. Visitors can mark a route as helpful or report an issue. Administrators can review wrong-route reports, missing-source notes, unclear answers, feature gaps, and knowledge gaps from a structured feedback dashboard.

New shortcode:

```text
[sc_research_librarian mode="feedback-summary" title="Research Librarian Feedback and Triage"]
```

New endpoints:

```text
POST /wp-json/sc-research-librarian-ai/v1/feedback/submit
GET  /wp-json/sc-research-librarian-ai/v1/feedback/summary
GET  /wp-json/sc-research-librarian-ai/v1/feedback/logs
GET  /wp-json/sc-research-librarian-ai/v1/feedback/export
```


## v3.8.0 Governance Layer

Adds governance, privacy, retention, and admin export controls for saved route sessions, feedback, handoffs, evaluation logs, retrieval status, and public-safe summary display.

## v3.9.0 — Scheduled Index Maintenance, Sitemap Sync, and Health Alerts

v3.9.0 adds the operational maintenance layer for the Research Librarian knowledge index. It can rebuild the index on a WordPress cron schedule, optionally include sitemap URLs in source coverage, expose index-health status, export maintenance JSON, and provide a public-safe maintenance summary shortcode.

New shortcode:

```text
[sc_research_librarian mode="maintenance-summary" title="Research Librarian Index Maintenance"]
```

New endpoints:

```text
GET  /wp-json/sc-research-librarian-ai/v1/maintenance/status
POST /wp-json/sc-research-librarian-ai/v1/maintenance/run
GET  /wp-json/sc-research-librarian-ai/v1/maintenance/export
```

Recommended first setup: enable scheduled maintenance daily, enable sitemap URLs if your sitemap is stable, leave automatic embedding after rebuild off until Gemini rate limits are confirmed.
