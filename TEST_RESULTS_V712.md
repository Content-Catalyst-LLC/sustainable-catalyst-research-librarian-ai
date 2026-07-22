# Research Librarian v7.1.2 Validation

## Release

- Version: `7.1.2`
- Title: **Timeout-Safe Chunk Processing**
- Source: v7.1.1 repository package
- Production database target: Neon Postgres with pgvector

## Implemented repair

- Default Postgres chunk activation batch reduced from 20 records to 5.
- Durable chunk cursor checkpointed after every record.
- Each record's chunks are written through one JSONB bulk insert instead of one network request per chunk.
- Adaptive batch sizing reduces slow batches and grows only one record at a time after fast steps.
- A Postgres advisory lock prevents overlapping activation retries for the same job.
- WordPress treats cURL timeout errors as ambiguous, polls Neon, and resumes from the confirmed cursor instead of declaring immediate failure.
- Existing paused Neon generations resume from their saved `chunk_cursor`; source discovery and source-batch replay are not restarted.
- Admin diagnostics expose current chunk batch, last-step records and duration, heartbeat, and recovered WordPress timeouts.

## Automated validation

- Backend tests from repository layout: **97 passed**.
- Backend tests from Render-style `backend/` layout: **97 passed**.
- WordPress/PHP test suites: **32 passed**.
- Reported PHP contract checks: **836 passed**.
- PHP syntax validation: **46 files passed**.
- JavaScript syntax validation: **3 files passed**.
- JSON parsing validation: **93 files passed**.
- Python compilation: passed.
- Production-source secret scan: **0 hits**. A deliberately fake Postgres URL remains in one database-identity test fixture.

## Package validation

- Repository ZIP integrity: verified.
- WordPress ZIP integrity: verified.
- Installer shell syntax: verified.
- Installer archive checksum contract: verified.

## Production boundary

The build environment did not have the user's private Neon connection strings, WordPress staging file, or live Render service. The live Neon request duration and resume behavior must therefore be confirmed after deployment. v7.1.2 is designed to continue the currently paused generation from the durable chunk cursor rather than restarting the rebuild.
