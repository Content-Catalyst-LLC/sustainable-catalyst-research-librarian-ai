# Research Librarian AI v10.4.0 — Systematic Review & Evidence Synthesis Intelligence

## Purpose
Extend reproducible evidence-search protocols into a durable, auditable systematic-review and evidence-synthesis workflow while preserving explicit human scholarly judgment.

## Added
- Durable systematic-review registries linked to v10.3 evidence-search strategies, v10.2 methodology plans, and v10.1 research-question plans.
- Candidate-study registry with source identity, retrieval lineage, identifiers, and duplicate-group references.
- Human title/abstract and full-text screening decisions with reviewer attribution and exclusion reasons.
- Review-flow accounting for registered candidates, screening decisions, full-text decisions, and included records; this is accounting, not PRISMA certification.
- Structured extraction matrices with population, exposure/intervention, comparator, outcomes, study design, arbitrary protocol fields, notes, and source-locator references.
- Reviewer-recorded risk-of-bias assessments by instrument/domain without automatic bias judgments.
- Reviewer-recorded evidence-certainty grades by framework/outcome without automatic certainty grading.
- Narrative, quantitative, mixed, and meta-analysis synthesis plans with heterogeneity considerations and specialist-runtime execution targets.
- Synthesis handoff packets for Workspace, Research Lab, Analytics R, or other declared specialist runtimes without automatic execution.
- Governed Platform Core `systematic-review-evidence-synthesis` candidate objects without automatic Core writes.
- Immutable review snapshots and durable `systematic-review-evidence-synthesis-snapshot` jobs.
- v10 unified-environment binding as `systematic-review-plan`.

## Architecture boundary
Research Librarian owns review protocol orchestration, screening/extraction records, evidence-synthesis planning, audit lineage, and handoff preparation. Knowledge Library remains the authority for source ingestion, parsing, indexing, retrieval, source identity, and document intelligence. Specialist runtimes execute computational synthesis. Platform Core remains the governed authority for promoted research/evidence objects and provenance.

## Governance
The engine does not automatically include or exclude studies, determine risk of bias, assign evidence certainty, execute meta-analysis, interpret pooled effects, or promote truth. Human review remains explicit and attributable.
