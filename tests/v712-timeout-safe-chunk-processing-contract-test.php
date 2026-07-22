<?php
/** Static release contract for v7.1.2 timeout-safe chunk processing. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$config = file_get_contents( $root . '/backend/app/config.py' );
$store = file_get_contents( $root . '/backend/app/postgres_store.py' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_timeout_safe_chunk_manifest_v7.1.2.json' ), true );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.1.2' ),
    'module_version' => false !== strpos( $module, "const VERSION = '7.1.2';" ),
    'small_default_batch' => false !== strpos( $config, 'SC_RL_POSTGRES_ACTIVATION_CHUNK_RECORD_BATCH_LIMIT", 5' ),
    'bulk_chunk_insert' => false !== strpos( $store, 'jsonb_to_recordset' ),
    'record_checkpoint' => false !== strpos( $store, 'Persist after every record' ),
    'advisory_lock' => false !== strpos( $store, 'pg_try_advisory_lock' ),
    'timeout_detection' => false !== strpos( $module, 'is_backend_timeout_error' ),
    'timeout_poll' => false !== strpos( $module, 'backend_timeout_poll_only' ),
    'visible_batch' => false !== strpos( $module, 'Current chunk batch' ),
    'manifest' => is_array( $manifest ) && '7.1.2' === ( $manifest['version'] ?? '' ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.1.2', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
