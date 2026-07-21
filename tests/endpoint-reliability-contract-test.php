<?php
/** Static contract checks for Research Librarian AI v6.5.1 endpoint and recovery reliability. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_cold_start_recovery_manifest_v6.3.1.json' ), true );

$checks = array(
    'plugin_version' => false !== strpos( $main, "const VERSION        = '7.0.2';" ),
    'durable_module' => false !== strpos( $module, 'final class SC_RL6_V630_Durable_Index' ),
    'nonce_route' => false !== strpos( $main, "'/nonce'" ) && false !== strpos( $main, 'handle_nonce_request' ),
    'single_nonce_retry' => false !== strpos( $js, 'function fetchWithNonce' ) && false !== strpos( $js, 'fetchWithNonce(url, options, false)' ),
    'rolling_rate_limit' => false !== strpos( $main, '$timestamps = get_transient( $key )' ) && false !== strpos( $main, '$timestamp > ( $now - $window )' ),
    'retry_after_header' => false !== strpos( $main, "'Retry-After'" ) && false !== strpos( $main, "'retry_after' => \$retry_after" ),
    'editor_rate_limit_exemption' => false !== strpos( $main, "'rate_limit_admin_exempt'" ) && false !== strpos( $main, "current_user_can( 'edit_posts' )" ),
    'diagnostics_routes' => false !== strpos( $module, "'/python/diagnostics'" ) && false !== strpos( $module, "'/python/manifest'" ) && false !== strpos( $module, "'/python/snapshots'" ),
    'recovery_routes' => false !== strpos( $module, "'/python/recover'" ) && false !== strpos( $module, "'/python/rollback'" ),
    'authenticated_health_test' => false !== strpos( $module, "'/v1/knowledge/summary'" ),
    'cold_start_diagnostic' => false !== strpos( $module, 'backend-cold-start' ),
    'empty_index_diagnostic' => false !== strpos( $module, 'index-empty' ),
    'wordpress_first_indexing' => strpos( $module, "get_post_types( array( 'public' => true )" ) < strpos( $module, '$saved_index = get_option( SC_RL6_Core::INDEX_OPTION' ),
    'transactional_full_sync' => false !== strpos( $module, "'mode' => 'transactional-replace'" ) && false !== strpos( $module, "'committed'" ),
    'incremental_queue' => false !== strpos( $module, 'QUEUE_OPTION' ) && false !== strpos( $module, 'sync_incremental_queue' ),
    'record_hashes' => false !== strpos( $module, "'content_hash'" ) && false !== strpos( $module, 'record_content_hash' ),
    'delete_tombstones' => false !== strpos( $models, 'deleted_ids: list[str]' ) && false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS tombstones' ),
    'wordpress_private_snapshot' => false !== strpos( $module, 'sc-research-librarian-private/index-snapshots' ) && false !== strpos( $module, 'Require all denied' ),
    'snapshot_integrity' => false !== strpos( $module, "hash_file( 'sha256'" ) && false !== strpos( $module, 'snapshot_checksum' ),
    'automatic_rehydration' => false !== strpos( $module, 'automatic-cold-start' ) && false !== strpos( $module, 'recover_backend_from_snapshot' ),
    'sqlite_runtime' => false !== strpos( $store, 'knowledge_index.sqlite3' ) && false !== strpos( $store, 'PRAGMA journal_mode=WAL' ),
    'staged_jobs' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS staging_records' ) && false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS sync_jobs' ),
    'atomic_commit' => false !== strpos( $store, 'BEGIN IMMEDIATE' ) && false !== strpos( $store, 'final_batch' ),
    'idempotent_jobs' => false !== strpos( $store, 'duplicate_batch' ) && false !== strpos( $store, 'str(existing["state"]) in {"completed", "completed-with-rejections"}' ),
    'runtime_snapshots' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS snapshots' ) && false !== strpos( $store, 'def rollback(' ),
    'runtime_snapshot_retention' => false !== strpos( $store, 'settings.max_runtime_snapshots' ) && false !== strpos( file_get_contents( $root . '/backend/app/config.py' ), 'SC_RL_MAX_RUNTIME_SNAPSHOTS' ),
    'legacy_json_migration' => false !== strpos( $store, 'def _migrate_legacy_json' ) && false !== strpos( $store, '.json.migrated' ),
    'batch_position_validation' => false !== strpos( $models, 'batch_index must not exceed batch_count' ) && false !== strpos( $models, '@model_validator' ),
    'manifest_endpoint' => false !== strpos( $backend, '@app.get("/v1/knowledge/manifest"' ),
    'rollback_endpoint' => false !== strpos( $backend, '@app.post("/v1/knowledge/rollback"' ),
    'terminal_black_background' => 1 === preg_match( '/\.sc-rl-ai__textarea\s*\{[^}]*background:\s*#000;/s', $css ),
    'terminal_green_text' => 1 === preg_match( '/\.sc-rl-ai__textarea\s*\{[^}]*color:\s*#7dff91;/s', $css ),
    'terminal_green_caret' => false !== strpos( $css, 'caret-color: #7dff91' ),
    'terminal_accessible_focus' => false !== strpos( $css, '.sc-rl-ai__textarea:focus-visible' ) && false !== strpos( $css, '0 0 0 4px rgba(125,255,145,.24)' ),
    'light_answer_surface' => false !== strpos( $css, '.sc-rl-ai__answer-card' ) && false !== strpos( $css, '--sc-rl-paper: #fff' ),
    'light_source_cards' => false !== strpos( $css, '.sc-rl-production-answer__source-card' ) && false !== strpos( $css, 'background: #fff' ),
    'release_manifest' => is_array( $manifest ) && '6.3.1' === ( $manifest['version'] ?? '' ),
    'backward_aliases' => false !== strpos( $module, "class_alias( 'SC_RL6_V630_Durable_Index', 'SC_RL6_V621_Endpoint_Reliability' )" ) && false !== strpos( $module, "class_alias( 'SC_RL6_V630_Durable_Index', 'SC_RL6_V620_Knowledge_Intelligence' )" ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
$result = array( 'version' => '7.0.2', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed );
echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
