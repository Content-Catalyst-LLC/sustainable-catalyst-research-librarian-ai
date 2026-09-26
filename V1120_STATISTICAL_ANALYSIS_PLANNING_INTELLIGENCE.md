# Research Librarian AI v11.2.0 — Statistical Analysis Planning Intelligence

## Purpose
Turns a v11.1 study protocol and its preregistration lineage into an explicit, reviewable statistical analysis plan before specialist-runtime execution.

## Capabilities
- Bind a statistical plan to a v11.1 study protocol and inherit program, protocol, sampling, hypothesis, outcome, variable, commitment, and preregistration-baseline lineage.
- Register explicit estimands with population, exposure/treatment, comparator, outcome, time horizon, and summary measure.
- Register model specifications without fitting models or ranking alternatives.
- Register planned assumption checks and prespecified responses if assumptions are challenged.
- Record power/sample-size planning inputs and external calculation artifact references without calculating power automatically.
- Record multiplicity/error-rate procedures.
- Record missing-data assumptions, planned handling, diagnostics, and fallback/sensitivity strategy.
- Register sensitivity analyses and interpretation boundaries.
- Register reporting commitments covering estimates, intervals, diagnostics, thresholds, effects, and subgroups.
- Require human approval of model specifications for structural runtime-handoff readiness.
- Produce non-executing handoffs through the existing v8.11 Statistical Research layer to specialist runtimes such as Catalyst Analytics R, Workspace, Research Lab, Workbench, or approved external runtimes.
- Produce non-writing Platform Core statistical-analysis-plan candidates without promotion.
- Freeze immutable reproducibility snapshots and expose durable snapshot jobs.
- Bind statistical-analysis plans into the unified scholarly/AI research environment.

## Governance
The plan is a prospective statistical specification, not an analysis result or scientific-validity certificate. Study-protocol/preregistration lineage is inherited rather than rewritten. Human statistical review remains required. The Librarian does not choose a best model or method, calculate power automatically, execute statistical analyses, infer statistical significance or causality, interpret results, or promote truth. The existing v8.11 Statistical Research layer remains the runtime/Core bridge; specialist runtimes own computation and Platform Core remains statistical-reasoning authority.
