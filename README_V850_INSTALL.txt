Research Librarian AI v8.5.0 — Document Intelligence & Scholarly Parsing

INSTALL ORDER
1. Push/tag the v8.5.0 repository to GitHub.
2. Deploy the v8.5.0 Python backend to Contabo before installing WordPress.
3. Verify /health reports 8.5.0.
4. Verify /v1/documents/capabilities reports the document-intelligence schema and PDF support.
5. Parse a Markdown smoke document through /v1/documents/parse.
6. Verify /v1/jobs/runtime remains durable and /v1/core/readiness remains Core v3.3+ write-ready.
7. Install the v8.5.0 WordPress package.

VPS DEFAULTS
Runtime root: /opt/sustainable-catalyst/research-librarian-ai
Compose: /opt/sustainable-catalyst/research-librarian-ai/compose.yml
Environment: /opt/sustainable-catalyst/research-librarian-ai/.env.contabo
Container: sc-research-librarian
Port: 127.0.0.1:8093
Platform Core: http://sc-core:8090

v8.5.0 adds no knowledge-index schema migration. Parsed sections are stored in existing record metadata and consumed by existing deterministic section-aware chunking.
