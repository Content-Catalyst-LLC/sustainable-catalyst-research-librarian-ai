<?php
/** Static release contract for v7.1.2 durable incremental index activation. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$config = file_get_contents( $root . '/backend/app/config.py' );
$docs = file_get_contents( $root . '/docs/V707_DURABLE_INCREMENTAL_INDEX_ACTIVATION.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_v707_durable_incremental_activation_manifest.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.1.2' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '7.1.2';" ),
    'durable_version' => false !== strpos( $module, "const VERSION = '7.1.2';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.1.2"' ),
    'schema_eleven' => false !== strpos( $store, 'SCHEMA_VERSION = 12' ),
    'index_schema_eleven' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/12.0' ),
    'no_background_tasks' => false === strpos( $backend, 'BackgroundTasks' ) && false === strpos( $backend, 'background_tasks.add_task' ),
    'commit_step_endpoint' => false !== strpos( $backend, '/v1/knowledge/sync/jobs/{job_id}/commit/step' ),
    'advance_method' => false !== strpos( $store, 'def advance_sync_commit' ),
    'activation_records_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS activation_records' ),
    'activation_chunks_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS activation_chunks' ),
    'record_cursor' => false !== strpos( $store, 'activation_cursor' ),
    'chunk_cursor' => false !== strpos( $store, 'chunk_cursor' ) && false !== strpos( $store, 'chunk_records_processed' ),
    'checksum_cursor' => false !== strpos( $store, 'checksum_cursor' ) && false !== strpos( $store, 'activation_checksum' ),
    'bounded_record_setting' => false !== strpos( $config, 'SC_RL_ACTIVATION_RECORD_BATCH_LIMIT' ),
    'bounded_chunk_setting' => false !== strpos( $config, 'SC_RL_ACTIVATION_CHUNK_RECORD_BATCH_LIMIT' ),
    'bounded_checksum_setting' => false !== strpos( $config, 'SC_RL_ACTIVATION_CHECKSUM_BATCH_LIMIT' ),
    'atomic_switch' => false !== strpos( $store, 'The only non-incremental operation is a database-local table' ) && false !== strpos( $store, 'DELETE FROM retrieval_chunks' ),
    'legacy_upgrade' => false !== strpos( $store, 'Upgrade v7.0.6 queued/activating jobs in place' ),
    'wordpress_step_request' => false !== strpos( $module, 'backend_advance_sync_commit' ) && false !== strpos( $module, '/commit/step' ),
    'backend_state_loss_replay' => false !== strpos( $module, 'backend-ephemeral-state-lost-before-activation' ),
    'shadow_record_metric' => false !== strpos( $module, 'Shadow records' ),
    'chunked_record_metric' => false !== strpos( $module, 'Chunked records' ),
    'verified_record_metric' => false !== strpos( $module, 'Verified records' ),
    'durable_step_metric' => false !== strpos( $module, 'Durable steps' ),
    'persistent_storage_guidance' => false !== strpos( $module, 'SC_RL_DATA_DIR=/var/data/sc-research-librarian' ),
    'documentation' => false !== strpos( $docs, 'Durable activation state machine' ) && false !== strpos( $docs, 'commit/step' ),
    'manifest' => is_array( $manifest ) && '7.0.7' === ( $manifest['version'] ?? '' ) && 11 === ( $manifest['sqlite_schema'] ?? 0 ) && false === ( $manifest['activation']['in_process_background_task'] ?? true ),
    'free_vector_database' => is_array( $manifest ) && false === ( $manifest['paid_infrastructure_required'] ?? true ),
);
$failed = array_keys( array_filter( $checks, static function ( $passed ) { return ! $passed; } ) );
echo json_encode( array(
    'version' => '7.1.2',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
