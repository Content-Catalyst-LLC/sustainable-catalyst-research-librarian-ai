# Research Librarian AI v6.2.1 — WordPress Indexing and Endpoint Reliability Patch

## Release purpose

v6.2.1 makes the existing WordPress + FastAPI architecture dependable before the retrieval stack expands. It fixes the public request path, makes full-library sync results visible, provides recovery controls, and introduces the requested terminal-style question field.

## Indexing behavior

The synchronization collector now processes canonical published WordPress posts first. Legacy route/index records are appended only when they contribute a URL that was not already represented. This prevents a summary-only record from masking the complete article body, headings, taxonomies, series metadata, article-map metadata, and parent relationship.

Every full synchronization creates a job report containing:

- job ID and timestamps
- eligible and missing post types
- eligible published posts
- collected and skipped records
- duplicate URLs
- accepted and rejected records
- per-post-type totals
- per-batch mode, sent count, accepted count, rejected count, state, and backend total
- the final backend response

The latest report and the previous 20 completed or failed reports are available through protected administrator endpoints.

## Endpoint diagnostics

Public and administrator states now distinguish:

- WordPress REST route unavailable
- expired or invalid WordPress nonce
- invalid WordPress JSON response
- WordPress server error
- Python backend not configured
- Python backend cold start
- Python backend unreachable
- Python backend server failure
- shared integration-key mismatch
- empty knowledge index
- Python-side rate limiting
- Gemini quota or provider unavailability
- public WordPress question limit

The public interface refreshes an expired nonce and retries the original question or title-suggestion request once. It never retries an arbitrary server failure.

## Rate limiting

The fixed hourly counter is replaced with a rolling time window. The response includes a structured reset time and a `Retry-After` header. Authenticated users with editorial capability are exempt by default so administrators can test the system without locking themselves out. The Python Intelligence screen shows active windows and includes a protected reset control.

## Repair operation

**Repair Endpoint and Resynchronize** performs these operations in order:

1. Rebuild the WP-Cron synchronization schedule.
2. Test the public Python `/health` route.
3. Test the authenticated `/v1/knowledge/summary` route to verify the integration key.
4. Collect the complete public WordPress knowledge set.
5. Replace and upsert the Python index in tracked batches.
6. Save final diagnostics and the synchronization report.

A failed stage is reported explicitly and does not claim that later stages succeeded.

## Public interface

Only the question-entry control receives the terminal treatment:

- black background
- green monospace text
- green caret
- subdued green placeholder
- visible green hover and focus states
- dark autofill correction

The answer panel, endpoint notices, evidence areas, title suggestions, and source cards remain light for long-form readability.

## Compatibility

v6.2.1 preserves the v6.2.0 option names, scheduled hook, and a backward class alias so existing settings, scheduled events, and cached administrator references continue to work after upgrade.
