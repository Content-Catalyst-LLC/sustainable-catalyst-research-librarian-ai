# Sustainable Catalyst Research Librarian AI

Sustainable Catalyst Research Librarian AI is the research-guidance, retrieval, evidence-planning, research-state, and reproducible research-intelligence layer of the Sustainable Catalyst platform.

**Current release:** v11.7.0 — Research Integrity & Methodological Audit

## Architecture

Research Librarian AI helps structure research without silently replacing source authority, scientific execution, or human judgment.

- **Research guidance and planning** — research questions, methodology plans, search strategies, study protocols, preregistration, statistical plans, causal designs, simulation/model studies, reproduction/replication planning, cross-study synthesis, meta-research planning, and research-integrity/methodological audit.
- **Retrieval and source intelligence** — deterministic and semantic retrieval, reranking, source identity, document parsing, citation context, federated discovery, and evidence-grounding workflows.
- **Research state** — projects, investigations, contexts, open questions, lifecycle state, collaboration rooms, activity, and durable workflow state.
- **Evidence intelligence** — source evaluation, evidence comparison, gaps, claims/counterclaims, contradictions, argument structures, review workflows, synthesis planning, methodological audit, discrepancy tracing, and remediation tracking.
- **AI research context** — retrieval/context manifests, RAG evaluation, AI experiment orchestration, benchmark/evaluation lineage, and reproducibility metadata.
- **Python/FastAPI backend** — production research services, durable jobs, PostgreSQL/pgvector knowledge indexing, and ancillary SQLite/local-state support.
- **WordPress interface** — public and institutional Research Librarian experience.
- **Knowledge Library integration** — Library remains authoritative for source ingestion, documents, and knowledge assets.
- **Platform Core integration** — Core remains authoritative for governed research/evidence objects, provenance, lineage, and cross-product exchange.
- **Workspace / Lab / Workbench handoffs** — specialist runtimes execute computation and experiments; the Librarian prepares and tracks governed handoffs.

The Librarian can organize, plan, retrieve, compare, and preserve research context. It does not automatically determine truth, accept claims, infer causality, certify validity, or substitute for specialist scientific execution.

## Repository layout

- `assets/` — browser and WordPress assets.
- `backend/` — FastAPI backend, retrieval, research-state services, durable jobs, migrations, and persistence.
- `data/` — tracked configuration and research-support data.
- `deploy/` — production deployment material.
- `docs/` — current architecture, methodology, integration, and operational documentation.
- `includes/` — WordPress/PHP application code.
- `knowledge/` — tracked knowledge/configuration resources.
- `scripts/` — active repository and operational tooling.
- `tests/` — active regression and release validation.
- `sustainable-catalyst-research-librarian-ai.php` — canonical WordPress plugin entry point.
- `compose.yml` — container orchestration definition.

## Release history

Historical release manifests, release notes, install notes, test reports, terminal-command files, one-off push/upgrade scripts, and per-version build documentation are intentionally not retained at the root of `main`.

The exact repository state immediately before the September 29, 2026 cleanup is preserved on:

`archive/pre-root-cleanup-2026-09-29-research-librarian-ai`

Git history continues to preserve prior source and release artifacts. Generated release material should live in release bundles or ignored staging directories rather than accumulating in the source-tree root.
