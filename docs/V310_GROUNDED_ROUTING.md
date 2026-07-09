# Research Librarian v3.1.0 — Grounded Routing and Source-Aware Recommendations

v3.1.0 makes the Research Librarian source-aware. Every route recommendation is built from the deterministic route map plus a Sustainable Catalyst source index.

## Added

- Grounding source index for Platform, Demos, Research Librarian, Decision Studio, Workbench, Knowledge Library, Methodology, Catalyst modules, Feature Suggestions, and GitHub.
- Confidence level, score, reason codes, ambiguity notes, and handoff suggestions.
- Route notes that export sources, confidence, handoffs, and reason codes.
- AI prompt context that provides Gemini/OpenAI with matched Sustainable Catalyst source records.
- Admin source index table.

## REST endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/sources
POST /wp-json/sc-research-librarian-ai/v1/grounded-route
POST /wp-json/sc-research-librarian-ai/v1/ask
GET  /wp-json/sc-research-librarian-ai/v1/health
```

## Scope

This is routing and retrieval infrastructure for Sustainable Catalyst. It does not provide professional advice, certification, compliance review, or unrestricted web research.
