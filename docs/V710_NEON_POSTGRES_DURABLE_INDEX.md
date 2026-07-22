# v7.1.0 — Neon Postgres Durable Index

v7.1.0 removes the production knowledge index from Render's ephemeral local
filesystem. Source batches, generations, records, chunks, embeddings, and
activation cursors are stored in Postgres. The active index is selected through
one verified generation pointer instead of renaming SQLite files.

## Required Render environment

```text
SC_RL_DATABASE_BACKEND=postgres
DATABASE_URL=<Neon pooled connection string>
DIRECT_DATABASE_URL=<Neon direct connection string>
```

Keep `SC_RL_BACKEND_API_KEY`, `SC_RL_GEMINI_API_KEY`, and
`SC_RL_CORS_ORIGINS` unchanged.

## Recovery from v7.0.8

Do not cancel the preserved WordPress rebuild. After backend and WordPress are
both on v7.1.0, choose **Repair and Resume Commit**. Neon initially reports the
old SQLite transaction as missing, so WordPress replays the existing staging
file into a fresh Postgres generation. Discovery does not need to run again.

## Activation

1. Stage idempotent source batches.
2. Copy records into an invisible generation in bounded steps.
3. Build chunks in bounded steps.
4. Calculate a durable checksum in bounded steps.
5. Verify record and chunk counts.
6. Atomically switch the active-generation pointer.
7. Start the embedding queue.

The previous active generation remains available for rollback.

## Free-tier embedding storage

The default `SC_RL_EMBEDDING_DIMENSIONS=768` reduces vector storage and keeps
semantic retrieval practical on Neon Free. `gemini-embedding-001` vectors are
normalized after truncation; `gemini-embedding-2` handles truncated-vector
normalization automatically. Changing the model or dimensions requires a full
re-embedding run.
