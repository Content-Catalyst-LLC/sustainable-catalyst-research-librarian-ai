# Research Librarian v12.0.5 — Identity, Session & Access Runtime

v12.0.5 replaces the v12.0.4 browser operator-key bridge with first-class backend identity and authenticated-session authority.

## Identity authority

Python/FastAPI is authoritative for identities and authenticated sessions. Production identity/session records are durable in Postgres; SQLite remains the local/test fallback.

WordPress is not an identity authority, session authority, or canonical-state authority.

## Authentication

- Email + password login.
- Passwords are hashed with `hashlib.scrypt` using a unique random salt.
- Plaintext passwords are never stored.
- Authentication tokens are generated with `secrets.token_urlsafe(48)`.
- Only SHA-256 hashes of session tokens are stored.
- Browser authentication uses an HttpOnly, SameSite=Strict session cookie.
- Secure cookies default on in production.
- Login lockout is applied after repeated failures.
- Sessions have bounded expiry, last-seen tracking, explicit logout, revocation, and password/role/status revocation.

## Access roles

- `owner`: read/write research plus identity administration.
- `editor`: read/write research and projects.
- `researcher`: read/write research and projects.
- `viewer`: read-only research access.

The existing `X-SC-RL-Key` remains supported for server-to-server integrations, WordPress compatibility, and explicit identity provisioning. It is not embedded in the standalone web application.

## Identity-owned research continuity

Research sessions created through identity authentication receive `client_ref=identity:<identity_id>` server-side. A browser-supplied `client_ref` cannot override this binding. Session listing and session access are filtered/checked against the authenticated identity. The integration-key path remains unrestricted for server administration and compatibility.

## Routes

Public:
- `GET /v1/research-librarian/auth/manifest`
- `POST /v1/research-librarian/auth/login`

Authenticated:
- `GET /v1/research-librarian/auth/me`
- `POST /v1/research-librarian/auth/logout`
- `GET /v1/research-librarian/auth/sessions`
- `POST /v1/research-librarian/auth/sessions/{auth_session_id}/revoke`
- `POST /v1/research-librarian/auth/password`

Administrative:
- `POST /v1/research-librarian/auth/provision` — integration key required.
- `GET /v1/research-librarian/auth/identities`
- `POST /v1/research-librarian/auth/identities/{identity_id}/role`
- `POST /v1/research-librarian/auth/identities/{identity_id}/status`

## First-owner provisioning

v12.0.5 deliberately creates no default account and no default password. After backend deployment, provision the first owner explicitly with the server integration key. See the deployment instructions in this build kit.

## Next boundary

v12.0.6 — Thin WordPress Adapter.
