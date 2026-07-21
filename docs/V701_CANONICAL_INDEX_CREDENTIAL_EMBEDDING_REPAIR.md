# Research Librarian AI v7.0.1

## Canonical Index, Credential, and Embedding Queue Repair

Research Librarian v7.0.1 repairs the production split between the legacy WordPress index and the durable Python index.

### Canonical behavior

When Python Intelligence is enabled, the Render/FastAPI SQLite index is authoritative. Knowledge Index rebuild, embedding test, and embedding generation actions delegate to the backend. The backend reads Gemini credentials only from `SC_RL_GEMINI_API_KEY`. The WordPress-side Gemini key remains available solely for direct fallback operation when Python Intelligence is disabled.

### Index completeness

The WordPress fallback crawler now discovers every eligible public post type, excludes WordPress infrastructure types, and paginates deterministically across the complete eligible set. The durable sync continues to publish per-post-type collection diagnostics.

### Resumable embeddings

A successful full sync schedules bounded embedding batches through WP-Cron. Each backend batch persists completed vectors. Remaining chunks schedule the next pass, transient provider failures retry, and credential failures stop with an explicit configuration state rather than looping.

### Recovery operation

Use **Python Intelligence → Full Sync and Complete Embedding Queue**. It:

1. Collects all eligible public records.
2. Commits the transactional runtime index.
3. Tests the backend embedding credential and model.
4. Processes an initial batch.
5. Continues through WP-Cron until pending chunks reach zero.

### Credential boundary

- WordPress ↔ Python authentication: `SC_RL_BACKEND_API_KEY` mirrored in the WordPress Shared integration key field.
- Python ↔ Gemini authentication: `SC_RL_GEMINI_API_KEY` stored only in Render.
- WordPress fallback ↔ Gemini authentication: optional WordPress saved Gemini key, used only when Python Intelligence is disabled.
