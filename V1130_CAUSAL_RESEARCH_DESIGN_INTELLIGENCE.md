# Research Librarian AI v11.3.0 — Causal Research Design Intelligence

## Purpose
v11.3.0 adds a durable, prospective causal-design layer above v11.2 Statistical Analysis Planning Intelligence. It organizes causal questions and identification assumptions before specialist runtimes estimate effects.

## Architecture boundary
Research Librarian owns causal-design orchestration and reviewable planning. Research Lab, Catalyst Analytics R, Workspace and other specialist runtimes own causal estimation, diagnostics and computation. Platform Core remains the governed authority for causal/research objects. A registered DAG or identification strategy is an explicit assumption structure, not a causal fact or proof that identification holds.

## Capabilities
- Durable causal research design projects bound to v11.2 statistical analysis plans.
- Inherited preregistration, study-protocol, research-program, estimand and model-specification lineage.
- Causal variable roles: treatment, exposure, outcome, confounder, mediator, collider, instrument, selection, effect modifier, negative control and other roles.
- Directed acyclic causal graph with unknown-reference, self-loop and cycle rejection.
- Explicit causal assumption registry with observable, partially observable and untestable classifications.
- Identification strategies including randomized designs, backdoor/frontdoor adjustment, instrumental variables, regression discontinuity, difference-in-differences, interrupted time series, synthetic control, matching, weighting, g-formula and target-trial emulation.
- Planned overlap, balance, pre-trends, manipulation, first-stage, placebo, negative-control, attrition, missingness, measurement and model diagnostics.
- Negative-control and causal sensitivity plans.
- Human approval of identification strategies before runtime handoff readiness.
- Causal-design matrix, DAG view, structural readiness, specialist-runtime handoffs, Platform Core candidates and immutable snapshots.
- Unified scholarly AI environment component: `causal-research-design`.
- Durable job: `causal-research-design-intelligence-snapshot`.
- Postgres migration 028.

## Guardrails
- No automatic causal identification.
- No automatic adjustment-set selection.
- No automatic instrument validation.
- No automatic causal estimation.
- No automatic causality inference.
- No automatic execution.
- No automatic truth promotion.
- Untestable assumptions remain explicitly untestable.
- DAG edges record researcher-declared assumptions, not empirically established causal relations.
- Readiness means structural planning completeness, not identification validity.
