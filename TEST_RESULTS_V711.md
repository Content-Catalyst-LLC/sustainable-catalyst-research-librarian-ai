# Research Librarian v7.1.1 Validation Report

**Release:** v7.1.1 — Fail-Closed Neon Activation and Database Identity  
**Validation date:** 2026-07-21

## Repair target

v7.1.0 could report a completed activation while the selected Neon database remained empty. The backend could still initialize its local SQLite compatibility store, and the WordPress recovery workflow did not have enough database-identity evidence to distinguish a valid Neon generation from an old or foreign committed marker.

v7.1.1 makes the production Postgres path fail closed. Startup now validates the pooled runtime URL, direct migration URL, database, role, schema, pgvector extension, required tables, and password-free database fingerprint before the service accepts traffic.

## Automated validation

- Backend tests: **94 passed**
- WordPress/PHP suites: **31 passed**
- Explicitly reported PHP checks: **855 passed, 0 failed**
- PHP syntax: **45 files passed**
- JavaScript syntax: **3 files passed**
- JSON parsing: **89 files passed**
- Python compilation: **passed**
- Secret-pattern scan: **passed**

## Fail-closed coverage

The regression suite verifies that:

- configured Neon URLs cannot be silently ignored in favor of SQLite;
- production Render startup rejects SQLite unless it is explicitly allowed for emergency diagnostics;
- `DATABASE_URL` and `DIRECT_DATABASE_URL` must identify the same normalized endpoint, database, role, and schema;
- the Postgres migration runs automatically and confirms pgvector plus required tables;
- database diagnostics expose only non-secret identity information;
- a committed generation is not accepted unless records, retrieval chunks, the active pointer, and the database fingerprint all verify;
- committed-empty and foreign-database transactions are replayed from the preserved WordPress staging file;
- WordPress reports the effective Postgres backend and active database identity instead of a hard-coded SQLite label;
- the standalone Neon check refuses missing or mismatched runtime/migration connections.

## Production validation boundary

The packaging environment did not have access to the user's private Neon connection strings. Therefore, the live Neon connection, automatic migration, and production replay were not executed during packaging. On Render, v7.1.1 will now fail startup with an explicit database-identity or migration error instead of silently starting against an empty local index.

Run the password-free production diagnostic from the Render shell with:

```bash
python backend/scripts/neon_check.py
```

A successful result reports `"ok": true`, matching runtime and migration identities, pgvector readiness, and all required tables.
