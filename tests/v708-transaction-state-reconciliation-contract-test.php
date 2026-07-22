<?php
/** Static release contract for v7.1.2 transaction-state reconciliation and durable recovery. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$config = file_get_contents( $root . '/backend/app/config.py' );
$docs = file_get_contents( $root . '/docs/V708_TRANSACTION_STATE_RECONCILIATION_DURABLE_RECOVERY.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_v708_transaction_state_reconciliation_manifest.json' ), true );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.1.2' ),
    'durable_version' => false !== strpos( $module, "const VERSION = '7.1.2';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.1.2"' ),
    'schema_twelve' => false !== strpos( $store, 'SCHEMA_VERSION = 12' ),
    'reconcile_endpoint' => false !== strpos( $backend, '/v1/knowledge/sync/jobs/{job_id}/reconcile' ),
    'reconcile_model' => false !== strpos( file_get_contents( $root . '/backend/app/models.py' ), 'class SyncReconcileRequest' ),
    'backend_classifier' => false !== strpos( $store, 'def reconcile_sync_job' ) && false !== strpos( $store, 'empty-shell' ) && false !== strpos( $store, 'batch-count-mismatch' ),
    'zero_batch_rejected' => false !== strpos( $store, 'contains no staged source batches' ),
    'wordpress_expected_count' => false !== strpos( $module, 'expected_batch_count' ) && false !== strpos( $module, 'local_reconciliation_status' ),
    'empty_missing_not_success' => false !== strpos( $module, "'transaction_state' => 'empty-shell'" ) || false !== strpos( $module, "\$transaction_state = 'empty-shell'" ),
    'missing_batch_replay' => false !== strpos( $module, 'process_build_missing_batch_replay_step' ) && false !== strpos( $module, 'sync_batch_offsets' ),
    'fresh_recovery_generation' => false !== strpos( $module, 'recovery_generation' ) && false !== strpos( $module, 'Durable recovery restarted with a fresh reconciliation generation' ),
    'counter_reset' => false !== strpos( $module, "\$state['transaction_replay_count'] = 0" ),
    'diagnostic_error' => false !== strpos( $module, 'missing batches: ' ) && false !== strpos( $module, 'none reported' ),
    'admin_diagnostics' => false !== strpos( $module, 'Transaction state' ) && false !== strpos( $module, 'Recovery action' ) && false !== strpos( $module, 'Transaction ID' ),
    'persistent_disk_autodetect' => false !== strpos( $config, 'render_disk = Path("/var/data")' ),
    'documentation' => false !== strpos( $docs, 'empty `missing_batches` array' ),
    'manifest' => is_array( $manifest ) && '7.1.2' === ( $manifest['version'] ?? '' ) && 12 === ( $manifest['sqlite_schema'] ?? 0 ),
);
$failed = array_keys( array_filter( $checks, static function ( $passed ) { return ! $passed; } ) );
echo json_encode( array( 'version' => '7.1.2', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
