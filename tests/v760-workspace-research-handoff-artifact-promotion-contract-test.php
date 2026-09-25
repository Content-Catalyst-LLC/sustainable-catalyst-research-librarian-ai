<?php
/** Static release contract for Research Librarian AI v7.6.0 Workspace research handoff and artifact promotion. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v700-connected-platform.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$promotion = file_get_contents( $root . '/backend/app/workspace_promotion.py' );
$state = file_get_contents( $root . '/backend/app/research_state.py' );
$collab = file_get_contents( $root . '/backend/app/collaboration.py' );
$platform = file_get_contents( $root . '/backend/app/platform_v7.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$js = file_get_contents( $root . '/assets/sc-research-platform-v760-workspace.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$docs = file_get_contents( $root . '/docs/V760_WORKSPACE_RESEARCH_HANDOFF_ARTIFACT_PROMOTION.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_workspace_promotion_manifest_v7.6.0.json' ), true );
$v750 = json_decode( file_get_contents( $root . '/data/research_librarian_collaborative_room_manifest_v7.5.0.json' ), true );
$migrations = glob( $root . '/backend/migrations/*.sql' );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 10.2.0' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '10.2.0';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "10.2.0"' ),
    'module_version' => false !== strpos( $module, "const VERSION = '8.0.0';" ),
    'api_15' => false !== strpos( $platform, 'sc-connected-research-api/2.0' ),
    'workspace_25' => false !== strpos( $module, 'sc-research-librarian-public-workspace/3.0' ),
    'sqlite_schema_16' => false !== strpos( $store, 'SCHEMA_VERSION = 19' ),
    'knowledge_index_13' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/13.0' ),
    'no_new_postgres_migration' => is_file( $root . '/backend/migrations/004_async_document_processing_runtime.sql' ),

    'promotion_schema' => false !== strpos( $promotion, 'sc-workspace-artifact-promotion/1.0' ),
    'handoff_schema' => false !== strpos( $promotion, 'sc-workspace-research-handoff/1.0' ),
    'summary_schema' => false !== strpos( $promotion, 'sc-workspace-promotion-summary/1.0' ),
    'receipt_schema' => false !== strpos( $promotion, 'sc-workspace-promotion-receipt/1.0' ),
    'import_contract' => false !== strpos( $promotion, 'sc-workspace-research-import/1.0' ),
    'notebook_contract' => false !== strpos( $promotion, 'sc-workspace-notebook-seed/1.0' ),
    'evidence_set_contract' => false !== strpos( $promotion, 'sc-workspace-evidence-set/1.0' ),
    'analysis_contract' => false !== strpos( $promotion, 'sc-workspace-analysis-seed/1.0' ),
    'document_contract' => false !== strpos( $promotion, 'sc-workspace-document-seed/1.0' ),
    'citation_pack_contract' => false !== strpos( $promotion, 'sc-workspace-citation-pack/1.0' ),
    'packet_builder' => false !== strpos( $promotion, 'def build_workspace_packet(' ),
    'promotion_normalizer' => false !== strpos( $promotion, 'def normalize_promotion(' ),
    'receipt_applier' => false !== strpos( $promotion, 'def apply_promotion_receipt(' ),
    'catalog_builder' => false !== strpos( $promotion, 'def artifact_catalog(' ),
    'sha256_fingerprint' => false !== strpos( $promotion, 'hashlib.sha256' ),
    'source_scope_preserved' => false !== strpos( $promotion, '"source_scope_preserved": True' ),
    'owner_attribution_preserved' => false !== strpos( $promotion, '"owner_attribution_preserved": True' ),
    'participant_attribution_preserved' => false !== strpos( $promotion, '"participant_attribution_preserved": True' ),
    'individual_room_state_distinct' => false !== strpos( $promotion, '"personal_and_room_state_remain_distinct": True' ),
    'promotion_not_publication' => false !== strpos( $promotion, '"promotion_is_not_publication": True' ),
    'promotion_not_editorial' => false !== strpos( $promotion, '"promotion_is_not_editorial_approval": True' ),
    'promotion_not_truth' => false !== strpos( $promotion, '"promotion_is_not_truth_judgment": True' ),
    'explicit_import' => false !== strpos( $promotion, '"workspace_import_requires_explicit_user_action": True' ),
    'scope_reclassification_block' => false !== strpos( $promotion, '"workspace_may_not_silently_reclassify_source_scope": True' ),
    'rejected_excluded_default' => false !== strpos( $promotion, '"rejected_sources_excluded_by_default": True' ),
    'receipt_fingerprint_check' => false !== strpos( $promotion, 'Workspace receipt packet fingerprint does not match the prepared promotion.' ),
    'receipt_transfer_only' => false !== strpos( $promotion, '"receipt_confirms_transfer_only": True' ),
    'receipt_no_publication' => false !== strpos( $promotion, '"does_not_confirm_publication": True' ),

    'prepare_model' => false !== strpos( $models, 'class WorkspacePromotionPrepareRequest' ),
    'receipt_model' => false !== strpos( $models, 'class WorkspacePromotionReceiptRequest' ),
    'include_rejected_model' => false !== strpos( $models, 'include_rejected: bool = False' ),
    'receipt_actor_model' => false !== strpos( $models, 'actor_ref: str = Field(default="", max_length=220)' ),

    'promotion_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_workspace_promotions' ),
    'promotion_owner_index' => false !== strpos( $store, 'idx_workspace_promotions_owner' ),
    'promotion_project_index' => false !== strpos( $store, 'idx_workspace_promotions_project' ),
    'save_promotion_method' => false !== strpos( $store, 'def save_workspace_promotion(' ),
    'get_promotion_method' => false !== strpos( $store, 'def workspace_promotion(' ),
    'list_promotions_method' => false !== strpos( $store, 'def workspace_promotions(' ),
    'backup_promotions' => false !== strpos( $store, '"workspace_promotions":promotions' ),
    'platform_summary_promotions' => false !== strpos( $store, '"workspace_promotions":"research_workspace_promotions"' ),

    'promotion_scope_helper' => false !== strpos( $backend, 'def _workspace_promotion_scope(' ),
    'catalog_endpoint' => false !== strpos( $backend, '@app.get("/v1/workspace/promotions/catalog"' ),
    'list_endpoint' => false !== strpos( $backend, '@app.get("/v1/workspace/promotions"' ),
    'get_endpoint' => false !== strpos( $backend, '@app.get("/v1/workspace/promotions/{promotion_id}"' ),
    'prepare_endpoint' => false !== strpos( $backend, '@app.post("/v1/workspace/promotions/prepare"' ),
    'receipt_endpoint' => false !== strpos( $backend, '@app.post("/v1/workspace/promotions/{promotion_id}/receipt"' ),
    'api_resource' => false !== strpos( $backend, '"workspace-promotions"' ),
    'api_explicit_import' => false !== strpos( $backend, '"explicit_import_required": True' ),
    'backup_import_promotions' => false !== strpos( $backend, 'for promotion_payload in body.get("workspace_promotions") or []:' ),
    'project_activity_prepared' => false !== strpos( $state, '"workspace-promotion-prepared"' ),
    'project_activity_imported' => false !== strpos( $state, '"workspace-promotion-imported"' ),
    'room_activity_prepared' => false !== strpos( $collab, '"workspace-promotion-prepared"' ),
    'room_activity_imported' => false !== strpos( $collab, '"workspace-promotion-imported"' ),

    'wp_promotion_schema' => false !== strpos( $module, "const WORKSPACE_PROMOTION_SCHEMA = 'sc-workspace-artifact-promotion/1.0';" ),
    'wp_handoff_schema' => false !== strpos( $module, "const WORKSPACE_HANDOFF_SCHEMA = 'sc-workspace-research-handoff/1.0';" ),
    'wp_capability_promotion' => false !== strpos( $module, "'workspace_artifact_promotion' => '1'" ),
    'wp_capability_receipts' => false !== strpos( $module, "'workspace_promotion_receipts' => '1'" ),
    'wp_capability_explicit_import' => false !== strpos( $module, "'workspace_explicit_import' => '1'" ),
    'wp_route_promotions' => false !== strpos( $module, "'/platform/v7/workspace/promotions'" ),
    'wp_route_promotion_id' => false !== strpos( $module, "'/platform/v7/workspace/promotions/(?P<promotion_id>" ),
    'wp_prepare_method' => false !== strpos( $module, 'rest_workspace_promotion_prepare' ),
    'wp_receipt_method' => false !== strpos( $module, 'rest_workspace_promotion_receipt' ),
    'wp_owner_server_side' => false !== strpos( $module, "'owner_ref' => self::owner_ref()" ),
    'wp_actor_server_side' => false !== strpos( $module, "'actor_ref' => self::owner_ref()" ),
    'wp_context_authorized' => false !== strpos( $module, 'self::authorized_context( $context_id )' ),
    'wp_project_authorized' => false !== strpos( $module, 'self::authorized_project( $project_id, false )' ),
    'wp_room_authorized' => false !== strpos( $module, 'self::authorized_room( $room_id, false, false )' ),
    'wp_selected_objects_authorized' => false !== strpos( $module, 'self::authorized_object_ids( $p[\'selected_object_ids\'] ?? array() )' ),
    'wp_artifact_allowlist' => false !== strpos( $module, "array( 'notebook', 'evidence-set', 'analysis', 'document', 'citation-pack' )" ),
    'wp_workspace_asset' => false !== strpos( $module, 'sc-research-platform-v760-workspace.js' ),
    'wp_workspace_url' => false !== strpos( $module, "home_url( '/workspace/' )" ),
    'wp_promotion_button' => false !== strpos( $module, 'data-sc-rl-v760-workspace-run>Promote to Workspace' ),
    'wp_promotion_panel' => false !== strpos( $module, 'data-sc-rl-v760-workspace-panel' ),
    'wp_promotion_form' => false !== strpos( $module, 'data-sc-rl-v760-workspace-form' ),

    'js_prepare' => false !== strpos( $js, 'Preparing governed Workspace handoff' ),
    'js_no_auto_import' => false !== strpos( $js, 'Nothing has been published or imported automatically.' ),
    'js_download' => false !== strpos( $js, 'Download handoff JSON' ),
    'js_open_workspace' => false !== strpos( $js, 'Open Workspace' ),
    'js_history' => false !== strpos( $js, 'Recent promotion outbox' ),
    'js_boundary_copy' => false !== strpos( $js, 'not publication, editorial approval, or a truth judgment' ),
    'css_promotion_panel' => false !== strpos( $css, '.sc-rl-v760-workspace-panel' ),
    'css_promotion_card' => false !== strpos( $css, '.sc-rl-v760-promotion-card' ),

    'manifest_version' => is_array( $manifest ) && '7.6.0' === ( $manifest['version'] ?? '' ),
    'manifest_api' => is_array( $manifest ) && 'sc-connected-research-api/1.5' === ( $manifest['api_schema'] ?? '' ),
    'manifest_workspace' => is_array( $manifest ) && 'sc-research-librarian-public-workspace/2.5' === ( $manifest['workspace_schema'] ?? '' ),
    'manifest_sqlite_16' => is_array( $manifest ) && 16 === ( $manifest['storage']['ancillary_sqlite_schema_version'] ?? 0 ),
    'manifest_no_postgres_migration' => is_array( $manifest ) && false === ( $manifest['storage']['new_postgres_migration_required'] ?? true ),
    'manifest_explicit_import' => is_array( $manifest ) && true === ( $manifest['governance']['explicit_workspace_import_required'] ?? false ),
    'manifest_scope_preserved' => is_array( $manifest ) && true === ( $manifest['governance']['source_scope_preserved'] ?? false ),
    'manifest_actor_boundary' => is_array( $manifest ) && true === ( $manifest['privacy_boundaries']['browser_cannot_choose_owner_or_actor_identity'] ?? false ),
    'manifest_receipt_fingerprint' => is_array( $manifest ) && true === ( $manifest['receipts']['packet_fingerprint_must_match'] ?? false ),
    'manifest_backup' => is_array( $manifest ) && true === ( $manifest['backup']['workspace_promotions_included'] ?? false ),
    'v750_manifest_preserved' => is_array( $v750 ) && '7.5.0' === ( $v750['version'] ?? '' ) && 15 === ( $v750['storage']['ancillary_sqlite_schema_version'] ?? 0 ),
    'docs_explicit_import' => false !== strpos( $docs, 'does **not** silently create, publish, or import a Workspace artifact' ),
    'docs_no_neon_migration' => false !== strpos( $docs, 'No Neon/Postgres knowledge-index migration is required for v7.6.0' ),
    'docs_state_boundary' => false !== strpos( $docs, 'Personal v7.4 research state and shared v7.5 room state remain distinct' ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.6.0', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
