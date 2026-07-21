# Sustainable Catalyst Research Librarian AI v7.0.8

A site-scoped connected research intelligence platform with deterministic transaction reconciliation, restart-safe index activation, verified retrieval, and a visible public research workspace. See `docs/V708_TRANSACTION_STATE_RECONCILIATION_DURABLE_RECOVERY.md`.

## v7.0.8 highlights

- Distinguishes a complete 24/24 backend transaction from an empty transaction that merely reports no missing batches
- Compares the backend batch manifest with the WordPress-owned expected batch count
- Adds an authenticated transaction-reconciliation endpoint with explicit recovery actions
- Replays only missing batches when the durable byte-offset ledger is available
- Recreates missing, empty, mismatched, or indeterminate transactions from the preserved WordPress staging file
- Resets replay counters after successful reconciliation
- Starts a new recovery generation when resuming an exhausted v7.0.7 recovery job
- Rejects activation of zero-batch backend transactions
- Exposes transaction state, recovery action, transaction ID, storage path, and persistence diagnostics
- Automatically uses a writable `/var/data` Render disk when available
- Preserves the previous active index until the replacement is verified and switched atomically

## Architecture

WordPress remains the canonical publishing, administration, identity, and recovery boundary. FastAPI provides durable SQLite research state, retrieval, project services, cross-product handoffs, governance, and backup verification. Generation is isolated behind `sc-generation-adapter/1.0`; retrieval and project continuity remain usable when generation is unavailable.

## Public shortcodes

- `[sustainable_catalyst_research_librarian_ai]`
- `[sc_research_librarian]`
- `[sc_connected_research_workspace]`
- `[sc_research_projects_summary]`
- `[sc_connected_research_platform_status]`
- `[sc_research_librarian_methodology]`
- `[sc_research_librarian_governance_status]`
- `[sc_research_librarian_platform_handoffs]`

## Backend resources

`/v1/projects`, `/v1/investigations`, `/v1/projects/entities`, `/v1/workflows/template`, `/v1/research/contradictions`, `/v1/research/uncertainties`, `/v1/projects/{project_id}/backup`, `/v1/platform/backups/import`, `/v1/platform/api`, and `/v1/platform/summary`.

## Runtime

- Python 3.12.12
- FastAPI
- SQLite schema 12
- WordPress 6.0+
- No paid vector database is required; persistent backend storage is recommended for strongest restart durability

See `docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md` and `docs/INSTALL.md`.
