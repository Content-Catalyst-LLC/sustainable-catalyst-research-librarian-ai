Research Librarian AI v8.2.0 — Python Service Architecture & Platform Core Client
=================================================================================

DEPLOYMENT ORDER
1. Push/tag the v8.2.0 repository to GitHub.
2. Deploy the v8.2.0 Python backend to Contabo BEFORE installing the WordPress package.
3. Verify /health reports 8.2.0.
4. Verify authenticated /v1/core/readiness reports Platform Core 3.3.0+ compatible and all required Core capability probes healthy.
5. Install the v8.2.0 WordPress plugin package.

CORE REQUIREMENTS
- Platform Core v3.3.0 or newer within major version 3.
- Core container: sc-core on the shared sc-internal network.
- Core private URL: http://sc-core:8090.
- Research Librarian receives the same write secret used by Core as SC_CORE_WRITE_API_KEY, stored server-side as SC_RL_CORE_WRITE_API_KEY.
- No Core secret belongs in WordPress or in the release ZIP.

DATABASE CHANGE
- Ancillary SQLite schema advances 18 -> 19.
- New table: platform_core_bindings.
- Postgres/pgvector knowledge index remains schema 3 / sc-research-librarian-postgres-index/1.2.
- No Postgres knowledge-index migration is required.

NEW PRIVATE ENDPOINTS
GET  /v1/core/architecture
GET  /v1/core/readiness
GET  /v1/core/bindings
GET  /v1/core/bindings/{local_kind}/{local_id}
POST /v1/core/research-objects/promote
POST /v1/core/research-projects/synchronize
GET  /v1/core/research-projects/{core_project_id}/bundle
POST /v1/core/exchange/packages

All endpoints require X-SC-RL-Key.

BOUNDARIES
- Research Librarian Python owns ingestion, parsing, chunking, indexing, retrieval, connectors, document intelligence, and Core orchestration.
- Platform Core owns governed research objects, provenance/lineage, reasoning objects, reproducibility, visual/statistical reasoning, and cross-product exchange.
- No automatic truth promotion.
- No automatic conclusion promotion.
- Core is not used as an arbitrary research-code execution engine.
