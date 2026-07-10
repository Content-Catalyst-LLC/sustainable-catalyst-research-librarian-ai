# Research Librarian v3.8.0 — Governance, Privacy Controls, and Retention Policies

v3.8.0 adds a governance layer around the Research Librarian's retrieval, session, feedback, handoff, and evaluation infrastructure.

## Goals

- Keep the Research Librarian useful without turning it into a surveillance product.
- Make public/admin boundaries explicit.
- Summarize retention targets for saved sessions, feedback, handoffs, and evaluation records.
- Provide governance export data for operational review.
- Allow redaction of question/note text in governance exports.
- Expose a public-safe governance summary shortcode.

## New endpoints

- `GET /wp-json/sc-research-librarian-ai/v1/governance/status`
- `GET /wp-json/sc-research-librarian-ai/v1/governance/export`
- `POST /wp-json/sc-research-librarian-ai/v1/governance/purge-expired`

## New shortcode

```text
[sc_research_librarian mode="governance-summary" title="Research Librarian Governance"]
```

## Enterprise relevance

This release is about operational maturity. Retrieval infrastructure needs more than embeddings and route confidence; it also needs governance surfaces that say what is logged, what is exported, what is admin-only, what is retained, and what is safe to show publicly.
