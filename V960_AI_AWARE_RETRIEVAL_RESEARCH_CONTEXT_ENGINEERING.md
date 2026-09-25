# Research Librarian AI v9.6.0 — AI-Aware Retrieval & Research Context Engineering

v9.6.0 makes AI-assisted retrieval reproducible at the context level. The Librarian records which corpus and dataset versions, chunking strategy, embedding model, retriever, reranker, prompt version, model version, generation parameters and retrieved evidence were used for a research interaction.

## Architecture boundary

Platform Core remains the governed system of record for AI model/model-version, prompt/prompt-version, inference, evaluation and provenance objects as those Core contracts become available. Research Librarian stores external references to those objects and the local retrieval-context lineage needed to reproduce research retrieval. It does not mint model identity, train models, certify grounding, or interpret retrieval scores as validity.

## Durable objects

- AI research context manifests
- retrieval-run receipts
- retrieved-evidence rank/score records
- context lineage views
- immutable AI context snapshots
- audit events

## Governance

- model and prompt identity are declared/external references
- retrieval scores are descriptive only
- output presence does not certify evidence grounding
- snapshots certify reproducibility of configuration/lineage, not quality or truth
- research judgment remains human-reviewed
