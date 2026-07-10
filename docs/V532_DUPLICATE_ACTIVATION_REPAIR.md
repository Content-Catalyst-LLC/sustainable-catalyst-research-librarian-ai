# Research Librarian v5.3.2 — Duplicate Activation Notice Cleanup and Stale Active Plugin Repair

This build repairs the activation problem that can occur when an older versioned Research Librarian folder is deleted before the new stable-folder build is activated.

## Problem addressed

WordPress can retain stale `active_plugins` entries after plugin folders are deleted or replaced. That can leave the Research Librarian in a state where the Plugins screen shows one active copy, but the plugin still displays a duplicate-copy notice or REST routes return `rest_no_route`.

## Fixes

- Detects duplicate Research Librarian active-plugin paths.
- Detects stale active-plugin records whose files are missing.
- Displays exact paths causing the warning.
- Adds a nonce-protected one-click repair action.
- Preserves the current stable plugin folder where possible.
- Adds admin-only activation status and repair REST endpoints.
- Keeps the fatal-error guard without trapping the site in a permanent nag state.

## New endpoints

- `GET /wp-json/sc-research-librarian-ai/v1/activation/status`
- `POST /wp-json/sc-research-librarian-ai/v1/activation/repair`

## Verification

After repair, confirm:

```text
/wp-json/sc-research-librarian-ai/v1/health
```

The response should include:

```json
{"ok": true, "version": "5.3.2"}
```
