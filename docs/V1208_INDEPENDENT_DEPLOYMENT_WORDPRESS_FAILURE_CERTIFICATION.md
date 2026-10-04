# Research Librarian v12.0.8 — Independent Deployment & WordPress-Failure Certification

v12.0.8 closes the WordPress-decoupling program begun in v12.0.1 by certifying that the Research Librarian remains operational when WordPress is unreachable or absent.

## What this release certifies

The certification target is specifically:

**WordPress unreachable or absent.**

The certified independent path includes:

- backend service health;
- Independent API v1;
- Independent Web App;
- backend-owned identity/session authority;
- persistent research sessions;
- retrieval;
- project API surface;
- migration-ledger continuity;
- compatibility-alias continuity;
- thin WordPress adapter fail-closed semantics.

This is not a general “all dependencies can fail” certification. PostgreSQL, Platform Core, and other configured backend/runtime dependencies retain their existing architectural roles.

## Runtime certification report

Backend endpoints:

- `GET /v1/research-librarian/independence/manifest`
- `GET /v1/research-librarian/independence/report`

The manifest is public metadata. The report requires normal Independent API authentication.

The report is read-only. It evaluates runtime authority, WordPress optionality, database readiness, identity runtime, persistent-session runtime, migration-ledger continuity, web-app assets, browser secret boundaries, thin-adapter failure semantics, and required route registration.

Each report receives a deterministic SHA-256 certificate fingerprint over the material certification result.

## WordPress blackout probe

The v12.0.8 automated test suite and production deployment verifier run an in-process DNS blackout guard for WordPress/Sustainable Catalyst hostnames while exercising:

- `/health`;
- `/research-librarian/`;
- Independent API manifest;
- identity manifest;
- migration manifest;
- deterministic retrieval with semantic embeddings disabled;
- persistent session creation;
- persistent turn creation;
- session summary;
- the independence certification report.

Any accidental outbound WordPress DNS dependency causes the certification probe to fail.

## WordPress plugin role

The WordPress v12.0.8 module is passive. It exposes only:

- `GET /wp-json/sc-research-librarian-ai/v1/independent-certification`

That route reports the certified architecture boundary. It does not proxy the backend report, hold backend credentials, perform remote requests, or store canonical research state.

## No database migration

v12.0.8 adds no database migration. It certifies the durable stores established by previous releases.

## Release completion criteria

Production v12.0.8 is certified only when the Contabo deployment verifier confirms:

1. v12.0.8 health is ready;
2. Postgres remains the production database backend;
3. identity/session runtime is available;
4. migration ledger remains available;
5. required independent routes are registered;
6. the read-only certification report returns `certified=true`;
7. the WordPress DNS blackout probe completes with no blocked WordPress network attempt.

## Next boundary

v12.1.0 — Neural Research Intelligence Foundation.
