# Research Librarian v4.8.0 — Admin Query Review and Route Improvement Workflow

v4.8.0 adds a route-quality improvement layer for the Sustainable Catalyst Research Librarian.

## Purpose

The Research Librarian now has retrieval, embeddings, source cards, handoffs, guided paths, analytics, feedback, governance, maintenance, and security. The next operational need is a disciplined way to review failures and tune the routing system over time.

## What it does

- Ingests review candidates from feedback logs, evaluation failure logs, saved route sessions, and guided path logs.
- Creates admin-only review queue items with source, query, observed route, expected route, priority, and suggested action.
- Supports manual correction records through the review correction endpoint.
- Allows admins to mark items as reviewed, accepted, rejected, deferred, converted to curation, or converted to source updates.
- Exports review queue JSON for release review or offline analysis.

## REST endpoints

- `GET /wp-json/sc-research-librarian-ai/v1/review/status`
- `GET /wp-json/sc-research-librarian-ai/v1/review/queue`
- `POST /wp-json/sc-research-librarian-ai/v1/review/ingest`
- `POST /wp-json/sc-research-librarian-ai/v1/review/mark`
- `POST /wp-json/sc-research-librarian-ai/v1/review/correction`
- `GET /wp-json/sc-research-librarian-ai/v1/review/export`
- `POST /wp-json/sc-research-librarian-ai/v1/review/clear`

## Shortcodes

- `[sc_research_librarian mode="query-review" title="Research Librarian Query Review"]`
- `[sc_research_librarian_query_review_summary title="Research Librarian Query Review"]`
- `[sc_research_librarian_route_improvement_summary title="Research Librarian Route Improvement"]`

## Admin page

Go to **Settings → Research Librarian Query Review** and click **Ingest Review Candidates** after collecting user feedback, route sessions, guided paths, or retrieval evaluation results.
