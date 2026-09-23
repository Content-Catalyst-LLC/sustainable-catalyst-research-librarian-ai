# Research Librarian AI v8.9.0 — Finding, Claim & Evidence Extraction Pipeline

v8.9.0 connects the Librarian's document/retrieval/evidence layers to Platform Core's governed Finding, Claim & Evidence Intelligence contract (`sc.research.finding-claim-evidence.v1`).

## Pipeline

1. Passage evidence is supplied from Librarian retrieval/document intelligence.
2. v8.7 evidence bindings resolve local passage IDs to governed Core EvidenceRecord IDs when available.
3. The Python runtime performs deterministic sentence segmentation and transparent cue-based candidate classification.
4. Candidate findings and claims are returned as `pending`, with exact passage provenance, classification basis, and uncertainty cues.
5. Core promotion is rejected unless the candidate has an explicit `approved` review decision and reviewer identity.
6. Approved candidates are registered in Core with status `proposed`, never as accepted truth.
7. Evidence links default to `contextualizes` unless the caller explicitly supplies a stronger relation.

## Governance boundary

The Librarian may extract and organize candidate propositions. It does not determine truth, automatically accept findings or claims, judge evidence strength, resolve semantic contradictions, or publish conclusions. Platform Core remains the governed registry for findings, claims, evidence relationships, revisions, contradictions, arguments, conclusions, lineage, and reproducibility.

## API

- `GET /v1/core/research-intelligence/capabilities`
- `POST /v1/core/research-intelligence/extract`
- `POST /v1/core/research-intelligence/promote`
- generic durable jobs support `job_type=research-intelligence-extraction`

## Core readiness

v8.9.0 also repairs the v8.8 readiness-registration gap by probing both:

- `/v1/research/project-state/readiness`
- `/v1/research/intelligence/readiness`

through the normal `/v1/core/readiness` capability report.
