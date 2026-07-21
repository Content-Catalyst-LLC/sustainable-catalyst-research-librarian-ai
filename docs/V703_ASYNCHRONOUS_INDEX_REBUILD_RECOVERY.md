# Research Librarian AI v7.0.3

## Asynchronous Index Rebuild and Recovery

v7.0.3 removes the full knowledge-index rebuild from the WordPress admin request. The primary button now creates a persistent job and returns immediately. Source discovery, transactional synchronization, verification, snapshot creation, and semantic-index scheduling continue in bounded, resumable passes.

## Why this repair exists

The v7.0.2 one-click workflow performed source collection, synchronization, verification, embedding tests, and several embedding batches in one request. On production WordPress hosting, that could exceed PHP memory or execution-time limits and produce a critical-error screen.

## Workflow

1. Test the authenticated Python bridge.
2. Discover one bounded page of public WordPress records per pass.
3. Append normalized records to a private JSONL staging file.
4. Determine the exact record and batch counts.
5. Send one transactional replacement batch per pass.
6. Keep the existing Python index active while batches are staged.
7. Commit the replacement only after the final batch arrives.
8. Verify that the committed index is nonempty.
9. Stream a private canonical recovery snapshot without loading all records into PHP memory.
10. Test and schedule the resumable Gemini embedding queue.

## Recovery controls

The administration screen exposes Pause, Resume, Run Next Batch Now, and Cancel. A failed build retains its file cursor and can resume after configuration is corrected. A cancelled or failed replacement never removes the previously committed durable index.

When WP-Cron is disabled, the operator can process one bounded step manually or configure a real server cron request to `wp-cron.php`.

## Operational state

The persistent build record stores the job identifier, stage, progress, source cursor, file cursor, discovered and synchronized counts, retry count, warnings, and last error. A short-lived lock prevents duplicate workers. Stale jobs can be resumed or replaced after the configured threshold.

## Free-tier boundary

The repair uses WordPress private uploads, WP-Cron, the existing Render service, and the existing SQLite transactional store. No paid queue, worker, or database service is required.
