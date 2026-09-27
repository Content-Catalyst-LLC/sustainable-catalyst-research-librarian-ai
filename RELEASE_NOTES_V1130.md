# Research Librarian AI v11.3.0 — Causal Research Design Intelligence

v11.3.0 adds governed, prospective causal research design planning above v11.2 Statistical Analysis Planning Intelligence.

### Added
- Durable causal-design records with inherited v11.2 statistical-plan and preregistration lineage.
- Causal variable-role registry and directed acyclic graph with cycle rejection.
- Explicit causal assumptions with testability classification.
- Identification-strategy registry for experimental and quasi-experimental/observational designs.
- Diagnostic, negative-control and causal sensitivity planning.
- Human identification-strategy approval gates.
- Causal DAG and design-matrix views.
- Non-executing handoffs to Research Lab causal inference and statistical-analysis runtimes.
- Platform Core `causal-research-design` candidates and immutable snapshots.
- Unified-environment `causal-research-design` binding.
- Durable `causal-research-design-intelligence-snapshot` job.
- Migration `028_causal_research_design_intelligence.sql`.

### Governance
A DAG, adjustment set, instrument or identification strategy is treated as a declared design assumption, not proof of a causal relation or valid identification. v11.3 performs no automatic identification, adjustment-set selection, instrument validation, causal estimation, causality inference, execution or truth promotion.
