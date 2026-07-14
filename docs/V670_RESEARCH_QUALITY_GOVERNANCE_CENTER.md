# Research Librarian AI v6.7.0

## Research Quality and Governance Center

v6.7.0 establishes measurable, reviewable controls around retrieval quality, citation integrity, source approval, freshness, retention, release readiness, and public methodology. It does not permit autonomous publication, source exclusion, or release-gate overrides.

## New contracts

- `sc-research-governance-policy/1.0`
- `sc-research-source-review/1.0`
- `sc-research-answer-trace/1.0`
- `sc-research-quality-evaluation/1.0`
- `sc-research-release-gate/1.0`
- `sc-research-methodology/1.0`
- `sc-research-governance-export/1.0`

## Answer traceability

Every `/v1/ask` result receives a trace ID and tamper-evident fingerprint covering model, prompt version, index version and checksum, retrieval profile, governance policy, source records, citation verification, evidence gate, and quality score. Query and answer text are not retained by default.

## Release quality gate

The release gate compares exact-title accuracy, top-three retrieval relevance, citation precision and completeness, unsupported-claim rate, route accuracy, PDF page-reference accuracy, fallback continuity, and mean answer quality with the active policy. Critical citation failures block release. Human overrides require a named reviewer and remain auditable.

## Source governance

Records can be approved, left under review, or excluded. Exclusion requires a human reviewer. The retrieval layer can warn about stale records and can optionally require explicit approval without changing the canonical WordPress source.

## Retention and privacy

Trace, evaluation, and governance-event retention are independently configurable. Sessions are hashed by default. Query and answer text storage is opt-in.

## Public methodology

Use `[sc_research_librarian_methodology]` to publish the method, evaluation criteria, limitations, and human-control boundaries.
