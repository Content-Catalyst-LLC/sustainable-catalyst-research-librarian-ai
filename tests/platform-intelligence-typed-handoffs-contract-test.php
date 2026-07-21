<?php
/** Static release contract checks for Research Librarian AI v7.0.3 compatibility regression. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$bridge = file_get_contents( $root . '/includes/class-sc-rl-v660-platform-handoffs.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$config = file_get_contents( $root . '/backend/app/config.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$handoffs = file_get_contents( $root . '/backend/app/platform_handoffs.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$render = file_get_contents( $root . '/render.yaml' );
$docs = file_get_contents( $root . '/docs/V660_PLATFORM_INTELLIGENCE_TYPED_HANDOFFS.md' );
$roadmap = file_get_contents( $root . '/docs/ROADMAP.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_platform_handoffs_manifest_v6.6.0.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.0.3' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '7.0.3';" ),
    'bridge_version' => false !== strpos( $bridge, "const VERSION = '7.0.3';" ),
    'durable_module_version' => false !== strpos( $module, "const VERSION = '7.0.3';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.0.3"' ),
    'sqlite_schema_seven' => false !== strpos( $store, 'SCHEMA_VERSION = 10' ),
    'index_schema_seven' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/10.0' ),
    'handoff_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS platform_handoffs' ),
    'artifact_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS platform_artifact_returns' ),
    'handoff_storage' => false !== strpos( $store, 'def save_platform_handoff' ) && false !== strpos( $store, 'def platform_handoffs' ),
    'artifact_storage' => false !== strpos( $store, 'def save_artifact_return' ) && false !== strpos( $store, 'def artifact_returns' ),
    'handoff_schema' => false !== strpos( $handoffs, 'sc-research-handoff/2.0' ),
    'route_schema' => false !== strpos( $handoffs, 'sc-research-route/2.0' ),
    'artifact_schema' => false !== strpos( $handoffs, 'sc-research-artifact-return/1.0' ),
    'workbench_contract' => false !== strpos( $handoffs, 'sc-workbench-task/1.0' ),
    'decision_contract' => false !== strpos( $handoffs, 'sc-decision-packet-seed/1.0' ),
    'site_intelligence_contract' => false !== strpos( $handoffs, 'sc-site-intelligence-query/1.0' ),
    'lab_contract' => false !== strpos( $handoffs, 'sc-lab-workflow/1.0' ),
    'feature_suggestion_contract' => false !== strpos( $handoffs, 'sc-feature-suggestion/1.0' ),
    'capability_catalog' => false !== strpos( $handoffs, 'def capability_catalog' ) && false !== strpos( $handoffs, 'def available_capabilities' ),
    'destination_inference' => false !== strpos( $handoffs, 'def infer_destination' ) && false !== strpos( $handoffs, 'def suggested_destinations' ),
    'source_context' => false !== strpos( $handoffs, 'citation_label' ) && false !== strpos( $handoffs, 'retrieval_reasons' ),
    'human_confirmation' => false !== strpos( $handoffs, 'human_confirmation_required' ),
    'provenance_chain' => false !== strpos( $handoffs, 'research_question' ) && false !== strpos( $handoffs, 'typed_handoff' ),
    'payload_fingerprint' => false !== strpos( $handoffs, 'payload_fingerprint' ) && false !== strpos( $handoffs, 'hashlib.sha256' ),
    'tamper_validation' => false !== strpos( $handoffs, 'Payload fingerprint does not match' ),
    'artifact_validation' => false !== strpos( $handoffs, 'def validate_artifact_return' ),
    'prepare_model' => false !== strpos( $models, 'class PlatformHandoffPrepareRequest' ),
    'validate_model' => false !== strpos( $models, 'class PlatformHandoffValidateRequest' ),
    'artifact_model' => false !== strpos( $models, 'class ArtifactReturnRequest' ),
    'ask_capabilities' => false !== strpos( $models, 'capabilities: list[dict[str, Any]]' ),
    'ask_typed_handoffs' => false !== strpos( $models, 'typed_handoffs: list[dict[str, Any]]' ),
    'ask_provenance' => false !== strpos( $models, 'provenance: dict[str, Any]' ),
    'workspace_schema' => false !== strpos( $backend, 'sc-research-librarian-public-workspace/2.0' ),
    'backend_capabilities_endpoint' => false !== strpos( $backend, '@app.get("/v1/platform/capabilities"' ),
    'backend_prepare_endpoint' => false !== strpos( $backend, '@app.post("/v1/handoffs/prepare"' ),
    'backend_validate_endpoint' => false !== strpos( $backend, '@app.post("/v1/handoffs/validate"' ),
    'backend_log_endpoint' => false !== strpos( $backend, '@app.get("/v1/handoffs/logs"' ),
    'backend_artifact_return_endpoint' => false !== strpos( $backend, '@app.post("/v1/handoffs/artifacts/return"' ),
    'backend_artifact_list_endpoint' => false !== strpos( $backend, '@app.get("/v1/handoffs/artifacts"' ),
    'integration_key_protection' => substr_count( $backend, 'dependencies=[Depends(require_key)]' ) >= 6,
    'ask_previews_handoffs' => false !== strpos( $backend, 'prepare_preview_handoffs' ) && false !== strpos( $backend, 'typed_handoffs=typed_handoffs' ),
    'capability_aware_actions' => false !== strpos( $backend, 'available_capabilities()' ) && false !== strpos( $backend, 'if "workbench" in capabilities' ),
    'workbench_config' => false !== strpos( $config, 'SC_RL_WORKBENCH_ENABLED' ) && false !== strpos( $config, 'SC_RL_WORKBENCH_URL' ),
    'decision_config' => false !== strpos( $config, 'SC_RL_DECISION_STUDIO_ENABLED' ),
    'site_config' => false !== strpos( $config, 'SC_RL_SITE_INTELLIGENCE_ENABLED' ),
    'lab_config' => false !== strpos( $config, 'SC_RL_LAB_ENABLED' ),
    'feature_config' => false !== strpos( $config, 'SC_RL_FEATURE_SUGGESTIONS_ENABLED' ),
    'wordpress_capability_route' => false !== strpos( $bridge, "'/platform/capabilities'" ),
    'wordpress_prepare_route' => false !== strpos( $bridge, "'/platform/handoff/prepare'" ),
    'wordpress_validate_route' => false !== strpos( $bridge, "'/platform/handoff/validate'" ),
    'wordpress_artifact_route' => false !== strpos( $bridge, "'/platform/artifact/return'" ),
    'wordpress_export_route' => false !== strpos( $bridge, "'/platform/handoffs/export'" ),
    'wordpress_nonce' => false !== strpos( $bridge, 'wp_verify_nonce' ) && false !== strpos( $bridge, 'x_wp_nonce' ),
    'wordpress_backend_proxy' => false !== strpos( $bridge, "'X-SC-RL-Key'" ) && false !== strpos( $bridge, 'wp_remote_request' ),
    'wordpress_local_fallback' => false !== strpos( $bridge, 'prepared-local-fallback' ),
    'wordpress_fingerprint_validation' => false !== strpos( $bridge, 'hash_equals' ) && false !== strpos( $bridge, 'Payload fingerprint does not match the handoff contents.' ),
    'wordpress_capability_merge' => false !== strpos( $bridge, 'public static function capabilities' ),
    'wordpress_admin' => false !== strpos( $bridge, 'Research Librarian Handoffs' ) && false !== strpos( $bridge, 'register_admin_menu' ),
    'wordpress_shortcode' => false !== strpos( $bridge, 'sc_research_librarian_platform_handoffs' ),
    'main_bridge_loaded' => false !== strpos( $main, 'class-sc-rl-v660-platform-handoffs.php' ) && false !== strpos( $main, 'SC_RL6_V660_Platform_Handoffs::init' ),
    'main_data_endpoints' => false !== strpos( $main, 'data-platform-capabilities-endpoint' ) && false !== strpos( $main, 'data-platform-handoff-endpoint' ),
    'main_artifact_endpoint' => false !== strpos( $main, 'data-artifact-return-endpoint' ),
    'wordpress_normalizes_handoffs' => false !== strpos( $module, "'typed_handoffs'" ) && false !== strpos( $module, "'capabilities'" ) && false !== strpos( $module, "'provenance'" ),
    'route_note_handoff' => false !== strpos( $module, "'handoff_payload'" ) && false !== strpos( $module, 'sc-research-librarian-route-note/7.0.3' ),
    'js_typed_cards' => false !== strpos( $js, 'Typed research handoffs' ) && false !== strpos( $js, 'typedHandoffs' ),
    'js_available_capabilities' => false !== strpos( $js, 'item && item.available' ),
    'js_prepare_action' => false !== strpos( $js, 'platformHandoffEndpoint' ) && false !== strpos( $js, 'Prepare payload' ),
    'js_download_payload' => false !== strpos( $js, "'-handoff.json'" ),
    'css_handoff_cards' => false !== strpos( $css, '.sc-rl-production-answer__handoff-grid' ),
    'css_handoff_mobile' => false !== strpos( $css, '@media (max-width: 720px)' ),
    'css_handoff_focus' => false !== strpos( $css, '.sc-rl-production-answer__handoff-grid button:focus-visible' ),
    'render_release_version' => false !== strpos( $render, 'SC_RL_RELEASE_VERSION' ) && false !== strpos( $render, '7.0.3' ),
    'render_destinations' => false !== strpos( $render, 'SC_RL_WORKBENCH_ENABLED' ) && false !== strpos( $render, 'SC_RL_LAB_ENABLED' ),
    'release_docs' => false !== strpos( $docs, 'Platform Intelligence and Typed Research Handoffs' ),
    'roadmap_complete' => false !== strpos( $roadmap, 'v6.6.0 — Platform Intelligence and Typed Research Handoffs — Complete' ),
    'manifest_version' => is_array( $manifest ) && '6.6.0' === ( $manifest['version'] ?? '' ),
    'manifest_handoff_schema' => is_array( $manifest ) && 'sc-research-handoff/2.0' === ( $manifest['handoff_schema'] ?? '' ),
    'manifest_destinations' => is_array( $manifest ) && 5 === count( $manifest['destinations'] ?? array() ),
    'manifest_human_control' => is_array( $manifest ) && true === ( $manifest['safety']['human_confirmation_required'] ?? false ),
    'manifest_free_tier' => is_array( $manifest ) && false === ( $manifest['compatibility']['paid_vector_database_required'] ?? true ),
    'black_green_prompt_preserved' => is_array( $manifest ) && true === ( $manifest['compatibility']['black_green_prompt_preserved'] ?? false ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array(
    'version' => '7.0.3',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
