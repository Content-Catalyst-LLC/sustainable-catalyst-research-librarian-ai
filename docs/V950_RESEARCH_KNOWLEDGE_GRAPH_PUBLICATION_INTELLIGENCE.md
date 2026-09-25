# Research Librarian AI v9.5.0 — Research Knowledge Graph & Publication Intelligence

v9.5.0 introduces a durable graph over existing research and scholarly objects. The graph distinguishes accepted edges from machine- or analyst-suggested proposals. Only explicit publication metadata, citation metadata, declared provenance, existing governed IDs, or human-approved proposals enter the accepted graph.

## Core objects
- node registry for publications, studies, people, organizations, datasets, sources, evidence, findings, claims, arguments, reviews, replications, statistical objects, visual objects, methods, software, and other research objects
- accepted relation registry
- pending/reviewed edge proposals
- immutable graph events
- content-hashed graph snapshots

## Publication intelligence
Publication materialization creates only relations already present in v9.4 publication records, including authorship/contribution, study derivation, citations, evidence/research-object references, statistical lineage, and visual lineage. Publication intelligence reports graph composition and relation counts. It does not produce impact, quality, authority, truth, or influence scores.

## Governance
- automatic semantic inference: disabled
- automatic proposal acceptance: disabled
- impact/authority ranking: disabled
- truth scoring: disabled
- automatic Core writes: disabled
- unresolved proposals excluded from snapshots
