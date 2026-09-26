# Research Librarian v10.5.0 — Scholarly Citation & Literature Intelligence

This release adds a durable literature-intelligence layer above the accepted Research Knowledge Graph and v10.4 systematic-review corpus. It records scholarly works, human-recorded citation contexts/functions, human-labeled literature strands, human-declared research gaps, human-declared seminal-work candidates, and reviewable related-work candidates.

## Authority boundaries

- Knowledge Library remains source-ingestion and source authority.
- Research Knowledge Graph remains accepted citation/relationship graph authority.
- Platform Core remains governed research-object authority.
- Citation counts and network position are descriptive corpus signals only.
- No automatic impact ranking, authority scoring, seminal-work classification, literature-gap claim, graph write, or truth promotion occurs.

## Reproducibility

The system persists literature projects and event lineage, exposes descriptive citation matrices and landscape views, creates non-writing graph handoffs and Platform Core candidates, supports unified-environment binding, and freezes immutable literature-intelligence snapshots through the durable async runtime.

## Migration

`020_scholarly_citation_literature_intelligence.sql`
