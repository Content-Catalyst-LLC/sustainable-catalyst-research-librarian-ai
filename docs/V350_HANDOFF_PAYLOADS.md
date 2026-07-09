# v3.5.0 — Workbench and Decision Studio Handoff Payloads

This release turns Research Librarian routing into structured downstream handoffs.

## Handoff targets

- Workbench: formulas, graphing, model inspection, unit-aware calculations, engineering notes, and exportable analytical reports.
- Decision Studio: Decision Packet seeds, artifact slots, source ledger seeds, assumption register seeds, four-pillar review placeholders, readiness and audit context.
- Module artifact: Canvas, Data, Analytics R, Global Impact, Narrative Risk, Finance, and Grit field recommendations.
- Feature Suggestions: missing or unsupported capability capture.
- Knowledge route: broad research/navigation follow-up.

## New endpoints

- `GET /wp-json/sc-research-librarian-ai/v1/handoff/schema`
- `POST /wp-json/sc-research-librarian-ai/v1/handoff/prepare`
- `GET /wp-json/sc-research-librarian-ai/v1/handoff/logs`
- `GET /wp-json/sc-research-librarian-ai/v1/handoff/export`

## Public shortcode

`[sc_research_librarian mode="handoff-summary" title="Research Librarian Handoff Layer"]`
