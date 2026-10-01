# Research Librarian v12.0.1 — Runtime Authority & WordPress Decoupling Foundation

v12.0.1 establishes the architectural boundary required to move Research Librarian toward an independent Sustainable Catalyst application without breaking the current WordPress experience.

## Runtime authority

The Python/FastAPI backend is the authoritative Research Librarian runtime. It owns backend service boot, health, authenticated research APIs, research-state persistence, retrieval/indexing, durable jobs, document/source intelligence, research-intelligence orchestration, unified research environments, scientist environments, and Platform Core client orchestration.

WordPress is explicitly classified as an optional interface adapter. It may own WordPress rendering, shortcodes, admin configuration, nonce/user-context translation, presentation assets, and request proxying. It must not own canonical research state, backend job state, scientist-environment state, runtime execution authority, Platform Core governance, scientific validity, or truth promotion.

## New runtime authority API

Authenticated endpoints:
- `/v1/core/runtime-authority/capabilities`
- `/v1/core/runtime-authority/manifest`
- `/v1/core/runtime-authority/wordpress-adapter-contract`
- `/v1/core/runtime-authority/dependency-map`
- `/v1/core/runtime-authority/independence-readiness`
- `/v1/core/runtime-authority/snapshots/freeze`

The public `/health` response now declares `runtime_authority=python-fastapi-backend` and `wordpress_required=false`.

## WordPress transition

The plugin adds `SC_RL_V1201_Runtime_Authority_Adapter`, which exposes the WordPress-side adapter declaration without moving canonical state into WordPress. The transition remains incremental: WordPress stays supported while later releases introduce the independent API, persistent sessions, web app, identity layer, thin adapter, migration compatibility, and independent deployment certification.

## Persistence

Migration 036 adds immutable runtime-authority certification snapshots. PostgreSQL is used in production and SQLite remains available for local/test certification.

This release is a foundation, not a cutover. It does not automatically migrate state or disable WordPress.
