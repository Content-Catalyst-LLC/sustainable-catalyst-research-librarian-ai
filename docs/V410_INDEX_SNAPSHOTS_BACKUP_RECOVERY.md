# Research Librarian v4.1.0 — Index Snapshots, Backup, and Recovery Readiness

Version 4.1.0 adds a recovery layer for the Sustainable Catalyst Research Librarian.

The purpose is operational safety. Before a major index rebuild, embedding run, plugin upgrade, sitemap sync, or migration, an administrator can create an exportable snapshot of the Research Librarian knowledge-index state and related operational status.

## What it adds

- Admin recovery snapshot creation
- Snapshot list and recovery dashboard
- Public-safe recovery summary
- Admin-only recovery export JSON
- Dry-run restore planning
- Snapshot deletion
- Recovery status endpoint
- Manifest entry for release auditing

## Snapshot contents

A recovery snapshot stores:

- Knowledge index records
- Embedding status summary
- Evaluation status
- Handoff status
- Governance status
- Maintenance status
- Snapshot creation reason
- Record counts and route/type coverage

Embedding vectors are intentionally stripped from snapshots. This keeps exports manageable and avoids creating very large WordPress options or JSON files. After restoring an index snapshot, Gemini embeddings should be regenerated.

## New endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/recovery/status
POST /wp-json/sc-research-librarian-ai/v1/recovery/create
GET  /wp-json/sc-research-librarian-ai/v1/recovery/export
POST /wp-json/sc-research-librarian-ai/v1/recovery/restore
POST /wp-json/sc-research-librarian-ai/v1/recovery/delete
```

Create, restore, export, and delete actions are admin-only where appropriate. Restore defaults to dry-run mode.

## New shortcodes

```text
[sc_research_librarian mode="recovery-summary" title="Research Librarian Recovery Readiness"]
[sc_research_librarian_recovery_summary title="Research Librarian Recovery Readiness"]
```

## Recommended use

Create a recovery snapshot before:

- Rebuilding the knowledge index
- Running a full Gemini embedding job
- Changing sitemap sync settings
- Running scheduled maintenance manually
- Installing a major plugin upgrade
- Migrating the site or plugin state

## Restore note

The restore endpoint supports dry-run planning by default. Actual restore should be used only after reviewing the exported recovery JSON. Embeddings should be regenerated after restore.
