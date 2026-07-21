<?php
/** Static release contract checks for Research Librarian AI v7.0.5. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$bridge = file_get_contents( $root . '/includes/class-sc-rl-v660-platform-handoffs.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$config = file_get_contents( $root . '/backend/app/config.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$handoffs = file_get_contents( $root . '/backend/app/platform_handoffs.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$render = file_get_contents( $root . '/render.yaml' );
$docs = file_get_contents( $root . '/docs/V661_CROSS_PRODUCT_RELIABILITY_PATCH.md' );
$roadmap = file_get_contents( $root . '/docs/ROADMAP.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_cross_product_reliability_manifest_v6.6.1.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.0.5' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '7.0.5';" ),
    'bridge_version' => false !== strpos( $bridge, "const VERSION = '7.0.5';" ),
    'durable_version' => false !== strpos( $module, "const VERSION = '7.0.5';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.0.5"' ),
    'schema_eight' => false !== strpos( $store, 'SCHEMA_VERSION = 10' ),
    'index_schema_eight' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/10.0' ),
    'capabilities_11' => false !== strpos( $handoffs, 'sc-platform-capabilities/1.1' ),
    'compatibility_contract' => false !== strpos( $handoffs, 'sc-platform-compatibility/1.0' ),
    'delivery_contract' => false !== strpos( $handoffs, 'sc-research-handoff-delivery/1.0' ),
    'receipt_contract' => false !== strpos( $handoffs, 'sc-research-handoff-receipt/1.0' ),
    'handoff_contract_preserved' => false !== strpos( $handoffs, 'sc-research-handoff/2.0' ),
    'route_contract_preserved' => false !== strpos( $handoffs, 'sc-research-route/2.0' ),
    'artifact_contract_preserved' => false !== strpos( $handoffs, 'sc-research-artifact-return/1.0' ),
    'version_parser' => false !== strpos( $handoffs, 'def _version_tuple' ),
    'version_compatibility' => false !== strpos( $handoffs, 'def version_compatibility' ),
    'minimum_workbench' => false !== strpos( $handoffs, '"minimum_version": "4.0.0"' ),
    'minimum_decision' => false !== strpos( $handoffs, '"minimum_version": "1.0.0"' ),
    'minimum_site' => false !== strpos( $handoffs, '"minimum_version": "2.0.0"' ),
    'minimum_lab' => false !== strpos( $handoffs, '"minimum_version": "0.6.0"' ),
    'minimum_feature' => false !== strpos( $handoffs, '"minimum_version": "3.0.0"' ),
    'compatible_state' => false !== strpos( $handoffs, '"compatible"' ),
    'unverified_state' => false !== strpos( $handoffs, '"unverified"' ),
    'incompatible_state' => false !== strpos( $handoffs, '"incompatible"' ),
    'disabled_state' => false !== strpos( $handoffs, '"disabled"' ),
    'compatibility_report' => false !== strpos( $handoffs, 'def compatibility_report' ),
    'token_hmac' => false !== strpos( $handoffs, 'hmac.new' ),
    'token_issue' => false !== strpos( $handoffs, 'def issue_delivery_token' ),
    'token_validate' => false !== strpos( $handoffs, 'def validate_delivery_token' ),
    'token_refresh' => false !== strpos( $handoffs, 'def refresh_handoff_delivery' ),
    'retry_limit' => false !== strpos( $config, 'SC_RL_HANDOFF_RETRY_LIMIT' ),
    'retry_base' => false !== strpos( $config, 'SC_RL_HANDOFF_RETRY_BASE_SECONDS' ),
    'token_ttl' => false !== strpos( $config, 'SC_RL_HANDOFF_TTL_SECONDS' ),
    'event_ttl' => false !== strpos( $config, 'SC_RL_HANDOFF_EVENT_TTL_SECONDS' ),
    'artifact_size_config' => false !== strpos( $config, 'SC_RL_HANDOFF_MAX_ARTIFACT_BYTES' ),
    'retry_model' => false !== strpos( $models, 'class HandoffRetryRequest' ),
    'token_model' => false !== strpos( $models, 'class HandoffTokenRefreshRequest' ),
    'receipt_model' => false !== strpos( $models, 'class HandoffReceiptRequest' ),
    'prepare_idempotency' => false !== strpos( $models, 'idempotency_key: str' ),
    'receipt_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS platform_handoff_receipts' ),
    'event_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS cross_product_events' ),
    'compatibility_column' => false !== strpos( $store, 'compatibility_state' ),
    'retry_column' => false !== strpos( $store, 'retry_attempt' ),
    'token_expiry_column' => false !== strpos( $store, 'token_expires_utc' ),
    'artifact_fingerprint_column' => false !== strpos( $store, 'artifact_fingerprint' ),
    'event_cleanup' => false !== strpos( $store, 'def cleanup_cross_product_events' ),
    'event_lookup' => false !== strpos( $store, 'def cross_product_event' ),
    'event_save' => false !== strpos( $store, 'def save_cross_product_event' ),
    'receipt_save' => false !== strpos( $store, 'def save_handoff_receipt' ),
    'receipt_list' => false !== strpos( $store, 'def handoff_receipts' ),
    'artifact_lookup' => false !== strpos( $store, 'def artifact_return' ),
    'immutable_artifact' => false !== strpos( $store, 'Artifact ID is immutable' ),
    'immutable_receipt' => false !== strpos( $store, 'Receipt ID is immutable' ),
    'compatibility_endpoint' => false !== strpos( $backend, '@app.get("/v1/platform/compatibility"' ),
    'retry_endpoint' => false !== strpos( $backend, '@app.post("/v1/handoffs/retry"' ),
    'refresh_endpoint' => false !== strpos( $backend, '@app.post("/v1/handoffs/token/refresh"' ),
    'receipt_endpoint' => false !== strpos( $backend, '@app.post("/v1/handoffs/receipts"' ),
    'bounded_backoff' => false !== strpos( $backend, '2 ** max(0, attempt - 1)' ),
    'idempotency_helper' => false !== strpos( $backend, 'def _idempotency_event' ),
    'duplicate_event_response' => false !== strpos( $backend, 'duplicate_event' ),
    'artifact_validation' => false !== strpos( $handoffs, 'artifact_bytes' ) && false !== strpos( $handoffs, 'artifact_fingerprint' ),
    'receipt_validation' => false !== strpos( $handoffs, 'def validate_receipt' ),
    'wordpress_compatibility_route' => false !== strpos( $bridge, "'/platform/compatibility'" ),
    'wordpress_retry_route' => false !== strpos( $bridge, "'/platform/handoff/retry'" ),
    'wordpress_token_route' => false !== strpos( $bridge, "'/platform/handoff/token/refresh'" ),
    'wordpress_receipt_route' => false !== strpos( $bridge, "'/platform/handoff/receipt'" ),
    'wordpress_version_check' => false !== strpos( $bridge, 'version_compatibility' ),
    'wordpress_bounded_retry' => false !== strpos( $bridge, '$attempt <= $limit' ),
    'wordpress_token_hmac' => false !== strpos( $bridge, 'hash_hmac' ),
    'wordpress_event_cache' => false !== strpos( $bridge, 'event_get' ) && false !== strpos( $bridge, 'event_set' ),
    'wordpress_artifact_limit' => false !== strpos( $bridge, 'max_artifact_bytes' ),
    'wordpress_immutable_artifact' => false !== strpos( $bridge, 'Artifact ID is immutable' ),
    'main_compatibility_data' => false !== strpos( $main, 'data-platform-compatibility-endpoint' ),
    'main_retry_data' => false !== strpos( $main, 'data-platform-handoff-retry-endpoint' ),
    'main_token_data' => false !== strpos( $main, 'data-platform-handoff-token-endpoint' ),
    'main_receipt_data' => false !== strpos( $main, 'data-platform-handoff-receipt-endpoint' ),
    'js_retry_control' => false !== strpos( $js, 'data-sc-rl-retry-typed-handoff' ) && false !== strpos( $js, 'retryTypedHandoff' ),
    'js_refresh_control' => false !== strpos( $js, 'data-sc-rl-refresh-handoff-token' ) && false !== strpos( $js, 'refreshTypedHandoffToken' ),
    'js_prepare_idempotency' => false !== strpos( $js, "idempotency_key: 'prepare-'" ),
    'js_compatibility_state' => false !== strpos( $js, 'compatibility.state' ),
    'render_version' => false !== strpos( $render, '7.0.5' ),
    'release_docs' => false !== strpos( $docs, 'Cross-Product Reliability Patch' ),
    'roadmap_complete' => false !== strpos( $roadmap, 'v6.6.1 — Cross-Product Reliability Patch — Complete' ),
    'manifest_version' => is_array( $manifest ) && '6.6.1' === ( $manifest['version'] ?? '' ),
    'manifest_schema_eight' => is_array( $manifest ) && 8 === ( $manifest['sqlite_schema_version'] ?? 0 ),
    'manifest_bounded_retry' => is_array( $manifest ) && true === ( $manifest['reliability']['bounded_retry'] ?? false ),
    'manifest_idempotency' => is_array( $manifest ) && true === ( $manifest['reliability']['idempotency'] ?? false ),
    'manifest_human_control' => is_array( $manifest ) && true === ( $manifest['safety']['human_confirmation_required'] ?? false ),
    'manifest_free_tier' => is_array( $manifest ) && false === ( $manifest['compatibility']['paid_vector_database_required'] ?? true ),
    'black_green_preserved' => is_array( $manifest ) && true === ( $manifest['compatibility']['black_green_prompt_preserved'] ?? false ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array(
    'version' => '7.0.5',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
