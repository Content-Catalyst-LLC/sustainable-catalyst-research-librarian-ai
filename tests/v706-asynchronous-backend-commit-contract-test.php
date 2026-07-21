<?php
/** Static release contract for v7.0.7 asynchronous backend commit recovery. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$docs = file_get_contents( $root . '/docs/V706_ASYNCHRONOUS_BACKEND_COMMIT_AMBIGUOUS_FAILURE_RECOVERY.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_v706_async_backend_commit_manifest.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.0.7' ),
    'durable_version' => false !== strpos( $module, "const VERSION = '7.0.7';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.0.7"' ),
    'defer_commit_contract' => false !== strpos( $models, 'defer_commit: bool = False' ),
    'sync_passes_defer_commit' => false !== strpos( $backend, 'defer_commit=payload.defer_commit' ),
    'commit_endpoint' => false !== strpos( $backend, '/v1/knowledge/sync/jobs/{job_id}/commit' ),
    'no_in_process_background_task' => false === strpos( $backend, 'background_tasks.add_task' ) && false === strpos( $backend, 'BackgroundTasks' ),
    'ready_to_commit_state' => false !== strpos( $store, "state='ready-to-commit'" ),
    'commit_queue_method' => false !== strpos( $store, 'def queue_sync_commit' ),
    'bounded_step_method' => false !== strpos( $store, 'def advance_sync_commit' ),
    'commit_stalled_detection' => false !== strpos( $store, 'state = "commit-stalled"' ),
    'commit_status_fields' => false !== strpos( $store, '"commit_progress"' ) && false !== strpos( $store, '"activation_records"' ) && false !== strpos( $store, '"indexed_chunks"' ),
    'wordpress_deferred_batches' => false !== strpos( $module, "'defer_commit' => true" ),
    'wordpress_queue_stage' => false !== strpos( $module, "'queuing-backend-commit'" ),
    'wordpress_poll_stage' => false !== strpos( $module, "'waiting-backend-commit'" ),
    'wordpress_commit_queue_request' => false !== strpos( $module, 'backend_queue_sync_commit' ),
    'ambiguous_final_reconciliation' => false !== strpos( $module, 'The final staging response was ambiguous' ),
    'empty_http_detail' => false !== strpos( $module, "returned an empty response for" ),
    'admin_activation_metric' => false !== strpos( $module, 'Backend activation' ),
    'admin_activation_progress' => false !== strpos( $module, 'Activation progress' ),
    'admin_shadow_records' => false !== strpos( $module, 'Shadow records' ),
    'admin_chunk_metric' => false !== strpos( $module, 'Retrieval chunks' ),
    'release_docs' => false !== strpos( $docs, 'WordPress now stages every source batch' ) && false !== strpos( $docs, 'commit-stalled' ),
    'release_manifest' => is_array( $manifest ) && '7.0.6' === ( $manifest['version'] ?? '' ) && true === ( $manifest['transaction_activation']['deferred_final_commit'] ?? false ),
    'free_tier' => is_array( $manifest ) && false === ( $manifest['paid_infrastructure_required'] ?? true ),
);
$failed = array_keys( array_filter( $checks, static function ( $passed ) { return ! $passed; } ) );
echo json_encode( array(
    'version' => '7.0.7',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
