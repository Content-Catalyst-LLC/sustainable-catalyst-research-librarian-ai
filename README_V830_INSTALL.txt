Research Librarian AI v8.3.0 — Asynchronous Ingestion & Document Processing Runtime

INSTALL ORDER
1. Push/tag the v8.3.0 repository to GitHub.
2. Deploy the v8.3.0 Python backend to Contabo BEFORE installing the WordPress package.
3. Verify /health reports 8.3.0.
4. Verify /v1/jobs/runtime reports a durable queue; production Postgres should report for-update-skip-locked.
5. Verify /v1/core/readiness remains compatible with Platform Core v3.3+.
6. Install the v8.3.0 WordPress plugin package.

VPS DEFAULTS
Runtime root: /opt/sustainable-catalyst/research-librarian-ai
Compose: /opt/sustainable-catalyst/research-librarian-ai/compose.yml
Environment: /opt/sustainable-catalyst/research-librarian-ai/.env.contabo
Container: sc-research-librarian
Port: 127.0.0.1:8093
Platform Core: http://sc-core:8090

The v8.3 deployer uses the correct research-librarian-ai runtime root by default. SC_TARGET_ROOT remains available as an override.
