<?php
/** Static release contract for Research Librarian AI v7.6.0 collaborative Research Rooms. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v700-connected-platform.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$collab = file_get_contents( $root . '/backend/app/collaboration.py' );
$context = file_get_contents( $root . '/backend/app/library_context.py' );
$platform = file_get_contents( $root . '/backend/app/platform_v7.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$postgres = file_get_contents( $root . '/backend/app/postgres_store.py' );
$js = file_get_contents( $root . '/assets/sc-research-platform-v750-rooms.js' );
$base_js = file_get_contents( $root . '/assets/sc-research-platform-v7.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$docs = file_get_contents( $root . '/docs/V750_COLLABORATIVE_RESEARCH_ROOM_INTELLIGENCE.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_collaborative_room_manifest_v7.5.0.json' ), true );
$v740 = json_decode( file_get_contents( $root . '/data/research_librarian_persistent_research_state_manifest_v7.4.0.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 9.1.0' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '9.1.0';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "9.1.0"' ),
    'module_version' => false !== strpos( $module, "const VERSION = '8.0.0';" ),
    'api_14' => false !== strpos( $platform, 'sc-connected-research-api/2.0' ),
    'workspace_24' => false !== strpos( $module, 'sc-research-librarian-public-workspace/3.0' ),
    'sqlite_schema_15' => false !== strpos( $store, 'SCHEMA_VERSION = 19' ),
    'knowledge_index_13' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/13.0' ),

    'room_schema' => false !== strpos( $collab, 'sc-research-room/1.0' ),
    'member_schema' => false !== strpos( $collab, 'sc-research-room-member/1.0' ),
    'evidence_schema' => false !== strpos( $collab, 'sc-research-room-evidence-state/1.0' ),
    'question_schema' => false !== strpos( $collab, 'sc-research-room-question/1.0' ),
    'disagreement_schema' => false !== strpos( $collab, 'sc-research-room-disagreement/1.0' ),
    'activity_schema' => false !== strpos( $collab, 'sc-research-room-activity/1.0' ),
    'synthesis_schema' => false !== strpos( $collab, 'sc-research-room-synthesis/1.0' ),
    'prompt_schema' => false !== strpos( $collab, 'sc-research-room-prompt/1.0' ),
    'role_contract' => false !== strpos( $collab, '"owner", "editor", "researcher", "viewer"' ),
    'individual_shared_separate' => false !== strpos( $collab, '"individual_and_shared_state_separate": True' ),
    'not_editorial' => false !== strpos( $collab, '"room_material_is_not_editorial": True' ),
    'room_not_fact' => false !== strpos( $collab, '"room_synthesis_is_not_fact": True' ),
    'evidence_not_truth_judgment' => false !== strpos( $collab, '"room_inclusion_is_not_truth_judgment": True' ),
    'positions_attributed' => false !== strpos( $collab, '"participant_positions_remain_attributed": True' ),
    'synthesis_builder' => false !== strpos( $collab, 'def build_room_synthesis(' ),
    'prompt_builder' => false !== strpos( $collab, 'def prompt_room_synthesis(' ),
    'prompt_boundary' => false !== strpos( $collab, 'not verified evidence' ),

    'room_model' => false !== strpos( $models, 'class ResearchRoomRequest' ),
    'member_model' => false !== strpos( $models, 'class ResearchRoomMemberRequest' ),
    'evidence_model' => false !== strpos( $models, 'class ResearchRoomEvidenceStateRequest' ),
    'question_model' => false !== strpos( $models, 'class ResearchRoomQuestionRequest' ),
    'disagreement_model' => false !== strpos( $models, 'class ResearchRoomDisagreementRequest' ),
    'activity_model' => false !== strpos( $models, 'class ResearchRoomActivityRequest' ),
    'room_actor_model' => false !== strpos( $models, 'actor_ref: str = Field(default="", max_length=220)' ),

    'room_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_rooms' ),
    'member_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_room_members' ),
    'evidence_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_room_evidence_states' ),
    'question_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_room_questions' ),
    'disagreement_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_room_disagreements' ),
    'activity_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS research_room_activity' ),
    'room_store_methods' => false !== strpos( $store, 'def save_research_room(' ) && false !== strpos( $store, 'def research_rooms(' ),
    'room_object_lookup' => false !== strpos( $store, 'def library_objects_for_room(' ),
    'project_backup_rooms' => false !== strpos( $store, '"research_rooms":room_bundles' ),
    'postgres_ancillary_delegate' => false !== strpos( $postgres, '__getattr__' ) && false !== strpos( $postgres, '_legacy' ),

    'room_list_endpoint' => false !== strpos( $backend, '@app.get("/v1/research/rooms"' ),
    'room_save_endpoint' => false !== strpos( $backend, '@app.post("/v1/research/rooms"' ),
    'member_endpoint' => false !== strpos( $backend, '/v1/research/rooms/{room_id}/members' ),
    'evidence_endpoint' => false !== strpos( $backend, '/v1/research/rooms/{room_id}/evidence' ),
    'question_endpoint' => false !== strpos( $backend, '/v1/research/rooms/{room_id}/questions' ),
    'disagreement_endpoint' => false !== strpos( $backend, '/v1/research/rooms/{room_id}/disagreements' ),
    'activity_endpoint' => false !== strpos( $backend, '/v1/research/rooms/{room_id}/activity' ),
    'synthesis_endpoint' => false !== strpos( $backend, '/v1/research/rooms/{room_id}/synthesis' ),
    'viewer_read_only' => false !== strpos( $backend, 'role') && false !== strpos( $backend, 'viewer' ) && false !== strpos( $backend, 'write=True' ),
    'position_impersonation_blocked' => false !== strpos( $backend, 'Participants may submit only their own attributed disagreement position.' ),
    'position_merge' => false !== strpos( $backend, 'merged_positions' ),
    'leadership_resolution' => false !== strpos( $backend, 'Only a Research Room owner/editor can resolve a disagreement.' ),
    'question_disposition_guard' => false !== strpos( $backend, 'Only the question creator or a Research Room owner/editor can change the question disposition.' ),
    'ownership_transfer_guard' => false !== strpos( $backend, 'Room ownership is not silently transferable through a generic update.' ),
    'room_context_membership_required' => false !== strpos( $backend, '_require_room_member(payload.room_id, payload.owner_ref)' ),
    'cross_member_context_sources' => false !== strpos( $backend, 'library_objects_for_room(room_id, 1000)' ),
    'room_prompt_in_resolution' => false !== strpos( $backend, 'resolution["prompt_context"]["room_collaboration"] = room_prompt' ),
    'ask_room_provenance' => false !== strpos( $backend, 'provenance["room_collaboration"]' ),
    'ask_room_activity' => false !== strpos( $backend, '"event_type": "search"' ) && false !== strpos( $backend, 'room_id' ),
    'context_sanitizes_room_prompt' => false !== strpos( $context, 'room_collaboration' ) && false !== strpos( $context, 'collaborative workflow metadata' ),

    'wp_room_schema' => false !== strpos( $module, "const ROOM_SCHEMA = 'sc-research-room/1.0';" ),
    'wp_synthesis_schema' => false !== strpos( $module, "const ROOM_SYNTHESIS_SCHEMA = 'sc-research-room-synthesis/1.0';" ),
    'wp_room_routes' => false !== strpos( $module, "'/platform/v7/rooms'" ) && false !== strpos( $module, "'/platform/v7/rooms/(?P<room_id>" ),
    'wp_authorized_room' => false !== strpos( $module, 'private static function authorized_room(' ),
    'wp_role_guards' => false !== strpos( $module, "array( 'owner', 'editor' )" ) && false !== strpos( $module, "array( 'owner', 'editor', 'researcher' )" ),
    'wp_member_identity_resolution' => false !== strpos( $module, 'resolve_room_member_identity' ) && false !== strpos( $module, "get_user_by( 'email'" ),
    'wp_actor_server_side' => false !== strpos( $module, "'actor_ref' => self::owner_ref()" ),
    'wp_contributor_server_side' => false !== strpos( $module, "'contributed_by_ref' => self::owner_ref()" ),
    'wp_question_creator_server_side' => false !== strpos( $module, "'created_by_ref' => self::owner_ref()" ),
    'wp_position_server_side' => false !== strpos( $module, "'participant_ref' => self::owner_ref()" ),
    'wp_room_context_authorized' => false !== strpos( $module, '$room=self::authorized_room($room_id,false,false)' ),
    'wp_room_workspace_button' => false !== strpos( $module, 'data-sc-rl-v750-room-run' ),
    'wp_room_panel' => false !== strpos( $module, 'data-sc-rl-v750-room-panel' ),
    'wp_context_room_select' => false !== strpos( $module, 'data-sc-rl-v750-context-room' ),
    'wp_member_form' => false !== strpos( $module, 'data-sc-rl-v750-member-form' ),
    'wp_evidence_form' => false !== strpos( $module, 'data-sc-rl-v750-evidence-form' ),
    'wp_question_form' => false !== strpos( $module, 'data-sc-rl-v750-room-question-form' ),
    'wp_disagreement_form' => false !== strpos( $module, 'data-sc-rl-v750-disagreement-form' ),
    'wp_nonce_boundary' => false !== strpos( $module, 'checked_json' ) && false !== strpos( $module, 'X-WP-Nonce' ),

    'base_js_room_context' => false !== strpos( $base_js, 'current-research-room' ) && false !== strpos( $base_js, 'room_id:roomId' ),
    'room_js_loader' => false !== strpos( $js, 'async function loadRoom(roomId)' ),
    'room_js_membership' => false !== strpos( $js, '/members' ) && false !== strpos( $js, 'member_identity' ),
    'room_js_evidence' => false !== strpos( $js, '/evidence' ) && false !== strpos( $js, 'Evidence shared with room.' ),
    'room_js_questions' => false !== strpos( $js, '/questions' ) && false !== strpos( $js, 'Question added.' ),
    'room_js_disagreements' => false !== strpos( $js, '/disagreements' ) && false !== strpos( $js, 'Attributed position saved.' ),
    'room_js_context_promotion' => false !== strpos( $js, "scopes:['current-research-room']" ),
    'room_js_governance_copy' => false !== strpos( $js, 'Room inclusion is not a truth judgment.' ),
    'room_css_panel' => false !== strpos( $css, '.sc-rl-v750-room-panel' ),
    'room_css_summary' => false !== strpos( $css, '.sc-rl-v750-room-summary' ),
    'room_css_forms' => false !== strpos( $css, '.sc-rl-v750-room-forms' ),

    'manifest_version' => is_array( $manifest ) && '7.5.0' === ( $manifest['version'] ?? '' ),
    'manifest_api' => is_array( $manifest ) && 'sc-connected-research-api/1.4' === ( $manifest['api_schema'] ?? '' ),
    'manifest_workspace' => is_array( $manifest ) && 'sc-research-librarian-public-workspace/2.4' === ( $manifest['workspace_schema'] ?? '' ),
    'manifest_sqlite_15' => is_array( $manifest ) && 15 === ( $manifest['storage']['ancillary_sqlite_schema_version'] ?? 0 ),
    'manifest_no_postgres_migration' => is_array( $manifest ) && false === ( $manifest['storage']['new_postgres_migration_required'] ?? true ),
    'manifest_attribution' => is_array( $manifest ) && true === ( $manifest['governance']['participant_positions_remain_attributed'] ?? false ),
    'manifest_browser_actor_boundary' => is_array( $manifest ) && true === ( $manifest['privacy_boundaries']['browser_cannot_choose_actor_identity'] ?? false ),
    'manifest_shared_scope_preserved' => is_array( $manifest ) && true === ( $manifest['privacy_boundaries']['shared_source_retains_original_owner_and_scope'] ?? false ),
    'v740_manifest_preserved' => is_array( $v740 ) && '7.4.0' === ( $v740['version'] ?? '' ) && 14 === ( $v740['storage']['ancillary_sqlite_schema_version'] ?? 0 ),
    'docs_separate_state' => false !== strpos( $docs, 'shared room state does not replace individual research state' ),
    'docs_no_neon_migration' => false !== strpos( $docs, 'no Neon/Postgres knowledge-index migration' ),
    'docs_browser_identity_boundary' => false !== strpos( $docs, 'Browser payloads do not choose' ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.6.0', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
