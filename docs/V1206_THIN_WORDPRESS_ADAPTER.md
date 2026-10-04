# Research Librarian v12.0.6 — Thin WordPress Adapter

v12.0.6 completes the adapter boundary established by v12.0.1–v12.0.5: WordPress is now explicitly an optional presentation/proxy compatibility layer for the independent Research Librarian runtime.

## Authority boundary

Python/FastAPI remains authoritative for:

- identities and authenticated sessions;
- projects and investigations;
- persistent research sessions and turns;
- retrieval and research intelligence;
- evidence/source objects and provenance;
- scientist-environment state;
- backend jobs and runtime execution.

WordPress is not authoritative for any of those domains.

## Thin adapter behavior

The v12.0.6 WordPress adapter exposes:

- `GET /wp-json/sc-research-librarian-ai/v1/thin-adapter`
- `GET /wp-json/sc-research-librarian-ai/v1/thin-adapter/status`
- `POST /wp-json/sc-research-librarian-ai/v1/thin-adapter/proxy`

The public manifest contains only safe adapter metadata. Status/proxy requests require an authenticated WordPress user and a valid WordPress REST nonce.

The proxy does **not** accept arbitrary upstream URLs, hosts, paths, or HTTP methods. Clients submit an operation name from a fixed server-side allowlist. The adapter maps that operation to a fixed Independent API v1 path.

## Allowed read operations

- status
- capabilities
- retrieve
- projects
- project
- project-investigations
- sessions
- session
- session-turns
- session-summary

## Allowed write operations

- project-create
- session-create
- session-turn-add
- session-snapshot-freeze

Write operations additionally require the WordPress `edit_posts` capability.

## Credentials

The existing Research Librarian backend URL and integration key remain stored in the existing server-side Python Intelligence connection configuration. The browser never receives the integration key.

The adapter sends `X-SC-RL-Key` only server-to-server.

## WordPress actor context

The adapter forwards bounded WordPress user context in `X-SC-RL-WP-Actor` as a provenance hint:

- WordPress site URL
- WordPress user ID
- display name
- roles

This context is **not** a Research Librarian backend identity and does not override the v12.0.5 identity/session authority.

## Fail-closed behavior

If the Python backend is unavailable, rejects a request, or returns invalid JSON, the adapter returns an error. It does not create or mutate canonical research state in WordPress and does not fall back to a local WordPress research runtime.

## Storage policy

v12.0.6 adds no database migration and stores no new canonical research data in WordPress. Existing WordPress options are used only to read backend connection configuration.

## Next boundary

v12.0.7 — WordPress State Migration & Compatibility Layer.

That release will explicitly inventory and migrate legacy WordPress research state while preserving the v12.0.6 rule that canonical research authority remains in Python/Postgres.
