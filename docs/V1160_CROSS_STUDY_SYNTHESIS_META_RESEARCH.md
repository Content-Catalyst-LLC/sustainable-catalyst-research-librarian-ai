# Research Librarian AI v11.6.0 — Cross-Study Synthesis & Meta-Research

## Purpose
v11.6.0 creates the governed layer that sits above individual study protocols, statistical/causal/model plans, systematic reviews, and v11.5 reproduction/replication records. It organizes multiple studies into a reviewable synthesis without treating aggregation as truth.

## Durable objects
- cross-study synthesis project
- study evidence record and human inclusion/exclusion disposition
- cross-study comparability dimension
- human risk-of-bias assessment
- meta-research observation
- synthesis/compute plan
- specialist-runtime execution receipt
- human synthesis interpretation
- human approval decision
- study matrix, evidence landscape, directional-variation map, meta-research summary
- Platform Core candidate
- immutable snapshot

## Execution boundary
Research Librarian prepares governed synthesis inputs and handoffs. Workspace, Research Lab, or another named specialist runtime performs meta-analysis, meta-regression, Bayesian synthesis, network synthesis, diagnostics, or sensitivity computation. Returned pooled estimates and diagnostics are execution receipts, not scholarly verdicts.

## Governance
The engine does not automatically include studies, judge risk of bias, perform meta-analysis, declare publication bias, accept claims, infer causality, or promote a pooled estimate to truth. Study differences and limitations remain explicit. Scholarly conclusions require a human-authored interpretation.

## Persistence
Postgres migration: `031_cross_study_synthesis_meta_research.sql`.
Durable job: `cross-study-synthesis-meta-research-snapshot`.
Unified environment component: `cross-study-synthesis-plan`.
