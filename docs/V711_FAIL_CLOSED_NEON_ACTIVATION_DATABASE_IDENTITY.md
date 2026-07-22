# v7.1.1 — Fail-Closed Neon Activation and Database Identity

v7.1.1 prevents a production deployment from silently using an empty local
SQLite knowledge index when Neon credentials are present or expected.

## Startup contract

When `SC_RL_DATABASE_BACKEND=postgres`, startup requires:

```text
DATABASE_URL=<pooled Neon connection string>
DIRECT_DATABASE_URL=<direct Neon connection string>
SC_RL_DATABASE_SCHEMA=public
SC_RL_DATABASE_FAIL_CLOSED=true
```

The backend automatically runs its idempotent schema migration through the
direct connection, then verifies that the runtime and migration connections
resolve to the same normalized endpoint, database, role, schema, and Neon
branch/project identifiers when available. A mismatch raises a startup error.
There is no production fallback to the local SQLite knowledge index.

## Database identity

The authenticated database diagnostics and identity endpoints expose only
non-secret information:

- effective storage backend;
- endpoint identifier and pooled/direct roles;
- database, role, and schema;
- Neon branch/project identifiers when available;
- migration and pgvector readiness;
- a password-free database fingerprint;
- active generation, record, and chunk counts.

## Committed-empty recovery

A generation is committed only when all of the following are true inside the
same Postgres transaction:

1. the expected record count exists;
2. retrieval chunks exist;
3. the active-generation row is selected;
4. the meta pointer identifies the same generation;
5. the generation fingerprint matches the connected Neon identity.

A historical SQLite-era or foreign-database commit marker is classified as
`committed-empty` or `committed-unverified`, never as success. WordPress keeps
the private staging file and replays it into a fresh Neon generation without
re-running source discovery.
