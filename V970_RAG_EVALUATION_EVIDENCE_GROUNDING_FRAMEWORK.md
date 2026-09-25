# Research Librarian AI v9.7.0 — RAG Evaluation & Evidence-Grounding Framework

## Purpose

v9.7.0 adds a durable evaluation layer above v9.6 AI-Aware Retrieval & Research Context Engineering. It evaluates retrieval behavior and records evidence-grounding review without turning metrics into truth, validity, or model-quality verdicts.

## Durable objects

- RAG evaluation records linked to a v9.6 AI research context
- evaluation cases linked to declared retrieval runs
- explicit relevance sets and ranked retrieved evidence
- claim-grounding assessments
- citation-correctness assessments
- descriptive evaluation summaries
- side-by-side comparison packets
- immutable evaluation snapshots
- append-only evaluation events

## Retrieval metrics

v9.7 can deterministically compute from reviewer/benchmark-declared relevance sets:

- precision@k
- recall@k
- reciprocal rank
- nDCG@k

These measurements describe retrieval behavior. They do not certify answer validity or research truth.

## Evidence-grounding review

Claim support states are explicitly authored as:

- supported
- partially-supported
- unsupported
- conflicting
- not-assessed

Citation review states are explicitly authored as:

- correct
- partially-correct
- incorrect
- unverifiable
- not-assessed

The Librarian records these judgments and their evidence/rationale; it does not generate a truth determination from them.

## Evaluation summaries

Summaries may report retrieval means, unsupported/conflicting claim rates, citation-correctness rates, latency, and explicit cost metadata. There is no composite score, model ranking, winner selection, automatic claim acceptance, or automatic quality grade.

## Platform boundary

- **Research Librarian:** evaluation orchestration, context linkage, measurement records, human review records, snapshots.
- **Platform Core:** governed AI/model/evaluation semantics and cross-product provenance as the Core AI Engineering track comes online.
- **Workspace / specialist runtimes:** model execution, inference, training/fine-tuning and benchmark computation where appropriate.
- **Research Lab:** statistical comparison, robustness and experimental analysis of evaluation results.

## Durable job

`rag-evaluation-snapshot`

## Migration

`012_rag_evaluation_evidence_grounding.sql`

## Governance

- automatic truth judgment: disabled
- automatic model ranking: disabled
- automatic quality grade: disabled
- automatic claim acceptance: disabled
- metrics are evidence, not verdicts
- human review is required for grounding judgments
