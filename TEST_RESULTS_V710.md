# Research Librarian v7.1.0 Validation Report

**Release:** v7.1.0 — Neon Postgres Durable Index  
**Validation date:** 2026-07-22

## Release scope

Research Librarian v7.1.0 introduces a Neon-compatible PostgreSQL generation
store for the durable knowledge index. The release adds idempotent source-batch
staging, bounded generation activation, active-generation switching, durable
reconciliation, pgvector embeddings, database diagnostics, and recovery from
the existing private WordPress staging file.

SQLite remains available for local development, test compatibility, and
ancillary platform data. Production knowledge-index storage switches to
PostgreSQL only when `SC_RL_DATABASE_BACKEND=postgres` and a valid
`DATABASE_URL` are configured.

## Validation results

- Backend test suite: **87 passed**
- WordPress/PHP test suites: **30 passed**
- PHP syntax validation: **44 files passed**
- JavaScript syntax validation: **3 files passed**
- JSON parsing validation: **86 files passed**
- Python compile validation: **32 files passed**
- Repository ZIP integrity: **passed**
- WordPress plugin ZIP integrity: **passed**
- Secret-pattern scan: **passed**

## Postgres-specific contract coverage

The automated suite covers:

- Postgres backend selection and SQLite fallback
- Required pooled and direct connection settings
- Schema and pgvector migration contracts
- Idempotent batch staging
- Generation-scoped records and chunks
- Bounded activation cursors
- Active-generation switching
- Reconciliation and recovery states
- Embedding dimensionality configuration
- Neon database diagnostics in the WordPress administration interface
- Free-tier storage warning configuration

## Deployment validation boundary

No live Neon credentials were supplied to the build environment. Therefore,
this release was **not** tested against the user's live Neon project or Render
service. Live validation must be completed after deployment by running the
included Neon readiness check and confirming the backend database diagnostics.
The local and contract tests do not substitute for that production connection
test.

## Required production settings

```text
SC_RL_DATABASE_BACKEND=postgres
DATABASE_URL=<Neon pooled connection string>
DIRECT_DATABASE_URL=<Neon direct connection string>
SC_RL_EMBEDDING_DIMENSIONS=768
SC_RL_POSTGRES_GENERATION_RETENTION=1
SC_RL_NEON_FREE_STORAGE_WARNING_MB=400
```

Existing Gemini, backend integration-key, and CORS settings remain required.
