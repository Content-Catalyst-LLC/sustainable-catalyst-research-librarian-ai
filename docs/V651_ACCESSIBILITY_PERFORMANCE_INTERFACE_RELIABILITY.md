# Research Librarian AI v6.5.1 — Accessibility, Performance, and Interface Reliability

## Purpose

v6.5.1 hardens the public research workspace introduced in v6.5.0. It does not change the evidence model, retrieval calibration, or durable index schema. The release improves keyboard and assistive-technology behavior, avoids unnecessary browser and WordPress requests, stages large answer rendering, and makes the interface more dependable across WordPress themes, mobile layouts, reduced-motion preferences, and high-contrast environments.

## Accessibility

- Research modes use a roving `tabindex` radio-group pattern.
- Arrow keys, Home, and End move among research modes.
- The question field exposes combobox/listbox semantics for indexed-title suggestions.
- Suggestions use stable option IDs, `aria-selected`, and `aria-activedescendant`.
- Arrow keys move through suggestions without moving focus away from the question field.
- Enter chooses the active suggestion; Escape closes the list.
- Status, progress, suggestion count, and final result availability are announced.
- The progress indicator exposes `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, and `aria-valuetext`.
- Focus moves to the completed workspace heading after an explicit research request.
- Endpoint failures receive alert semantics and programmatic focus.
- Browser prompt dialogs were replaced with an accessible, labeled feedback dialog.
- Reduced-motion and forced-colors rules preserve core operation.
- Mobile controls use a minimum 44-pixel target height.

## Performance

- Health responses are coalesced and cached for 45 seconds across multiple shortcode instances.
- Common-route responses are coalesced and cached for five minutes.
- Title suggestions are cached for five minutes in the browser.
- WordPress caches suggestions for five minutes against the current canonical ledger checksum.
- A changed index checksum automatically invalidates old suggestion entries.
- Stale suggestion requests are aborted while a visitor continues typing.
- Superseded answer and guided-path requests are aborted.
- Identical in-flight questions do not create duplicate requests.
- Direct answers render before secondary evidence and action cards.
- The public script is marked for deferred loading when the installed WordPress version supports script loading strategies.
- FastAPI enables gzip compression for responses of at least 900 bytes.
- Repeated cards use `content-visibility` where supported.

## Interface reliability

- Clipboard actions include a non-Clipboard-API fallback.
- Object URLs are revoked after a delay to avoid download failures in Safari-derived browsers.
- Form controls and buttons receive scoped theme-resistance rules.
- Sticky positioning accounts for the WordPress administrator bar.
- Mobile layouts collapse to one column and prevent horizontal overflow.
- Feedback submission no longer depends on `window.prompt`.
- Path-builder requests use the same cancellation and duplicate-request controls as the primary workspace.

## Compatibility

- SQLite remains schema version 6; no index migration is required.
- The public workspace response schema advances to `sc-research-librarian-public-workspace/1.1`.
- The v6.5.0 research modes, exports, continuity, citation verification, retrieval calibration, snapshots, and recovery controls remain compatible.
- The black-and-green question field and light answer/source surfaces are preserved.
- No paid database, vector service, or persistent Render disk is introduced.
