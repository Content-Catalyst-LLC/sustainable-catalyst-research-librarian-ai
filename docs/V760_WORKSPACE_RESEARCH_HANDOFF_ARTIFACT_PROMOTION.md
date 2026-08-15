# v7.6.0 — Workspace Research Handoff & Artifact Promotion

Research Librarian AI v7.6.0 adds a governed bridge from Library and Research Room research into Sustainable Catalyst Workspace. The bridge prepares a durable, versioned handoff packet; it does **not** silently create, publish, or import a Workspace artifact.

## Artifact promotion contracts

A researcher can prepare one of five Workspace seed types:

- **Notebook** — research context, sources, open questions, research notes, and room collaboration.
- **Evidence Set** — sources, evidence-quality metadata, contradictions, and provenance.
- **Analysis** — research question/context, evidence, gaps, contradictions, assumptions, and open questions.
- **Document** — research context, outline seed, citations, sources, and open questions.
- **Citation Pack** — citation metadata, sources, fingerprints, and provenance.

The canonical handoff contract is `sc-workspace-research-handoff/1.0`, wrapped by promotion record `sc-workspace-artifact-promotion/1.0`. Workspace import is explicitly governed by `sc-workspace-research-import/1.0`.

## Provenance boundary

Promotion is a snapshot of selected research state. It is not publication, editorial approval, or a truth judgment. Source ownership, Library scope, object type, source fingerprint, project relationship, and Research Room attribution remain attached to the packet. Workspace may not silently reclassify a personal or room-shared source as Sustainable Catalyst editorial material.

Personal v7.4 research state and shared v7.5 room state remain distinct. A room handoff can carry both bounded representations, but it does not merge their authorship or provenance.

Rejected sources remain in the research ledger but are excluded from promotion by default. A researcher may deliberately include them when the artifact requires an audit trail or counter-evidence review.

## Explicit import and receipts

The WordPress interface exposes **Promote to Workspace** as an outbox operation. Preparing a packet does not claim that Workspace imported it. The researcher can download the fingerprinted JSON handoff and open Workspace as a separate action.

An optional receipt may later mark the promotion `exported` or `imported`. The receipt must match the exact packet fingerprint. A receipt confirms transfer only; it does not confirm publication, editorial endorsement, or factual validity.

## Authorization

WordPress resolves the signed-in owner/actor identity server-side. The browser cannot select a different owner or receipt actor. Context ownership, project access, room membership, and selected Library-object access are checked before the backend receives the promotion request.

A Research Room participant may promote shared evidence available through that room, but the packet retains the original contributor/source owner and original Library scope.

## Persistence and recovery

The ancillary workspace SQLite schema advances from **15 to 16** with `research_workspace_promotions`. Promotion packets and receipts are included in project backup/import.

The production Neon/Postgres knowledge index remains `sc-research-librarian-knowledge-index/13.0`. **No Neon/Postgres knowledge-index migration is required for v7.6.0.**

## Contract versions

- Research Librarian AI: `7.6.0`
- Connected Research API: `sc-connected-research-api/1.5`
- Public workspace: `sc-research-librarian-public-workspace/2.5`
- Ancillary SQLite schema: `16`
- Knowledge index: `sc-research-librarian-knowledge-index/13.0`
- Promotion: `sc-workspace-artifact-promotion/1.0`
- Handoff packet: `sc-workspace-research-handoff/1.0`
- Receipt: `sc-workspace-promotion-receipt/1.0`
- Workspace import: `sc-workspace-research-import/1.0`
