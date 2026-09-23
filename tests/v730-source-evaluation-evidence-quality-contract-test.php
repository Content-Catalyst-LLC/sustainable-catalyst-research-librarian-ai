<?php
/** Static release contract for v7.3.0 source evaluation and evidence-quality signals. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v700-connected-platform.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$quality = file_get_contents( $root . '/backend/app/evidence_quality.py' );
$context = file_get_contents( $root . '/backend/app/library_context.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$platform = file_get_contents( $root . '/backend/app/platform_v7.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$js = file_get_contents( $root . '/assets/sc-research-platform-v7.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$docs = file_get_contents( $root . '/docs/V730_SOURCE_EVALUATION_EVIDENCE_COMPARISON_RESEARCH_QUALITY_SIGNALS.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_source_evaluation_manifest_v7.3.0.json' ), true );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 8.2.0' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '8.2.0';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "8.2.0"' ),
    'module_version' => false !== strpos( $module, "const VERSION = '8.0.0';" ),
    'api_12' => false !== strpos( $platform, 'sc-connected-research-api/2.0' ),
    'workspace_22' => false !== strpos( $module, 'sc-research-librarian-public-workspace/3.0' ),
    'quality_schema_constant' => false !== strpos( $module, 'sc-research-quality-signals/1.0' ),
    'source_evaluation_schema' => false !== strpos( $quality, 'sc-source-evaluation/1.0' ),
    'comparison_schema' => false !== strpos( $quality, 'sc-evidence-comparison/1.0' ),
    'gap_schema' => false !== strpos( $quality, 'sc-evidence-gap-report/1.0' ),
    'quality_signals_schema' => false !== strpos( $quality, 'sc-research-quality-signals/1.0' ),
    'evaluate_function' => false !== strpos( $quality, 'def evaluate_source(' ),
    'compare_function' => false !== strpos( $quality, 'def compare_sources(' ),
    'gap_function' => false !== strpos( $quality, 'def evidence_gaps(' ),
    'compact_quality_function' => false !== strpos( $quality, 'def compact_source_quality(' ),
    'evidence_levels' => false !== strpos( $quality, 'EVIDENCE_LEVELS' ) && false !== strpos( $quality, '"primary"' ) && false !== strpos( $quality, '"secondary"' ),
    'publisher_signal' => false !== strpos( $quality, '"publisher"' ),
    'institution_signal' => false !== strpos( $quality, '"institution"' ),
    'publication_date_signal' => false !== strpos( $quality, '"publication_date"' ),
    'methodology_signal' => false !== strpos( $quality, '"methodology"' ),
    'citation_signal' => false !== strpos( $quality, '"citation"' ),
    'access_signal' => false !== strpos( $quality, '"access_state"' ),
    'provenance_signal' => false !== strpos( $quality, '"provenance"' ),
    'limitations_signal' => false !== strpos( $quality, '"limitations"' ),
    'no_truth_score' => false !== strpos( $quality, '"truth_score": None' ) && false !== strpos( $quality, '"no_truth_score": True' ),
    'no_automatic_winner' => false !== strpos( $quality, '"no_automatic_winner": True' ),
    'no_auto_rejection' => false !== strpos( $quality, '"no_automatic_source_rejection": True' ),
    'human_judgment' => false !== strpos( $quality, '"human_judgment_required": True' ),
    'no_primary_gap' => false !== strpos( $quality, 'no-primary-evidence' ),
    'provider_gap' => false !== strpos( $quality, 'provider-concentration' ),
    'methodology_gap' => false !== strpos( $quality, 'methodology-visibility' ),
    'undated_gap' => false !== strpos( $quality, 'undated-corpus' ),
    'citation_gap' => false !== strpos( $quality, 'citation-metadata' ),
    'limitations_gap' => false !== strpos( $quality, 'limitations-undocumented' ),
    'contrast_gap' => false !== strpos( $quality, 'contrast-coverage' ),
    'source_request_model' => false !== strpos( $models, 'class SourceEvaluationRequest' ),
    'comparison_request_model' => false !== strpos( $models, 'class EvidenceComparisonRequest' ),
    'gap_request_model' => false !== strpos( $models, 'class EvidenceGapRequest' ),
    'context_quality_endpoint' => false !== strpos( $backend, '/v1/research/contexts/{context_id}/evidence-quality' ),
    'source_evaluate_endpoint' => false !== strpos( $backend, '/v1/research/sources/evaluate' ),
    'comparison_endpoint' => false !== strpos( $backend, '/v1/research/evidence/compare' ),
    'gap_endpoint' => false !== strpos( $backend, '/v1/research/evidence/gaps' ),
    'quality_persistence' => false !== strpos( $backend, 'source-evaluation-set' ) && false !== strpos( $backend, 'evidence-comparison' ) && false !== strpos( $backend, 'evidence-gap-report' ),
    'project_entity_storage' => false !== strpos( $store, 'research_project_entities' ),
    'context_quality_carry' => false !== strpos( $context, '"quality_signals": compact_source_quality(item)' ),
    'context_boundary_note' => false !== strpos( $context, 'not truth scores or independent verification' ),
    'wordpress_quality_route' => false !== strpos( $module, '/evidence-quality' ),
    'wordpress_source_route' => false !== strpos( $module, '/platform/v7/evidence/evaluate' ),
    'wordpress_compare_route' => false !== strpos( $module, '/platform/v7/evidence/compare' ),
    'wordpress_gap_route' => false !== strpos( $module, '/platform/v7/evidence/gaps' ),
    'wordpress_owner_authorization' => false !== strpos( $module, 'authorized_object_ids' ) && false !== strpos( $module, 'authorized_context' ),
    'editorial_scope_admin_only' => false !== strpos( $module, "member_scopes=array('my-library','current-project','current-research-room','external-reference')" ) && false !== strpos( $module, "current_user_can('manage_options')" ) && false !== strpos( $module, "requested_scope" ),
    'wordpress_nonce_boundary' => false !== strpos( $module, 'checked_json' ) && false !== strpos( $module, 'X-WP-Nonce' ),
    'workspace_evaluate_action' => false !== strpos( $module, 'data-sc-rl-v730-quality-run' ),
    'workspace_quality_panel' => false !== strpos( $module, 'data-sc-rl-v730-quality-panel' ),
    'js_quality_renderer' => false !== strpos( $js, 'function renderQuality(body)' ),
    'js_context_quality_call' => false !== strpos( $js, '/evidence-quality' ) || false !== strpos( $js, 'evidence-quality`' ),
    'js_no_score_copy' => false !== strpos( $js, 'not a truth score, credibility score, or independent verification' ),
    'css_quality_panel' => false !== strpos( $css, '.sc-rl-v730-quality-panel' ),
    'manifest_version' => is_array( $manifest ) && '7.3.0' === ( $manifest['version'] ?? '' ),
    'manifest_truth_score_false' => is_array( $manifest ) && false === ( $manifest['governance']['truth_score'] ?? true ),
    'manifest_no_migration' => is_array( $manifest ) && false === ( $manifest['storage']['new_database_migration_required'] ?? true ),
    'manifest_v720_compatibility' => is_array( $manifest ) && true === ( $manifest['compatibility']['v7_2_library_object_model_preserved'] ?? false ),
    'docs_no_truth_score' => false !== strpos( $docs, 'does **not** assign a truth score' ),
    'docs_no_db_migration' => false !== strpos( $docs, 'No Postgres or SQLite schema migration is required' ),
    'sqlite_schema_preserved' => false !== strpos( $store, 'SCHEMA_VERSION = 19' ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.3.0', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
