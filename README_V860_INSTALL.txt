Research Librarian AI v8.6.0 — Source Identity, Deduplication & Citation Graph

Release order
1. Push/tag the v8.6.0 repository to GitHub.
2. Deploy the v8.6.0 Python backend to Contabo before installing WordPress.
3. Verify /health reports version 8.6.0 and ready=true.
4. Verify Platform Core v3.3+ readiness remains write-ready.
5. Verify /v1/sources/capabilities reports the durable source-identity/citation runtime.
6. Verify the production source graph reports storage_backend=postgres.
7. Install the v8.6.0 WordPress package.

Important architecture
- Research Librarian Python owns canonical source identity, document intelligence, connectors, indexing, retrieval, and citation topology.
- Platform Core remains authoritative for governed evidence, findings, claims, arguments, provenance/lineage, reasoning, and reproducibility.
- Stable identifier conflicts fail closed and require deliberate reconciliation; v8.6 never silently merges conflicting canonical works.
- Bibliography-only identifiers are excluded from the identity of the citing work.
- Cited works may exist as identifier-backed stubs until their full document/metadata is ingested.

Production storage
v8.6.0 adds Postgres source-graph tables through backend/migrations/005_source_identity_citation_graph.sql. SQLite is retained only as the local/test fallback for this subsystem.

VPS runtime root
/opt/sustainable-catalyst/research-librarian-ai
