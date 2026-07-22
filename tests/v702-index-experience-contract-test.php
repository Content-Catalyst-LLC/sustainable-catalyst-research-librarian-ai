<?php
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$provider = file_get_contents( $root . '/includes/class-sc-rl-v610-live-ai-admin.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_v702_index_experience_manifest.json' ), true );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.1.0' ),
    'version_constant' => false !== strpos( $module, "const VERSION = '7.1.0';" ),
    'one_click_pipeline' => false !== strpos( $module, 'build_index_pipeline' ) && false !== strpos( $module, 'Build Knowledge Index' ),
    'post_commit_verification' => false !== strpos( $module, "'/v1/knowledge/summary'" ) && false !== strpos( $module, 'index_verification_failed' ),
    'snapshot_recovery' => false !== strpos( $module, 'create_wordpress_snapshot_from_build_file' ) && false !== strpos( $module, 'verifying-index' ),
    'expanded_source_discovery' => false !== strpos( $module, 'publicly_queryable' ) && false !== strpos( $module, 'rest-and-rewrite' ),
    'source_filter' => false !== strpos( $module, 'sc_rl_indexable_post_types' ),
    'four_stage_interface' => false !== strpos( $module, '1 · Python connection' ) && false !== strpos( $module, '4 · Semantic search' ),
    'source_coverage_interface' => false !== strpos( $module, 'Source coverage' ),
    'progressive_disclosure' => false !== strpos( $module, 'Connection and advanced settings' ) && false !== strpos( $module, 'Technical diagnostics and transaction history' ),
    'fallback_page_clarity' => false !== strpos( $provider, 'Optional WordPress Fallback Provider' ) && false !== strpos( $provider, 'does not build or verify the Python index' ),
    'public_friendly_status' => false !== strpos( $js, 'Research service online' ) && false !== strpos( $js, 'Verified routing available' ),
    'backend_state_separation' => false !== strpos( $backend, 'generation_state' ) && false !== strpos( $backend, 'index_state' ) && false !== strpos( $backend, 'embedding_state' ),
    'manifest' => is_array( $manifest ) && '7.0.2' === ( $manifest['version'] ?? '' ) && false === ( $manifest['paid_infrastructure_required'] ?? true ),
);
$failed = array_keys( array_filter( $checks, function( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.1.0', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
