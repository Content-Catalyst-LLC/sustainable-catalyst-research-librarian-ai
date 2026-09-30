# Research Librarian AI v11.7.0 — Research Integrity & Methodological Audit

v11.7.0 adds a durable, review-centered audit layer for tracing whether reported research methods, analyses, synthesis decisions, and reproducibility claims remain connected to declared plans and evidence.

## Scope

The Librarian can bind an audit to research-question plans, methodology plans, evidence-search strategies, systematic reviews, preregistered protocols, statistical plans, causal designs, simulation studies, reproduction/replication projects, cross-study synthesis projects, scholarly objects, datasets, code artifacts, sources, and governed Core references.

It records:

- audit targets with lineage fingerprints when a supported upstream object can be resolved;
- reviewer-authored audit criteria;
- expected-versus-observed methodological observations;
- reviewer-authored findings and domain-scoped methodological appraisals;
- explicit finding dispositions;
- specialist verification requests, human approval, and returned execution receipts;
- remediation actions and closure status;
- traceability matrices, discrepancy registers, methodological profiles without composite scores, Core promotion candidates, and immutable snapshots.

## Human and scientific boundaries

Research Integrity & Methodological Audit is not an automated misconduct detector or validity classifier. A discrepancy is a signal for review. Findings and appraisals remain attributed to human reviewers. Specialist runtimes execute requested verification work. Execution receipts are observations, not integrity verdicts.

The runtime does not automatically infer misconduct, invalidate research, recommend retraction, rank methods, reject claims, suppress evidence, infer causality, block publication, execute verification, or promote truth. Platform Core remains the governed research-object authority.

## Cross-product architecture

- **Research Librarian** owns audit structure, review lineage, findings, appraisals, remediation, verification handoffs/receipts, and snapshots.
- **Workspace / Research Lab / Workbench** execute approved specialist checks and return artifacts/receipts.
- **Platform Core** owns governed promoted research/audit objects and cross-product lineage.
- **Knowledge Library** remains authoritative for source ingestion and document/source intelligence.

## Durable job

`research-integrity-methodological-audit-snapshot`

## Unified environment binding

`research-integrity-audit`
