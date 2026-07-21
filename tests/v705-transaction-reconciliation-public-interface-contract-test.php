<?php
/** Static release contract for v7.0.5 transaction reconciliation and visible public controls. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$docs = file_get_contents( $root . '/docs/V705_TRANSACTION_RECONCILIATION_PUBLIC_INTERFACE.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_v705_transaction_reconciliation_public_interface_manifest.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.0.5' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '7.0.5';" ),
    'durable_version' => false !== strpos( $module, "const VERSION = '7.0.5';" ),
    'backend_status_endpoint' => false !== strpos( $backend, '/v1/knowledge/sync/jobs/{job_id}' ),
    'backend_reset_endpoint' => false !== strpos( $backend, '@app.delete("/v1/knowledge/sync/jobs/{job_id}"' ),
    'store_status_method' => false !== strpos( $store, 'def sync_job_status' ),
    'store_missing_batches' => false !== strpos( $store, '"missing_batches": missing' ),
    'reconciliation_stage' => false !== strpos( $module, "case 'reconciling-transaction':" ),
    'durable_replay' => false !== strpos( $module, 'Replaying the durable WordPress staging file as a fresh transaction' ),
    'repair_button' => false !== strpos( $module, 'Repair and Resume Commit' ),
    'backend_retained_metric' => false !== strpos( $module, 'Backend retained' ),
    'mode_descriptions' => false !== strpos( $main, '<small>Locate a specific page or article</small>' ) && false !== strpos( $main, '<small>Build a reviewable workflow</small>' ),
    'visible_primary_action' => false !== strpos( $main, '>Start Research</button>' ),
    'visible_css_release' => false !== strpos( $css, 'v7.0.5 — visible research controls' ),
    'single_column_workspace' => false !== strpos( $css, 'grid-template-columns: minmax(0, 1fr) !important;' ),
    'visible_mode_grid' => false !== strpos( $css, 'grid-template-columns: repeat(4, minmax(0, 1fr)) !important;' ),
    'light_form_surface' => false !== strpos( $css, 'background: #fff !important;' ) && false !== strpos( $css, 'color-scheme: light !important;' ),
    'visitor_safe_offline_copy' => false !== strpos( $js, "offline: 'Verified fallback available'" ),
    'current_route_copy' => false !== strpos( $js, 'active v7.0.5 plugin' ),
    'release_documentation' => false !== strpos( $docs, 'Repair and Resume Commit' ) && false !== strpos( $docs, 'one readable vertical workflow' ),
    'release_manifest' => is_array( $manifest ) && '7.0.5' === ( $manifest['version'] ?? '' ) && true === ( $manifest['transaction_recovery']['durable_wordpress_replay'] ?? false ),
);
$failed = array_keys( array_filter( $checks, static function ( $passed ) { return ! $passed; } ) );
$result = array(
    'version' => '7.0.5',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
);
echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
