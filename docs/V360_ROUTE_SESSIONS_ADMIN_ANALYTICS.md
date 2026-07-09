# v3.6.0 — Saved Route Sessions and Admin Analytics

This build turns the Research Librarian into a more reviewable operational routing system. It does not track users personally or expose API keys. It stores useful route notes only when the Save session action is used.

## Added

- Saved route-session records from assistant route notes.
- Admin analytics for total sessions, unique routes, handoff targets, confidence counts, top route, top handoff target, and recent saved sessions.
- Public summary shortcode modes for session and analytics status.
- Admin export for route-session logs and related retrieval/evaluation context.
- Session log limit setting and clear-session admin action.

## Endpoints

```text
POST /wp-json/sc-research-librarian-ai/v1/session/save
GET  /wp-json/sc-research-librarian-ai/v1/session/logs
GET  /wp-json/sc-research-librarian-ai/v1/session/export
GET  /wp-json/sc-research-librarian-ai/v1/analytics/summary
```

## Shortcodes

```text
[sc_research_librarian mode="session-summary" title="Research Librarian Route Sessions"]
[sc_research_librarian mode="analytics-summary" title="Research Librarian Route Analytics"]
```

## Boundary

Saved sessions are for platform improvement, QA review, and route-pattern analysis. They should not contain confidential, regulated, proprietary, legal, financial, medical, tax, engineering, or safety-critical information.
