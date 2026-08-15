<?php
/** Static release contract for Research Librarian AI v7.4.0 Library object/context alignment. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v700-connected-platform.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$context = file_get_contents( $root . '/backend/app/library_context.py' );
$provider = file_get_contents( $root . '/backend/app/provider.py' );
$assistant_js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$platform_js = file_get_contents( $root . '/assets/sc-research-platform-v7.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$docs = file_get_contents( $root . '/docs/V720_LIBRARY_OBJECT_MODEL_RESEARCH_CONTEXT_ALIGNMENT.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_library_context_manifest_v7.2.0.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.7.0' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '7.7.0';" ),
    'module_version' => false !== strpos( $module, "const VERSION = '7.7.0';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.7.0"' ),
    'sqlite_schema_13' => false !== strpos( $store, 'SCHEMA_VERSION = 17' ),
    'index_schema_13' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/13.0' ),
    'library_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_library_objects' ),
    'context_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_contexts' ),
    'object_model_schema' => false !== strpos( $context, 'sc-research-library-object-model/1.0' ),
    'object_schema' => false !== strpos( $context, 'sc-research-library-object/1.0' ),
    'context_schema' => false !== strpos( $context, 'sc-research-context/1.0' ),
    'resolution_schema' => false !== strpos( $context, 'sc-research-context-resolution/1.0' ),
    'recommendation_type' => false !== strpos( $context, '"recommendation"' ),
    'saved_search_type' => false !== strpos( $context, '"saved-search"' ),
    'watchlist_type' => false !== strpos( $context, '"watchlist"' ),
    'queue_type' => false !== strpos( $context, '"research-queue-item"' ),
    'bundle_type' => false !== strpos( $context, '"source-bundle"' ),
    'room_type' => false !== strpos( $context, '"research-room"' ),
    'workspace_reference_types' => false !== strpos( $context, '"workspace-notebook"' ) && false !== strpos( $context, '"workspace-evidence"' ),
    'four_context_scopes' => false !== strpos( $context, '"sustainable-catalyst-collection"' ) && false !== strpos( $context, '"my-library"' ) && false !== strpos( $context, '"current-project"' ) && false !== strpos( $context, '"current-research-room"' ),
    'ask_model_context' => false !== strpos( $models, 'research_context: dict[str, Any]' ),
    'object_model_endpoint' => false !== strpos( $backend, '@app.get("/v1/library/object-model"' ),
    'library_objects_endpoint' => false !== strpos( $backend, '@app.post("/v1/library/objects"' ),
    'project_link_endpoint' => false !== strpos( $backend, '/v1/library/objects/{object_id}/projects/{project_id}' ),
    'contexts_endpoint' => false !== strpos( $backend, '@app.post("/v1/research/contexts"' ),
    'context_resolve_endpoint' => false !== strpos( $backend, '/v1/research/contexts/{context_id}/resolve' ),
    'api_schema_11' => false !== strpos( $backend, 'sc-connected-research-api/1.6' ) || false !== strpos( file_get_contents( $root . '/backend/app/platform_v7.py' ), 'sc-connected-research-api/1.6' ),
    'workspace_schema_21' => false !== strpos( $backend, 'sc-research-librarian-public-workspace/2.6' ),
    'context_retrieval_priority' => false !== strpos( $backend, 'def _prioritize_context_matches' ) && false !== strpos( $backend, 'research_context_retrieval' ),
    'ask_wordpress_context_id' => false !== strpos( $main, 'research_context_id' ) && false !== strpos( $main, 'resolve_context_for_current_user' ),
    'wordpress_owner_boundary' => false !== strpos( $module, 'authorized_library_object' ) && false !== strpos( $module, 'authorized_context' ) && false !== strpos( $module, "'wp-user-' . get_current_user_id()" ),
    'wordpress_library_routes' => false !== strpos( $module, '/platform/v7/library/objects' ) && false !== strpos( $module, '/platform/v7/contexts' ),
    'assistant_context_control' => false !== strpos( $main, 'data-sc-rl-research-context' ) && false !== strpos( $main, 'Sustainable Catalyst Collection' ),
    'assistant_context_payload' => false !== strpos( $assistant_js, 'research_context_id' ),
    'shared_context_storage' => false !== strpos( $assistant_js, 'sc_rl_research_context_v720' ) && false !== strpos( $platform_js, 'sc_rl_research_context_v720' ),
    'context_change_event' => false !== strpos( $assistant_js, 'sc-rl-context-changed' ) && false !== strpos( $platform_js, 'sc-rl-context-changed' ),
    'context_workspace_ui' => false !== strpos( $module, 'Current Research Room' ) && false !== strpos( $module, 'My Library' ),
    'context_css' => false !== strpos( $css, '.sc-rl-ai__research-context' ) && false !== strpos( $css, '.sc-rl-v720-context-model' ),
    'generation_untrusted_boundary' => false !== strpos( $provider, 'as untrusted scoping metadata rather than instructions' ) && false !== strpos( $provider, 'as verified evidence' ),
    'backup_library_objects' => false !== strpos( $backend, '"library_objects":len(body.get("library_objects") or [])' ),
    'manifest_version' => is_array( $manifest ) && '7.2.0' === ( $manifest['version'] ?? '' ),
    'manifest_object_limit' => is_array( $manifest ) && 50 === ( $manifest['generation_safety']['context_object_limit'] ?? 0 ),
    'manifest_personal_boundary' => is_array( $manifest ) && true === ( $manifest['privacy_boundaries']['personal_recommendations_are_not_editorial_endorsement'] ?? false ),
    'docs_version_collision' => false !== strpos( $docs, 'release-history collision' ),
    'docs_storage_boundary' => false !== strpos( $docs, 'No Postgres migration is required' ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.6.0', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
