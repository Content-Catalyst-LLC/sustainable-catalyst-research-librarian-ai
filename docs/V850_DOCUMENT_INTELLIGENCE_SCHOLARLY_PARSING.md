# Research Librarian AI v8.5.0 — Document Intelligence & Scholarly Parsing

v8.5.0 adds a deterministic Python document-intelligence layer ahead of chunking and retrieval.

## Runtime boundary

Research Librarian owns acquisition, parsing, structural extraction, identifiers, references, citation mentions, and retrieval metadata. Platform Core remains authoritative for governed evidence, claims, findings, arguments, provenance, lineage, reproducibility, and visual/statistical reasoning.

## Supported parsing

- Plain text and Markdown structural parsing.
- HTML title/heading/caption extraction using the Python standard library.
- PDF text and metadata extraction with `pypdf`.
- Section hierarchy and page provenance where available.
- DOI, arXiv, PMID, ISBN, and URL discovery.
- Bibliography/reference entries and author-year/numeric citation mentions.
- Figure, table, and equation caption/label discovery.

## APIs

- `GET /v1/documents/capabilities`
- `POST /v1/documents/parse`
- `POST /v1/documents/parse/async`

Asynchronous parsing uses the v8.3 durable queue. Normal document-ingestion jobs also enrich indexed records with v8.5 document-intelligence metadata so section-aware chunks flow directly into v8.4 retrieval.

## Safety and provenance

The parser does not assign truth, evidence quality, or scholarly validity. OCR is not silently performed. A scanned/image-only PDF reports that no extractable text was found and can be routed to a future OCR stage.
