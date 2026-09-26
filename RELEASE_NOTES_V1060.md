# Research Librarian AI v10.6.0 — Argument, Claim & Counterclaim Intelligence

v10.6.0 adds a durable argument-analysis layer above v10.5 Scholarly Citation & Literature Intelligence.

## Added

- Durable argument-intelligence projects with optional v10.5 literature-intelligence lineage.
- Researcher-recorded thesis claims, claims, subclaims, counterclaims, rebuttals and qualifications.
- Explicit claim↔evidence relations with provenance, source locators, rationale and optional researcher-declared strength labels.
- Explicit claim↔claim relations: support, challenge, rebuttal, qualification, dependency and alternatives.
- Assumption registry and unresolved tension/contradiction register.
- Descriptive claim-evidence matrices and argument maps.
- Analysis-scope claim decisions (`pending`, `accepted_for_analysis`, `rejected_from_analysis`) that leave truth status undetermined.
- Non-writing handoff to the existing v8.10 argument-synthesis planner.
- Governed Platform Core candidate packages without automatic promotion.
- Durable `argument-claim-counterclaim-intelligence-snapshot` jobs and immutable snapshots.
- Unified v10 environment binding as `argument-intelligence-plan`.
- Postgres migration `021_argument_claim_counterclaim_intelligence.sql`.

## Governance

v10.6.0 does not automatically accept claims, reject counterclaims, infer evidence relations, rank arguments, select a best argument, resolve contradictions, or promote truth. Platform Core remains the authority for governed argument and research objects.
