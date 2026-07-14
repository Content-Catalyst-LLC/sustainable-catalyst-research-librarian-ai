<?php
/** Static release contract checks for Research Librarian AI v6.5.1. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$config = file_get_contents( $root . '/backend/app/config.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$render = file_get_contents( $root . '/render.yaml' );
$docs = file_get_contents( $root . '/docs/V631_COLD_START_RECOVERY_HARDENING.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_cold_start_recovery_manifest_v6.3.1.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 6.6.1' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '6.6.1';" ),
    'module_version' => false !== strpos( $module, "const VERSION = '6.6.1';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "6.6.1"' ),
    'schema_version_six_or_newer' => false !== strpos( $store, 'SCHEMA_VERSION = 8' ),
    'startup_warmup_setting' => false !== strpos( $config, 'SC_RL_STARTUP_WARMUP_SECONDS' ),
    'stalled_job_setting' => false !== strpos( $config, 'SC_RL_STALLED_JOB_SECONDS' ),
    'rejection_limit_setting' => false !== strpos( $config, 'SC_RL_MAX_REJECTION_DETAILS' ),
    'startup_endpoint' => false !== strpos( $backend, '@app.get("/startup")' ),
    'startup_state' => false !== strpos( $backend, '"startup_state"' ) && false !== strpos( $models, 'startup_state: str' ),
    'startup_phase' => false !== strpos( $backend, '"startup_phase"' ) && false !== strpos( $models, 'startup_phase: str' ),
    'startup_progress' => false !== strpos( $backend, '"startup_progress"' ) && false !== strpos( $models, 'startup_progress: int' ),
    'startup_uptime' => false !== strpos( $backend, 'uptime_seconds' ) && false !== strpos( $models, 'service_started_utc: str' ),
    'startup_ready' => false !== strpos( $models, 'ready: bool' ),
    'maintenance_endpoint' => false !== strpos( $backend, '@app.post("/v1/knowledge/maintenance"' ),
    'snapshot_validation_endpoint' => false !== strpos( $backend, '@app.get("/v1/knowledge/snapshots/validate"' ),
    'stalled_detection' => false !== strpos( $store, 'def repair_stalled_jobs' ) && false !== strpos( $store, "state='stalled'" ),
    'startup_repairs_stalled' => false !== strpos( $store, 'self.repair_stalled_jobs(settings.stalled_job_seconds, purge_staging=True)' ),
    'rejection_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS sync_rejections' ),
    'raw_record_validation' => false !== strpos( $models, 'records: list[dict[str, Any]]' ) && false !== strpos( $store, 'KnowledgeRecord.model_validate(raw)' ),
    'rejected_record_response' => false !== strpos( $models, 'rejected_records: list[dict[str, Any]]' ) && false !== strpos( $backend, 'rejected_records=result.rejected_records' ),
    'completed_with_rejections' => false !== strpos( $store, 'completed-with-rejections' ),
    'invalid_record_prior_copy_protection' => false !== strpos( $store, 'protected_ids' ),
    'runtime_snapshot_validation' => false !== strpos( $store, 'def validate_snapshots' ) && false !== strpos( $store, 'record checksum mismatch' ),
    'rollback_integrity_block' => false !== strpos( $backend, 'HTTPException(status_code=409' ),
    'retry_hook' => false !== strpos( $module, "SYNC_RETRY_HOOK" ) && false !== strpos( $module, 'run_sync_retry' ),
    'bounded_retry' => false !== strpos( $module, "'max_retry_attempts' => 5" ) && false !== strpos( $module, 'retry_max_seconds' ),
    'exponential_backoff' => false !== strpos( $module, 'pow( 2, max( 0, absint( $attempt ) - 1 ) )' ),
    'retry_exhaustion' => false !== strpos( $module, "'state' => 'exhausted'" ),
    'recovery_state' => false !== strpos( $module, 'RECOVERY_STATE_OPTION' ) && false !== strpos( $module, 'recovery_state()' ),
    'recovery_phases' => false !== strpos( $module, "'phase' => 'verifying-snapshot'" ) && false !== strpos( $module, "'phase' => 'verifying-commit'" ),
    'recovery_progress_public' => false !== strpos( $module, "'recovery_progress' => self::recovery_state()" ),
    'wordpress_snapshot_file_hash' => false !== strpos( $module, "hash_file( 'sha256'" ),
    'wordpress_snapshot_record_count' => false !== strpos( $module, 'failed its record-count validation' ),
    'wordpress_snapshot_duplicate_id' => false !== strpos( $module, 'duplicate record identifier' ),
    'wordpress_snapshot_record_hash' => false !== strpos( $module, 'content-hash validation' ),
    'wordpress_snapshot_checksum' => false !== strpos( $module, 'record checksum validation' ),
    'wordpress_snapshot_validation_action' => false !== strpos( $module, 'Validate Snapshots' ) && false !== strpos( $module, 'handle_snapshot_validation' ),
    'stalled_repair_action' => false !== strpos( $module, 'Repair Stalled Jobs' ),
    'clear_retry_action' => false !== strpos( $module, 'Clear Pending Retries' ),
    'operations_export' => false !== strpos( $module, 'Export Sync and Recovery Log' ) && false !== strpos( $module, 'handle_log_export' ),
    'alert_state' => false !== strpos( $module, 'ALERT_STATE_OPTION' ) && false !== strpos( $module, 'register_public_alert' ),
    'alert_suppression_window' => false !== strpos( $module, 'alert_suppression_minutes' ),
    'js_suppresses_duplicate_notice' => false !== strpos( $js, 'endpointStatus.suppress_notice' ),
    'js_startup_progress' => false !== strpos( $js, 'payload.startup_progress' ) && false !== strpos( $js, 'payload.recovery_progress' ),
    'render_warmup_setting' => false !== strpos( $render, 'SC_RL_STARTUP_WARMUP_SECONDS' ),
    'render_stalled_setting' => false !== strpos( $render, 'SC_RL_STALLED_JOB_SECONDS' ),
    'release_documentation' => false !== strpos( $docs, 'Failed-record isolation' ) && false !== strpos( $docs, 'Snapshot-integrity contract' ),
    'release_manifest' => is_array( $manifest ) && '6.3.1' === ( $manifest['version'] ?? '' ) && 4 === ( $manifest['backend_schema_version'] ?? 0 ),
    'free_tier_compatibility' => is_array( $manifest ) && false === ( $manifest['compatibility']['paid_database_required'] ?? true ),
    'backward_alias' => false !== strpos( $module, "SC_RL6_V631_Cold_Start_Recovery_Hardening" ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array(
    'version' => '6.6.1',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
