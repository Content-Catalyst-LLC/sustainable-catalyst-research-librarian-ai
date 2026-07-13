<?php
/** Static contract checks for Research Librarian AI v6.2.1 endpoint reliability. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v621-endpoint-reliability.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_endpoint_reliability_manifest_v6.2.1.json' ), true );

$checks = array(
    'plugin_version' => false !== strpos( $main, "const VERSION        = '6.2.1';" ),
    'reliability_module' => false !== strpos( $module, 'final class SC_RL6_V621_Endpoint_Reliability' ),
    'nonce_route' => false !== strpos( $main, "'/nonce'" ) && false !== strpos( $main, 'handle_nonce_request' ),
    'nonce_endpoint_exposed' => false !== strpos( $main, 'data-nonce-endpoint' ),
    'single_nonce_retry' => false !== strpos( $js, 'function fetchWithNonce' ) && false !== strpos( $js, 'fetchWithNonce(url, options, false)' ),
    'rolling_rate_limit' => false !== strpos( $main, '$timestamps = get_transient( $key )' ) && false !== strpos( $main, '$timestamp > ( $now - $window )' ),
    'retry_after_header' => false !== strpos( $main, "'Retry-After'" ) && false !== strpos( $main, "'retry_after' => \$retry_after" ),
    'editor_rate_limit_exemption' => false !== strpos( $main, "'rate_limit_admin_exempt'" ) && false !== strpos( $main, "current_user_can( 'edit_posts' )" ),
    'rate_limit_status_route' => false !== strpos( $main, "'/rate-limit/status'" ),
    'rate_limit_reset_route' => false !== strpos( $main, "'/rate-limit/reset'" ),
    'rate_limit_admin_button' => false !== strpos( $module, 'Reset Public Rate Limits' ),
    'diagnostics_route' => false !== strpos( $module, "'/python/diagnostics'" ),
    'sync_report_route' => false !== strpos( $module, "'/python/sync-report'" ),
    'repair_route' => false !== strpos( $module, "'/python/repair'" ),
    'authenticated_health_test' => false !== strpos( $module, "'/v1/knowledge/summary'" ),
    'integration_key_diagnostic' => false !== strpos( $module, 'integration-key-mismatch' ),
    'cold_start_diagnostic' => false !== strpos( $module, 'backend-cold-start' ),
    'empty_index_diagnostic' => false !== strpos( $module, 'index-empty' ),
    'wp_cron_diagnostic' => false !== strpos( $module, "'next_run_utc'" ) && false !== strpos( $module, "'wp_cron_disabled'" ),
    'wordpress_first_indexing' => strpos( $module, 'get_post_types( array( \'public\' => true )' ) < strpos( $module, '$saved_index = get_option( SC_RL6_Core::INDEX_OPTION' ),
    'duplicate_url_reporting' => false !== strpos( $module, "'duplicate_urls'" ),
    'per_batch_reporting' => false !== strpos( $module, "'accepted_records'" ) && false !== strpos( $module, "'rejected_records'" ) && false !== strpos( $module, "'batch_count'" ),
    'sync_history' => false !== strpos( $module, 'SYNC_HISTORY_OPTION' ) && false !== strpos( $module, 'array_slice( $history, -20 )' ),
    'terminal_black_background' => 1 === preg_match( '/\.sc-rl-ai__textarea\s*\{[^}]*background:\s*#000;/s', $css ),
    'terminal_green_text' => 1 === preg_match( '/\.sc-rl-ai__textarea\s*\{[^}]*color:\s*#7dff91;/s', $css ),
    'terminal_green_caret' => false !== strpos( $css, 'caret-color: #7dff91' ),
    'terminal_monospace' => false !== strpos( $css, '"SFMono-Regular", Consolas' ),
    'terminal_placeholder' => false !== strpos( $css, '.sc-rl-ai__textarea::placeholder' ) && false !== strpos( $css, 'rgba(125,255,145,.64)' ),
    'terminal_accessible_focus' => false !== strpos( $css, '.sc-rl-ai__textarea:focus-visible' ) && false !== strpos( $css, '0 0 0 4px rgba(125,255,145,.24)' ),
    'light_answer_surface' => false !== strpos( $css, '.sc-rl-ai__answer-card' ) && false !== strpos( $css, '--sc-rl-paper: #fff' ),
    'light_source_cards' => false !== strpos( $css, '.sc-rl-production-answer__source-card' ) && false !== strpos( $css, 'background: #fff' ),
    'endpoint_notice_in_production_answer' => false !== strpos( $js, 'renderAnswerUx(answerUx, data, endpointNotice + renderedAnswer)' ),
    'backend_sync_job_fields' => false !== strpos( $models, 'job_id: str' ) && false !== strpos( $models, 'batch_index: int' ) && false !== strpos( $models, 'batch_count: int' ),
    'backend_accept_reject_fields' => false !== strpos( $models, 'accepted: int' ) && false !== strpos( $models, 'rejected: int' ),
    'backend_populates_sync_fields' => false !== strpos( $backend, 'accepted=len(payload.records)' ) && false !== strpos( $backend, 'job_id=payload.job_id' ),
    'release_manifest' => is_array( $manifest ) && '6.2.1' === ( $manifest['version'] ?? '' ),
    'backward_class_alias' => false !== strpos( $module, "class_alias( 'SC_RL6_V621_Endpoint_Reliability', 'SC_RL6_V620_Knowledge_Intelligence' )" ),
);

$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
$result = array(
    'version' => '6.2.1',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
);
echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
