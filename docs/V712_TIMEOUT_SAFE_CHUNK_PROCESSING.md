# Research Librarian v7.1.2 — Timeout-Safe Chunk Processing

## Purpose

v7.1.2 resumes an existing paused Neon generation without rediscovering or replaying source records. The release bounds chunk activation so each WordPress-to-FastAPI request returns before the transport timeout.

## Durable behavior

- The default chunk batch is five records.
- Each record is deleted/rebuilt idempotently and committed before the next record starts.
- A JSONB recordset inserts all chunks for one record in one Postgres operation.
- A Postgres advisory lock prevents overlapping retries for the same job.
- The next batch size shrinks after a slow step and grows one record at a time after fast steps.
- WordPress treats cURL timeout 28 as ambiguous and polls Neon before retrying.

## Resume path

Keep the existing rebuild paused during deployment. After Render and WordPress both report v7.1.2, choose Resume. The backend continues from `chunk_cursor`; already chunked records are not repeated.
