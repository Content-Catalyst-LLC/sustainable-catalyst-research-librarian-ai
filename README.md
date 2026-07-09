# Sustainable Catalyst Research Librarian

Current release: **v4.6.0 — Public Answer UX, Source Cards, and Route Action Center**.

The Research Librarian is the source-aware routing, indexing, retrieval, handoff, governance, and operations layer for Sustainable Catalyst. It routes visitors to the right page, demo, article map, Workbench pathway, Decision Studio workflow, or feature suggestion route while preserving source context, confidence, feedback, governance, curation, and operations metadata.

## v4.6.0 focus

v4.6.0 upgrades the public assistant experience. The underlying retrieval system already supports source-aware routing, Gemini embeddings, evaluation, handoffs, sessions, feedback, governance, security, observability, curation, and integration contracts. This release makes the visitor-facing answer feel like a finished product by rendering route recommendations as structured cards instead of plain answer text alone.

## What changed

- Recommended route card with title, category, description, route link, and platform fit.
- Matched source cards with summaries, URLs, retrieval mode, and score metadata where available.
- Confidence badge with explanation, reason-code chips, and ambiguity notes.
- Route Action Center with open-route, Workbench/Decision Studio handoff, copy, download, session, and feedback actions.
- Low-confidence and no-source states that route users toward clarification or Feature Suggestions.
- Public-safe answer UX summary and admin export endpoints.

## New v4.6.0 shortcodes

```text
[sc_research_librarian mode="answer-ux" title="Research Librarian Public Answer UX"]
[sc_research_librarian_answer_ux_summary title="Research Librarian Public Answer UX"]
[sc_research_librarian_route_action_center_summary title="Research Librarian Route Action Center"]
```

## New v4.6.0 endpoints

```text
GET /wp-json/sc-research-librarian-ai/v1/answer-ux/status
GET /wp-json/sc-research-librarian-ai/v1/answer-ux/schema
GET /wp-json/sc-research-librarian-ai/v1/answer-ux/public-status
GET /wp-json/sc-research-librarian-ai/v1/answer-ux/export
GET /wp-json/sc-research-librarian-ai/v1/answer-ux/admin-export
```

## Installation

1. Upload and activate `sustainable-catalyst-research-librarian-ai-plugin-v4.6.0.zip`.
2. Confirm plugin settings are preserved.
3. Rebuild the knowledge index only if source content changed.
4. Regenerate embeddings only if the index changed.
5. Test the public shortcode and confirm answers show route cards, source cards, confidence, and actions.

## Boundary

Public answer UX is for navigation and routing. It does not certify claims, replace expert review, or provide legal, financial, medical, tax, engineering, compliance, assurance, ESG/SDG, or other regulated professional advice.
