# Research Librarian AI v11.5.0 — Reproduction & Replication Intelligence

## Architecture
Research Librarian owns governed reproduction/replication planning, lineage assembly, comparability structure, deviation disclosure, execution-receipt capture, and human assessment provenance. Specialist runtimes execute workflows and studies. Platform Core remains the governed research-object authority.

## Reproduction versus replication
- **Reproduction** attempts to rerun the same or materially equivalent computational/data workflow and compare expected artifacts or outputs.
- **Replication** tests a registered claim, design, or estimand with an independent dataset, population, setting, implementation, or method.
- A reproduced output is not independent replication evidence.
- A different replication result does not automatically falsify the source claim; comparability, uncertainty, design differences, and scope remain explicit.

## Durable objects
- reproduction/replication project
- reproduction attempt
- replication study
- comparability criterion
- environment manifest
- deviation record
- execution receipt
- human outcome assessment
- human plan decision
- comparison matrix
- lineage map
- runtime handoff
- Platform Core candidate
- immutable snapshot

## Lineage
A project binds a Study Protocol & Preregistration record and can additionally bind Statistical Analysis Planning, Causal Research Design, and Simulation & Model Study records. Cross-layer identifiers are validated fail-closed so mismatched upstream plans cannot be silently combined.

## Governance
The engine never automatically declares research reproduced, replicated, failed, falsified, confirmed, or true. Execution receipts are observations, not scholarly verdicts. Outcome assessments are explicitly human-authored and scope-bounded. Specialist runtimes own execution; Platform Core remains governed research-object authority.

## Runtime targets
Reproduction plans can hand off to Workspace, Research Lab, or a named runtime. Replication plans hand off to Research Lab with Workspace/statistical-runtime context. Handoffs contain execution inputs only and do not contain inferred outcomes.

## Persistence
Postgres migration: `030_reproduction_replication_intelligence.sql`.
Durable job: `reproduction-replication-intelligence-snapshot`.
Unified environment component: `reproduction-replication-plan`.
