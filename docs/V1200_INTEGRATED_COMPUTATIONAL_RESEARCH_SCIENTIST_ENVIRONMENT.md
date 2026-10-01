# Research Librarian v12.0.0 — Integrated Computational Research Scientist Environment

v12.0.0 is the capstone of the Research Librarian 10.x/11.x research-intelligence line.

It does not replace the v10.0 Unified Scholarly/AI Research Environment. Instead, it operationalizes that environment as a reproducible scientist workspace. Existing research-question, design, evidence, literature, data, computational-planning, protocol, statistical, causal, simulation, reproduction, synthesis, integrity, critique, revision, publication, AI-context, and knowledge-graph objects remain authoritative in their existing stores.

The scientist environment adds:
- Research lifecycle stages with entry/exit criteria.
- Governed computational work packages.
- Human-approved execution handoffs to Workspace, Research Lab, Workbench, Site Intelligence, and other specialist runtimes.
- Execution receipts preserving runtime/environment/artifact lineage.
- Human-authored interpretations that are separate from execution receipts.
- Human checkpoints and stage decisions.
- Lifecycle, workbench, runtime-handoff, and provenance maps.
- Structural/provenance readiness.
- A reproducible scientist dossier.
- Platform Core candidate and immutable environment snapshot.

Governance is explicit: Research Librarian orchestrates; specialist runtimes execute; Platform Core governs promoted objects; humans interpret and make scholarly judgments. v12.0 performs no automatic execution, model selection, causal inference, scientific-validity certification, scholarly judgment, or truth promotion.

Persistence uses PostgreSQL in production and SQLite for local/test operation. Migration 035 adds the scientist environment, event ledger, and immutable snapshot tables. The durable snapshot job is `integrated-computational-research-scientist-environment-snapshot`.
