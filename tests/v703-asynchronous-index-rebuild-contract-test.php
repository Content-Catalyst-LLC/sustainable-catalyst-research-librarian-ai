<?php
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_v703_async_index_recovery_manifest.json' ), true );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.0.3' ),
    'version_constant' => false !== strpos( $module, "const VERSION = '7.0.3';" ),
    'background_hook' => false !== strpos( $module, "const BUILD_HOOK = 'sc_rl_v703_index_build_event'" ) && false !== strpos( $module, "run_index_build_job" ),
    'persistent_state' => false !== strpos( $module, "sc_rl_v703_index_build_state" ) && false !== strpos( $module, "sc-rl-async-index-build/7.0.3" ),
    'bounded_start' => false !== strpos( $module, 'start_index_build' ) && false !== strpos( $module, 'The browser can be closed while background batches continue.' ),
    'bounded_discovery' => false !== strpos( $module, 'source_batch_size' ) && false !== strpos( $module, 'process_build_discovery_step' ),
    'private_jsonl' => false !== strpos( $module, "'.jsonl'" ) && false !== strpos( $module, 'append_build_record' ),
    'saved_file_cursor' => false !== strpos( $module, 'sync_offset' ) && false !== strpos( $module, 'read_build_batch' ),
    'transactional_batches' => false !== strpos( $module, 'wordpress-async-full-sync-v7.0.3' ) && false !== strpos( $module, '\'batch_count\' => $batch_count' ),
    'atomic_previous_index' => false !== strpos( $module, 'current index remains live' ) && false !== strpos( $module, 'previously committed durable index was not replaced' ),
    'pause_resume_cancel' => false !== strpos( $module, 'pause_index_build' ) && false !== strpos( $module, 'resume_index_build' ) && false !== strpos( $module, 'cancel_index_build' ),
    'manual_step' => false !== strpos( $module, 'run_next_index_build_step' ) && false !== strpos( $module, 'Run Next Batch Now' ),
    'bounded_retry' => false !== strpos( $module, 'handle_build_error' ) && false !== strpos( $module, 'retry-scheduled' ),
    'stale_lock' => false !== strpos( $module, 'BUILD_LOCK_OPTION' ) && false !== strpos( $module, 'build_is_stale' ),
    'streamed_snapshot' => false !== strpos( $module, 'create_wordpress_snapshot_from_build_file' ) && false !== strpos( $module, 'gzwrite' ),
    'embedding_after_verify' => false !== strpos( $module, "'starting-embeddings'" ) && false !== strpos( $module, 'v7.0.3-async-index-build' ),
    'cron_disabled_guidance' => false !== strpos( $module, 'WP-Cron is disabled' ) && false !== strpos( $module, 'wp-cron.php' ),
    'async_admin_handler' => false !== strpos( $module, "isset( \$_POST['sc_rl_v703_start_build'] )" ) && false !== strpos( $module, "self::start_index_build( 'manual-admin' )" ),
    'manifest' => is_array( $manifest ) && '7.0.3' === ( $manifest['version'] ?? '' ) && ! empty( $manifest['capabilities']['transactional_index_swap'] ) && false === ( $manifest['paid_infrastructure_required'] ?? true ),
    'documentation' => is_file( $root . '/docs/V703_ASYNCHRONOUS_INDEX_REBUILD_RECOVERY.md' ),
);
$failed = array_keys( array_filter( $checks, function( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.0.3', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
