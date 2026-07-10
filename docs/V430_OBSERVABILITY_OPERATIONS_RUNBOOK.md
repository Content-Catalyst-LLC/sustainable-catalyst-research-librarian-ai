# Research Librarian v4.3.0 — Observability, Operations Runbook, and Production Checks

This release adds an operations layer above the existing Research Librarian infrastructure. It does not change the public routing assistant; it gives administrators a clearer view of whether the knowledge index, Gemini embeddings, evaluation suite, handoff layer, recovery snapshots, security posture, feedback loop, and maintenance schedule are ready for production use.

## Added

- Public-safe observability summary.
- Admin Observability page.
- Operational readiness score.
- Run Observability Checks action.
- Admin-only observability events.
- Operations runbook summary and export.
- Signals for index records, embedded records, retrieval state, maintenance, security audit, recovery snapshots, evaluation status, handoff status, saved sessions, and feedback records.

## REST endpoints

- `GET /wp-json/sc-research-librarian-ai/v1/observability/status`
- `GET /wp-json/sc-research-librarian-ai/v1/observability/events` — admin only
- `POST /wp-json/sc-research-librarian-ai/v1/observability/run-checks` — admin only
- `GET /wp-json/sc-research-librarian-ai/v1/observability/export` — admin only
- `GET /wp-json/sc-research-librarian-ai/v1/operations/runbook`
- `GET /wp-json/sc-research-librarian-ai/v1/operations/export` — admin only

## Shortcodes

```text
[sc_research_librarian mode="observability-summary" title="Research Librarian Observability"]
[sc_research_librarian_observability_summary title="Research Librarian Observability"]
[sc_research_librarian mode="runbook-summary" title="Research Librarian Operations Runbook"]
[sc_research_librarian_runbook_summary title="Research Librarian Operations Runbook"]
```

## Recommended use

Use this page after plugin upgrades, index rebuilds, embedding refreshes, retrieval evaluation runs, security audits, maintenance changes, and recovery snapshot creation.

The public summary is safe for broad visibility. Full events and exports should remain administrator-only.
