# Research Librarian v5.4.0

## Decision Studio / Workbench Deep-Link Actions

Version 5.4.0 turns the typed handoff contracts prepared in v5.3.3 into public Route Action Center actions.

### Public actions

Workbench actions include analysis, calculation, graphing, and scenario comparison. Decision Studio actions include decision briefs, assumption review, tradeoff comparison, and scenario packets.

### Handoff lifecycle

1. A visitor receives a source-aware route result.
2. The Route Action Center displays relevant destination actions.
3. The browser requests a typed `sc-research-handoff/1.1` payload.
4. WordPress stores the payload behind a random, time-limited token.
5. The visitor is redirected to the configured destination URL.
6. A destination can resolve the token through the Research Librarian REST API and revalidate the payload.

Tokens expire after 30 minutes. They contain no API keys, email addresses, IP addresses, or required personal data.

### REST API

- `POST /wp-json/sc-research-librarian/v1/handoff/typed`
- `POST /wp-json/sc-research-librarian/v1/handoff/deep-link`
- `GET /wp-json/sc-research-librarian/v1/handoff/resolve/{token}`
- `GET /wp-json/sc-research-librarian/v1/integration/capabilities`

### Shared events

- `librarian.handoff_prepared`
- `librarian.deep_link_created`
- `librarian.deep_link_resolved`
- `librarian.deep_link_failed`

Destination plugins remain responsible for validating incoming payloads and enforcing their own professional-advice boundaries.
