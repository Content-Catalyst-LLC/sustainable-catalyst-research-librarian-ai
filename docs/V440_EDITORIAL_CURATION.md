# Research Librarian v4.4.0 — Editorial Curation, Route Overrides, and Source Weighting

v4.4.0 adds an editorial curation layer for Sustainable Catalyst Research Librarian.

## Purpose

The retrieval stack now has keyword matching, Gemini embeddings, evaluation tests, handoff payloads, feedback logs, governance, maintenance, security, and observability. The missing operational layer was editorial control: a way to deliberately steer canonical routes and source priority when retrieval scores are technically plausible but not editorially preferred.

## What this release adds

- Route override rules
- Source weighting rules
- Boundary pattern rules
- Admin curation dashboard
- Public-safe curation summary
- Admin-only curation export
- Curation test endpoint
- Routing integration before deterministic fallback
- Source priority integration before hybrid score sorting

## Route overrides

Route overrides let an administrator define trigger phrases and a canonical route. Example: calculation, graphing, symbolic math, and formula questions should route to Workbench even when other sources also match.

## Source weighting

Source weights boost canonical records during source ranking. Example: if the route is Workbench, boost indexed source records whose URL contains `workbench`.

## Boundary patterns

Boundary patterns route regulated-advice and certification prompts to methodology/boundary pages rather than letting the assistant over-answer.

## Public safety

The public shortcode exposes counts only. Full curation rules, notes, exports, and tests are admin-only.

## Shortcodes

```text
[sc_research_librarian mode="curation-summary" title="Research Librarian Editorial Curation"]
[sc_research_librarian_curation_summary title="Research Librarian Editorial Curation"]
[sc_research_librarian_route_overrides_summary title="Research Librarian Route Overrides"]
```

## REST endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/curation/status
GET  /wp-json/sc-research-librarian-ai/v1/curation/rules
GET  /wp-json/sc-research-librarian-ai/v1/curation/export
POST /wp-json/sc-research-librarian-ai/v1/curation/test
POST /wp-json/sc-research-librarian-ai/v1/curation/reset-defaults
```

## Admin page

```text
Settings → Research Librarian Curation
```
