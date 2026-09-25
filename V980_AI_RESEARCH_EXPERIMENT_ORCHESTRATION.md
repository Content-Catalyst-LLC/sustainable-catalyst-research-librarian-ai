# Research Librarian AI v9.8.0 — AI Research Experiment Orchestration

v9.8.0 turns the v9.6 AI research-context and v9.7 evaluation layers into a durable experiment-orchestration environment.

## Experiment lifecycle

1. Define an experiment and declared outcomes.
2. Register one or more parameterized trial configurations.
3. Create an explicit execution handoff to Workspace, Research Lab, Workbench, or an external runtime.
4. Register the external runtime's run receipt; a handoff alone never counts as execution.
5. Bind completed runs/trials to v9.7 RAG evaluations.
6. Inspect descriptive experiment state and run counts without automatic ranking.
7. Freeze an immutable, content-hashed experiment snapshot.

## Governance

Platform Core remains the owner of governed AI model, model-version, dataset, prompt, inference, provenance, and evaluation semantics. Research Librarian preserves external refs and orchestrates research workflow; it does not train models or mint model identity. Execution happens in specialist runtimes. Run success is taken only from an explicit receipt. Evaluation evidence does not imply a winning model, causal effect, validity, or truth.

## Durable job

`ai-research-experiment-snapshot`

## Migration

`013_ai_research_experiment_orchestration.sql`
