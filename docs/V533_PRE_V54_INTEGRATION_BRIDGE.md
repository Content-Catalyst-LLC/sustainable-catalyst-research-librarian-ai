# Research Librarian v5.3.3 — Pre-v5.4 Integration Bridge

This release prepares the contracts required by v5.4.0 without adding the public Decision Studio or Workbench deep-link action experience.

## Added

- Feature Suggestions v3 contextual feedback adapter
- Shared `sc_platform_event` publishing
- Privacy-minimized route, source, article-map, and rating context
- Typed `sc-research-handoff/1.0` payload preparation
- Destination capability discovery and availability checks
- Integration diagnostics and test events

## REST API

- `GET /wp-json/sc-research-librarian/v1/integration/capabilities`
- `GET /wp-json/sc-research-librarian/v1/integration/health` — administrators
- `POST /wp-json/sc-research-librarian/v1/feedback/contextual`
- `POST /wp-json/sc-research-librarian/v1/handoff/typed`
- `GET /wp-json/sc-research-librarian/v1/events/schema`

## Feedback boundary

The bridge sends typed context to Feature Suggestions through `scfs_research_librarian_feedback` when that action is available. It does not require Feature Suggestions to be active and does not transmit raw conversations, email addresses, IP addresses, or API keys.

## v5.4 boundary

The typed handoff endpoint prepares and validates payloads. Public deep-link buttons, destination launch URLs, action-center controls, failure recovery, and return-to-research navigation remain part of v5.4.0.
