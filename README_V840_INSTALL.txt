Research Librarian AI v8.4.0 — Advanced Retrieval & Reranking Engine

INSTALL ORDER
1. Push/tag the v8.4.0 repository to GitHub.
2. Deploy the v8.4.0 Python backend to Contabo BEFORE installing the WordPress package.
3. Verify /health reports 8.4.0.
4. Verify /v1/retrieval/plan returns the deterministic query-plan schema.
5. Verify /v1/retrieve/explain reports advanced retrieval diagnostics.
6. Verify /v1/jobs/runtime remains durable; production Postgres should report for-update-skip-locked.
7. Verify /v1/core/readiness remains compatible and write-ready with Platform Core v3.3+.
8. Install the v8.4.0 WordPress plugin package.

VPS DEFAULTS
Runtime root: /opt/sustainable-catalyst/research-librarian-ai
Compose: /opt/sustainable-catalyst/research-librarian-ai/compose.yml
Environment: /opt/sustainable-catalyst/research-librarian-ai/.env.contabo
Container: sc-research-librarian
Port: 127.0.0.1:8093
Platform Core: http://sc-core:8090

v8.4.0 does not require a new knowledge-index schema migration. It extends the Python retrieval layer while preserving the v8.3 Postgres async job runtime and v8.2 Platform Core boundary.
