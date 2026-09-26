# Research Librarian AI v10.3.0 — Evidence Search Strategy Engine

## Purpose
Translate a structured research question and optional methodology plan into a reproducible, auditable evidence-search protocol without automatically executing searches or deciding which sources count as valid evidence.

## Added
- Durable evidence-search strategy records linked to v10.1 question/hypothesis plans and v10.2 research-design plans.
- Deterministic concept and synonym registries derived from declared research variables, population, and context.
- Source-target registries for the Sustainable Catalyst Knowledge Library, Research Librarian federated discovery, scholarly databases, government sources, repositories, archives, domain repositories, and explicitly declared other targets.
- Reproducible Boolean query plans with target bindings, concept mappings, evidence-requirement mappings, and date/language/source-type filters.
- Explicit inclusion and exclusion criteria as reviewable protocol rules.
- Evidence-requirement coverage reporting that measures protocol mapping only, not evidence sufficiency.
- External search execution receipts recording what was run and how many results/imports were reported, without claiming source acceptance.
- Human protocol review and approval before search handoff.
- Search-handoff packets for Knowledge Library/federated discovery/connectors without automatic delivery, execution, import, or source acceptance.
- Governed Platform Core `evidence-search-protocol` candidate handoff without automatic Core writes.
- Immutable search-strategy snapshots and durable `evidence-search-strategy-snapshot` jobs.
- v10 unified-environment binding as `evidence-search-strategy-plan`.

## Architecture boundary
Research Librarian owns search-strategy construction, reproducibility, audit lineage, and orchestration. Knowledge Library remains the owner of source ingestion, parsing, indexing, retrieval, connectors, and document intelligence. Platform Core remains the governed authority for evidence/research objects and provenance. External provider or Library runtimes execute the actual search/import workflow.

## Governance
The engine does not automatically execute external searches, import or accept sources, screen evidence, judge evidence quality, infer scientific sufficiency, or promote truth. Human protocol approval remains explicit.
