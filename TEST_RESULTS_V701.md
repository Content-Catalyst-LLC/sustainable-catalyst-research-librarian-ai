# Research Librarian AI v7.0.1 Validation Report

**Release:** Canonical Index, Credential, and Embedding Queue Repair  
**Repository package:** `sustainable-catalyst-research-librarian-ai-v7.0.1.zip`  
**WordPress package:** `sustainable-catalyst-research-librarian-ai-wordpress-v7.0.1.zip`

## Repaired production paths

- Python durable SQLite index becomes canonical whenever Python Intelligence is enabled.
- Knowledge Index rebuild, embedding test, and embedding actions delegate to the authenticated Python backend.
- The WordPress fallback crawler indexes every eligible public post type rather than only posts and pages.
- The fallback index ceiling is expanded to 5,000 records and uses paginated collection.
- The backend exposes authenticated, secret-safe provider diagnostics and a single-embedding connection test.
- Gemini credential diagnostics explicitly identify `SC_RL_GEMINI_API_KEY` without returning the secret.
- Full sync can test the embedding configuration, process an initial bounded batch, and continue pending batches through WP-Cron.
- Invalid-key and credential failures stop the queue in `configuration-error`; transient failures retain bounded retry behavior.
- Semantic coverage counts only vectors created by the currently configured embedding model.

## Automated results

- **69/69** FastAPI/backend tests passed from the repository root.
- **69/69** FastAPI/backend tests passed from `backend/` to validate Render-style imports.
- **21/21** WordPress/PHP release suites passed.
- **695** reported PHP contract checks passed, plus functional assertions.
- **35** PHP files passed syntax validation.
- **3** JavaScript files passed Node syntax validation.
- **62** JSON files passed parsing validation.
- Python compile validation passed.
- Both macOS push scripts passed Bash syntax validation.
- Secret-pattern scan passed.

## Dedicated v7.0.1 verification

- All-public-post-type fallback indexing and removal of the posts/pages-only query.
- Canonical delegation to `SC_RL6_V630_Durable_Index::sync_and_complete_embeddings()`.
- Authenticated `/v1/provider/diagnostics` endpoint.
- Authenticated `/v1/knowledge/embeddings/test` endpoint.
- Secret-safe credential fingerprinting.
- Current-model-only semantic coverage.
- Resumable `sc_rl_v701_embedding_queue_event` processing.
- One-click **Full Sync and Complete Embedding Queue** recovery control.
- Invalid-provider-response conversion to a queue-stopping configuration error.

## Compatibility

- Plugin/backend version: **7.0.1**
- SQLite schema: **10**
- Knowledge index contract: `sc-research-librarian-knowledge-index/10.0`
- Public workspace contract: `sc-research-librarian-public-workspace/2.0`
- Stable platform API: `sc-connected-research-api/1.0`
- Python release target: **3.12**
- Existing schema-10 data is preserved; no destructive migration is introduced.
- Deterministic title-aware fallback remains available.
