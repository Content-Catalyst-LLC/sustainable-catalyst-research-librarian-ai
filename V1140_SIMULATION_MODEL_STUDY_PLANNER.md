# Research Librarian AI v11.4.0 — Simulation & Model Study Planner

## Architecture

Research Librarian owns prospective simulation/model-study planning and research-facing orchestration. Research Lab, Workspace, Workbench, language runtimes, and other specialist compute systems own execution. Platform Core remains the authority for governed model/research objects.

The planner inherits causal/statistical/program lineage from v11.3 rather than rewriting it. A model, scenario, calibration plan, or validation plan is a declared research object—not an empirical fact, validated forecast, or causal conclusion.

## Durable objects

- Simulation/model study
- Model specification
- Simulation variable
- Simulation parameter
- Scenario set
- Stochastic assumption
- Calibration plan
- Validation plan
- Uncertainty plan
- Sensitivity plan
- Ensemble plan
- Compute budget
- Stopping criterion
- Output commitment
- Human study decision
- Immutable simulation-study snapshot

## Analytical planning

The layer can record deterministic, stochastic, Monte Carlo, system-dynamics, agent-based, discrete-event, optimization, mechanistic, surrogate, or hybrid study designs. It can define scenario comparisons, probability distributions, seed policy, calibration targets, validation datasets/metrics, Monte Carlo budgets, Morris/Sobol-style sensitivity plans, uncertainty propagation, model ensembles, computational limits, stopping rules, and reporting commitments.

## Execution handoffs

Approved model specifications produce non-writing handoff packets targeted to `research-lab-simulation`, with secondary Workspace and Workbench targets. Handoffs contain the declared model inputs and analysis plan but explicitly state that execution, calibration, validation, forecast acceptance, causal inference, and result interpretation have not been performed.

## Governance

- Human model-study approval is required.
- Causal-design lineage is inherited, not rewritten.
- Model assumptions and scenario definitions remain explicit.
- Validation plans do not certify validity until independently executed and reviewed.
- Model output is not empirical truth.
- No automatic model selection.
- No automatic calibration.
- No automatic validation.
- No automatic simulation execution.
- No automatic forecast acceptance.
- No automatic causal inference.
- No automatic truth promotion.
