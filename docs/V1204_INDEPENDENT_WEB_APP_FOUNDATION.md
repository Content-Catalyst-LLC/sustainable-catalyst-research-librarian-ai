# Research Librarian v12.0.4 — Independent Web App Foundation

v12.0.4 introduces the first browser application served directly by the Research Librarian Python/FastAPI runtime.

## Entry point

`/research-librarian/`

The application does not require WordPress to render or operate. It consumes Independent Research Librarian API v1 and the persistent research-session runtime.

## Foundation capabilities

- Public standalone application shell and runtime manifest.
- Backend health and release discovery.
- Operator connection to the existing `X-SC-RL-Key` API boundary.
- Project browsing.
- Persistent research-session list/create/read.
- Persistent turn browser and manual research notes.
- Retrieval through `/v1/research-librarian/retrieve`.
- Source/evidence result display.
- Session snapshot freezing.
- Responsive desktop/mobile layout.
- Explicit offline, degraded, and unauthorized states.

## Security boundary

The backend API key is never embedded in the application, repository, HTML, CSS, or JavaScript. v12.0.4 accepts the key from an operator and keeps it only in JavaScript memory for the current page lifetime. It is not written to localStorage, sessionStorage, cookies, or canonical state.

This is intentionally an operator/developer bridge. v12.0.5 replaces it with Identity, Session & Access Runtime for end users.

## State authority

Canonical research state remains in Python/PostgreSQL. Browser state is presentation state only. WordPress neither hosts the standalone application nor stores its canonical session state.

No new database migration is required for v12.0.4.
