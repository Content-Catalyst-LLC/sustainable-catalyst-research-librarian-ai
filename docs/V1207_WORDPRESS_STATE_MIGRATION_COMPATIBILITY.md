# Research Librarian v12.0.7 — WordPress State Migration & Compatibility Layer

v12.0.7 provides the governed state-cutover layer between legacy WordPress-held Research Librarian state and the independent Python/FastAPI runtime.

## Architectural rule

WordPress is a migration **source** and optional compatibility interface. It is not the canonical research-state authority.

The migration process is explicit:

1. inventory WordPress state;
2. redact secret-bearing fields;
3. normalize state into typed migration candidates;
4. prepare a backend migration run;
5. classify candidates;
6. require explicit human confirmation;
7. apply supported candidates to the Python runtime;
8. issue durable migration receipts;
9. create compatibility aliases from legacy IDs to canonical IDs;
10. preserve the original WordPress state during the v12.0.7 rollback window.

No automatic migration occurs.

## Supported migration candidates

v12.0.7 can normalize and migrate:

- research projects;
- research contexts;
- Research Rooms;
- Library objects;
- persistent research sessions;
- persistent research turns;
- compatibility-only legacy records.

Unknown state is preserved as compatibility/inventory evidence rather than silently treated as canonical research data.

## Owner mapping

WordPress user IDs are not Research Librarian identities.

User-owned legacy records use owner keys such as:

`wp-user:7`

Before a user-owned record is migrated, an administrator must explicitly map that key to a backend identity reference:

`identity:<identity_id>`

Unmapped records are classified `blocked-owner-map`.

Compatibility aliases never grant authorization.

## Candidate classification

A prepared migration candidate is classified as one of:

- `migratable`
- `duplicate`
- `conflict`
- `blocked-owner-map`
- `blocked-secret-bearing`
- `unsupported`

A migration run containing conflicts fails closed at apply time.

## Idempotency

Candidate fingerprints and target IDs are deterministic.

The backend stores:

- migration runs;
- migration candidates;
- migration receipts;
- compatibility aliases.

Rerunning an identical inventory produces duplicates/idempotent receipts instead of creating new canonical objects.

Persistent turns receive deterministic requested turn IDs in v12.0.7, preventing duplicate conversation turns if migration is retried.

## WordPress inventory

The WordPress migration adapter reads only allowlisted Research Librarian namespaces:

- `sc_rl_*`
- `sc_research_librarian_*`

It inventories WordPress options and user metadata, plus explicitly registered extension candidates through:

`sc_rl_v1207_legacy_state_candidates`

Secret-looking keys such as passwords, API keys, private keys, tokens, nonces, and secrets are removed or blocked.

The inventory process is read-only.

## WordPress REST surface

Public metadata:

- `GET /wp-json/sc-research-librarian-ai/v1/state-migration`

Administrator + WordPress REST nonce:

- `POST /wp-json/sc-research-librarian-ai/v1/state-migration/inventory`
- `POST /wp-json/sc-research-librarian-ai/v1/state-migration/prepare`
- `GET /wp-json/sc-research-librarian-ai/v1/state-migration/runs/{run_id}`
- `POST /wp-json/sc-research-librarian-ai/v1/state-migration/runs/{run_id}/apply`

Authenticated compatibility resolution:

- `POST /wp-json/sc-research-librarian-ai/v1/state-migration/resolve`

Apply requires the literal administrator confirmation `MIGRATE`.

## Backend REST surface

- `GET /v1/research-librarian/wordpress-migration/manifest`
- `GET /v1/research-librarian/wordpress-migration/capabilities`
- `POST /v1/research-librarian/wordpress-migration/prepare`
- `GET /v1/research-librarian/wordpress-migration/runs`
- `GET /v1/research-librarian/wordpress-migration/runs/{run_id}`
- `POST /v1/research-librarian/wordpress-migration/runs/{run_id}/apply`
- `POST /v1/research-librarian/wordpress-migration/resolve`

## Migration 040

`040_wordpress_state_migration_compatibility.sql` adds durable Postgres tables for:

- migration runs;
- candidates;
- receipts;
- compatibility aliases.

SQLite equivalents exist for local/test execution.

## Rollback posture

v12.0.7 does not delete source WordPress state.

That is deliberate. The migration cutover can be validated while the source remains available for forensic comparison and rollback.

## Next boundary

v12.0.8 — Independent Deployment & WordPress-Failure Certification.

That release should prove the Research Librarian remains usable when WordPress is unreachable or removed from the runtime path.
