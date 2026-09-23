# Research Librarian AI v8.7.0 — Core Evidence Bridge

v8.7.0 establishes the governed evidence boundary between the Research Librarian Python runtime and Platform Core v3.3+.

## Responsibility boundary

Research Librarian owns source acquisition, scholarly parsing, canonical source identity, citation topology, indexing, and retrieval. Platform Core owns governed source snapshots, evidence records, reviews, claim linkage, arguments, provenance/lineage, statistical and visual reasoning, and reproducibility.

## Source snapshot promotion

A hydrated v8.6 canonical source can be promoted through `POST /v1/core/evidence/source-snapshots/promote`. The bridge resolves canonical source metadata and an optional source instance, requires SHA-256 content identity, assigns a deterministic Core snapshot ID, and stores an immutable Librarian↔Core binding.

Citation-only stubs fail closed and must be hydrated before promotion. Reusing the same local snapshot ID with changed governed content is rejected; callers must create an explicit revised snapshot object.

## Passage evidence promotion

`POST /v1/core/evidence/passages/promote` promotes a selected passage into a Platform Core `EvidenceRecord`. Passage promotion requires a previously synchronized source-snapshot binding and records canonical source ID, local/Core snapshot IDs, passage/chunk IDs, section/page provenance, and a SHA-256 passage fingerprint.

The default governance state is deliberately conservative:

- stance: `neutral`
- review status: `unreviewed`
- confidence: absent unless explicitly supplied
- automatic claim creation: disabled
- automatic truth/stance/confidence inference: disabled

The Librarian identifies and retrieves evidence candidates; Platform Core governs their interpretation and review.

## API

- `GET /v1/core/evidence/capabilities`
- `POST /v1/core/evidence/source-snapshots/promote`
- `POST /v1/core/evidence/passages/promote`
- existing `GET /v1/core/bindings` and binding lookup endpoints expose synchronization lineage.

## Idempotency and recovery

Core IDs and idempotency keys are deterministic. Successful bindings are immutable. A repeated identical promotion returns an idempotent replay without another Core write. If Core reports a conflict, the bridge attempts to read the deterministic Core object and confirms its Librarian canonical-source identity before recovering the binding.
