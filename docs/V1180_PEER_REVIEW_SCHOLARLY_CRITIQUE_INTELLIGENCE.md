# Research Librarian v11.8.0 — Peer Review & Scholarly Critique Intelligence

v11.8.0 adds a reproducible scholarly-critique layer above the existing v9.3 peer-review registry and the v11.7 research-integrity audit.

The older peer-review registry remains the durable study-level record for review rounds, reviewer assignments, reviews, author responses, revisions, replications, and editorial decisions. v11.8 does not replace it.

v11.8 organizes critique across manuscript/revision targets, research-integrity audits, methods/statistical/causal plans, synthesis and replication records, and specialist verification receipts. It creates a review workspace and reproducible critique package, not an automated editorial judge.

Objects include critique projects and target lineage, review rounds, critique dimensions, human reviewer comments, author responses, revision requirements, human-approved specialist verification requests/receipts, human-authored cross-review synthesis, cross-review matrices, issue registers, response coverage, structural readiness, editorial handoffs, Core candidates, and immutable snapshots.

No automatic accept/reject recommendation is generated. No reviewer is scored or ranked. No majority vote is interpreted as correctness. No scientific-validity or misconduct verdict is inferred. A completed revision requirement or verification receipt does not itself resolve a critique or imply acceptance. Editorial decisions remain explicit human actions.

Persistence: PostgreSQL production with SQLite local/test fallback. Migration 033. Durable job `peer-review-scholarly-critique-intelligence-snapshot`. Unified component type `scholarly-critique`.
