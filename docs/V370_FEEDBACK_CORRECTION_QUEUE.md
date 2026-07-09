# Research Librarian v3.7.0 — Feedback, Correction Queue, and Knowledge Gap Triage

This release adds a human review layer on top of routing, retrieval, sessions, analytics, and handoff payloads.

## What changed

- Public feedback actions in the assistant UI: **This helped** and **Report issue**.
- Feedback records for helpful signals, wrong-route reports, missing-source notes, unclear answers, feature gaps, and knowledge gaps.
- Triage labels for positive signals, route-correction review, confidence review, knowledge-gap triage, and editorial review.
- Admin feedback dashboard with counts, recent records, top affected route, and triage status.
- Exportable feedback JSON for review and future route-map tuning.
- Feedback summary shortcode for non-sensitive status display.

## New REST endpoints

- `POST /wp-json/sc-research-librarian-ai/v1/feedback/submit`
- `GET /wp-json/sc-research-librarian-ai/v1/feedback/summary`
- `GET /wp-json/sc-research-librarian-ai/v1/feedback/logs`
- `GET /wp-json/sc-research-librarian-ai/v1/feedback/export`

## New shortcode

```text
[sc_research_librarian mode="feedback-summary" title="Research Librarian Feedback and Triage"]
```

## Why this matters

Enterprise-grade retrieval systems need a review loop. Retrieval quality improves when weak answers, missing sources, route mismatches, and repeated knowledge gaps are captured as structured review records instead of disappearing into chat history.
