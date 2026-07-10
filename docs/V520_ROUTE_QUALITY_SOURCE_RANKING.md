# Research Librarian v5.2.0 — Public Route Quality Tuning and Source Card Ranking

This release tunes the visitor-facing routing experience after v5.1.0 live UX QA. It improves how matched sources are ranked, how prompt intent is diagnosed, and how weak/mismatched routes are surfaced for review.

## Capabilities

- Route quality status
- Source-card ranking rules
- Dominant prompt signal detection
- Broad-route demotion for specialized questions
- Route repair suggestions
- Admin calibration dashboard
- Public-safe route quality summary
- Public-safe source ranking summary

## Endpoint inventory

```text
GET  /wp-json/sc-research-librarian-ai/v1/quality/status
POST /wp-json/sc-research-librarian-ai/v1/quality/rank
POST /wp-json/sc-research-librarian-ai/v1/quality/run-calibration
GET  /wp-json/sc-research-librarian-ai/v1/quality/export
```

## Shortcodes

```text
[sc_research_librarian_route_quality_summary title="Research Librarian Route Quality"]
[sc_research_librarian_source_ranking_summary title="Research Librarian Source Card Ranking"]
```

## Calibration prompts

The route-quality layer checks expected routing for Workbench, Decision Studio, Narrative Risk, Global Impact, Catalyst Data, Platform, and certification-boundary prompts.
