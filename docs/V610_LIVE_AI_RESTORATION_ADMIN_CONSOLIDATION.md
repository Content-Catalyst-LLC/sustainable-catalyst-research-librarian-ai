# Research Librarian AI v6.1.0 — Live AI Restoration and Admin Consolidation

## Purpose

Version 6.1.0 restores the live AI experience as the primary public capability while preserving deterministic routing as a clearly labeled resilience layer. It also removes the long list of Research Librarian screens from WordPress Settings and consolidates administration under a dedicated top-level **Research Librarian AI** menu.

## Public AI experience

The assistant now exposes a public-safe operational status:

- **AI Online** after a successful provider request
- **AI Configured — Not Yet Tested** when credentials and a model are saved but no successful test is recorded
- **AI Temporarily Offline** after the latest provider request fails
- **AI Not Configured** when deterministic routing is the only active response path

The public status includes provider, model, semantic-retrieval mode, indexed-record count, last successful response, and fallback state without exposing keys or administrator-only error details.

## Administrator diagnostics

The dedicated **AI Provider** screen provides:

- provider and model configuration
- protected key replacement and clearing
- request timeout, output-token, temperature, and rate-limit controls
- semantic retrieval and embedding-model controls
- exact last provider error, HTTP status, and transport diagnostic
- provider connection test
- Gemini generate-content model discovery
- last success, failure, and latency records

A provider is not reported as online merely because a key is saved. A successful provider response is required.

## Country and Site Intelligence routing

The release adds an ISO-based country registry with 249 country records and aliases. Country detection runs before broad keyword routing.

Example:

```text
Question: What Sustainable Catalyst resources should I use to research climate and infrastructure in Pakistan?
Route ID: country-intelligence
Country: Pakistan
ISO alpha-3: PAK
Destination: /platform/site-intelligence/country-intelligence/?country=PAK
```

First-class Site Intelligence destinations include:

- Site Intelligence
- Country Intelligence
- Cross-Domain Comparison
- Dashboard Studio
- Sources and Methodology
- Public Observatories

Country and public-evidence routes can continue into Dashboard Studio, Workbench, or Decision Studio.

## Routing improvements

The deterministic router now:

1. detects a country entity;
2. applies approved editorial curation overrides;
3. scores all route-key matches instead of returning the first broad match;
4. prefers specific multi-word signals over generic terms;
5. uses Platform only when no specialized route wins.

The fallback remains useful during provider outages but is presented as fallback rather than as an AI answer.

## REST endpoints

Public:

```text
GET  /wp-json/sc-research-librarian-ai/v1/ai/status
POST /wp-json/sc-research-librarian-ai/v1/ask
```

Administrator-only:

```text
POST /wp-json/sc-research-librarian-ai/v1/ai/test
GET  /wp-json/sc-research-librarian-ai/v1/ai/models
```

The status endpoint is public-safe. Exact provider errors remain administrator-only.

## WordPress administration

The plugin now owns a top-level menu:

```text
Research Librarian AI
├── Dashboard
├── AI Provider
├── Index & Settings
├── Routes & Sources
├── Guided Paths
├── Feedback & Learning
├── Operations
└── Advanced
```

The Advanced screen consolidates recovery, security, observability, contracts, answer UX, query review, documentation, release audit, live QA, route quality, article maps, deep links, Feature Suggestions integration, demand intelligence, adaptive experiences, and closed-loop route improvement.

Legacy page slugs remain callable where existing module actions depend on them, but their menu entries are removed from WordPress Settings.

## Provider request behavior

Gemini generation uses:

- server-side `X-goog-api-key` authentication
- a model resource without a duplicated `models/` prefix
- `systemInstruction` for site-scoped policy and route context
- configurable request timeout
- structured HTTP and transport error records

OpenAI generation keeps the Responses API integration and adds configurable timeout plus structured provider diagnostics.

## Security and governance

- API keys remain server-side and are never sent to public JavaScript.
- Public errors are categorized without exposing provider response bodies or secrets.
- Exact errors are visible only to administrators.
- AI output remains advisory and site-scoped.
- Deterministic fallback does not claim to be AI.
- Country recognition does not create factual claims; it selects the appropriate Sustainable Catalyst evidence route.
- Workbench and Decision Studio retain their own responsible-use boundaries.

## Acceptance tests

Version 6.1.0 must pass:

- PHP syntax validation for all PHP files
- JavaScript syntax validation
- JSON validation for all data manifests
- collision-safe plugin bootstrap
- all four core public shortcodes registered
- all three AI status/test/model endpoints registered
- dedicated top-level admin menu registered
- legacy Settings menu entries removed
- Pakistan resolved to `country-intelligence` and `PAK`
- climate dashboard request resolved to `site-intelligence`
- archive integrity and secret scan
