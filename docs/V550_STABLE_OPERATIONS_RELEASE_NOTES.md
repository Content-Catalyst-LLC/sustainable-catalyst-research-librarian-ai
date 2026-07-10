# Research Librarian v5.5.0 — Stable Operations Polish and Release Notes

Version 5.5.0 closes the Research Librarian 5.x public-experience roadmap with an operational readiness and release-documentation layer.

## Operational readiness

The new **Settings → Research Librarian Operations** screen provides required and recommended checks for WordPress and PHP support, database connectivity, writable storage, duplicate plugin activation, scheduled operations, index maintenance, integration contracts, Workbench and Decision Studio destination availability, release manifests, and recovery assets.

Checks can be run manually and are also scheduled daily. Results are stored as bounded operational state and published as privacy-minimized `librarian.operations_checked` platform events.

## Migration and recovery validation

The release stores a versioned operations schema, provides repeatable migration validation, verifies that recovery assets are present, and preserves the existing backup, snapshot, and restoration tooling from the v4.1 recovery layer.

## Public release notes

Use:

```text
[sc_research_librarian_release_notes]
```

A limited public operational summary is available through:

```text
[sc_research_librarian_operations_status]
```

Neither shortcode exposes credentials, private diagnostics, personal data, or raw visitor conversations.

## REST operations

Administrator-only:

- `GET /wp-json/sc-research-librarian/v1/operations/status`
- `POST /wp-json/sc-research-librarian/v1/operations/check`
- `GET /wp-json/sc-research-librarian/v1/operations/export`

Public:

- `GET /wp-json/sc-research-librarian/v1/operations/release-notes`

## Release boundary

A successful readiness report is an operational signal, not an automated deployment approval. Administrators remain responsible for reviewing integrations, privacy settings, backups, production pages, and destination behavior before release.
