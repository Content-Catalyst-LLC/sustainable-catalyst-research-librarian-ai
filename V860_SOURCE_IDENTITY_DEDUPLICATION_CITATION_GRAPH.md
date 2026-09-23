# Research Librarian AI v8.6.0 — Source Identity, Deduplication & Citation Graph

v8.6.0 adds the durable scholarly identity layer between v8.5 document intelligence and the governed evidence model in Platform Core.

## Responsibilities

Research Librarian Python owns canonical source identity, alternate copies/versions, stable identifiers, author/institution links, duplicate resolution, and citation-network topology. Platform Core remains authoritative for governed evidence, findings, claims, arguments, provenance, lineage, statistical/visual reasoning, and reproducibility.

## Resolution order

1. DOI
2. arXiv identifier
3. PMID
4. ISBN
5. canonicalized URL
6. normalized title + publication year + first-author fingerprint

If stable identifiers in one request resolve to multiple existing canonical sources, v8.6 fails closed with an identity conflict. It never silently merges those records.

## Citation graph

References extracted by v8.5 are registered as citation edges. A reference containing a stable identifier can create a canonical **stub** even when the cited work has not yet been ingested. When that work later arrives, the same identifier hydrates the existing node instead of creating a duplicate.

Identifiers found only inside parsed bibliography entries are excluded from the citing work's identity. This prevents a paper from being incorrectly identified by the DOI of something it cites.

## Storage

Production uses Postgres tables prefixed `sc_rl_`; SQLite is a local/test fallback. The migration contract is `backend/migrations/005_source_identity_citation_graph.sql`.

## API

- `GET /v1/sources/capabilities`
- `POST /v1/sources/resolve`
- `GET /v1/sources/{canonical_source_id}`
- `GET /v1/sources/{canonical_source_id}/graph`
- `POST /v1/sources/{canonical_source_id}/citations`

`source-identity` is also a v8.3 durable job type.

## Ingestion integration

Normal asynchronous document ingestion now performs v8.5 parsing, resolves the document to a canonical v8.6 source, registers resolvable bibliography edges, writes the canonical source ID into knowledge-record metadata, and then continues through the existing durable index activation and optional embedding path.
