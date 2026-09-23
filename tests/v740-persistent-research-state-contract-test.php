<?php
/** Static release contract for v7.4.0 persistent research state. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v700-connected-platform.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$state = file_get_contents( $root . '/backend/app/research_state.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$platform = file_get_contents( $root . '/backend/app/platform_v7.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$postgres = file_get_contents( $root . '/backend/app/postgres_store.py' );
$js = file_get_contents( $root . '/assets/sc-research-platform-v7.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$docs = file_get_contents( $root . '/docs/V740_PERSISTENT_RESEARCH_STATE_READING_HISTORY_OPEN_QUESTIONS.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_persistent_research_state_manifest_v7.4.0.json' ), true );
$quality_manifest = json_decode( file_get_contents( $root . '/data/research_librarian_source_evaluation_manifest_v7.3.0.json' ), true );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 8.8.0' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '8.8.0';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "8.8.0"' ),
    'module_version' => false !== strpos( $module, "const VERSION = '8.0.0';" ),
    'api_13' => false !== strpos( $platform, 'sc-connected-research-api/2.0' ),
    'workspace_23' => false !== strpos( $module, 'sc-research-librarian-public-workspace/3.0' ),
    'state_schema_constant' => false !== strpos( $module, 'sc-research-state-summary/1.0' ),
    'activity_schema' => false !== strpos( $state, 'sc-research-activity-event/1.0' ),
    'object_state_schema' => false !== strpos( $state, 'sc-research-object-state/1.0' ),
    'question_schema' => false !== strpos( $state, 'sc-research-open-question/1.0' ),
    'summary_schema' => false !== strpos( $state, 'sc-research-state-summary/1.0' ),
    'prompt_schema' => false !== strpos( $state, 'sc-research-state-prompt/1.0' ),
    'activity_normalizer' => false !== strpos( $state, 'def normalize_activity(' ),
    'object_state_normalizer' => false !== strpos( $state, 'def normalize_object_state(' ),
    'question_normalizer' => false !== strpos( $state, 'def normalize_open_question(' ),
    'state_summarizer' => false !== strpos( $state, 'def summarize_research_state(' ),
    'bounded_prompt' => false !== strpos( $state, 'def prompt_research_state(' ),
    'workflow_memory_boundary' => false !== strpos( $state, 'This is explicit, inspectable workflow memory. It is not factual evidence.' ),
    'prior_search_not_evidence' => false !== strpos( $state, 'Do not cite prior searches or open questions as support.' ),
    'reading_states' => false !== strpos( $state, '"unread"' ) && false !== strpos( $state, '"reading"' ) && false !== strpos( $state, '"reviewed"' ) && false !== strpos( $state, '"rejected"' ),
    'contradiction_states' => false !== strpos( $state, '"flagged"' ) && false !== strpos( $state, '"resolved"' ),
    'question_states' => false !== strpos( $state, '"open"' ) && false !== strpos( $state, '"deferred"' ) && false !== strpos( $state, '"dismissed"' ),
    'activity_request_model' => false !== strpos( $models, 'class ResearchActivityRequest' ),
    'object_request_model' => false !== strpos( $models, 'class ResearchObjectStateRequest' ),
    'question_request_model' => false !== strpos( $models, 'class ResearchOpenQuestionRequest' ),
    'ask_response_state' => false !== strpos( $models, 'research_state: dict[str, Any]' ),
    'sqlite_schema_14' => false !== strpos( $store, 'SCHEMA_VERSION = 19' ),
    'knowledge_index_schema_13' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/13.0' ),
    'activity_table' => false !== strpos( $store, 'research_activity_events' ),
    'object_state_table' => false !== strpos( $store, 'research_object_states' ),
    'question_table' => false !== strpos( $store, 'research_open_questions' ),
    'activity_store_methods' => false !== strpos( $store, 'def save_research_activity(' ) && false !== strpos( $store, 'def research_activities(' ),
    'object_store_methods' => false !== strpos( $store, 'def save_research_object_state(' ) && false !== strpos( $store, 'def research_object_states(' ),
    'question_store_methods' => false !== strpos( $store, 'def save_research_open_question(' ) && false !== strpos( $store, 'def research_open_questions(' ),
    'project_backup_state' => false !== strpos( $store, '"research_activity"' ) && false !== strpos( $store, '"object_states"' ) && false !== strpos( $store, '"open_questions"' ),
    'postgres_ancillary_delegate' => false !== strpos( $postgres, '__getattr__' ) && false !== strpos( $postgres, '_legacy' ),
    'state_summary_endpoint' => false !== strpos( $backend, '/v1/research/state/summary' ),
    'activity_endpoint' => false !== strpos( $backend, '/v1/research/activity' ),
    'object_state_endpoint' => false !== strpos( $backend, '/v1/research/object-states' ),
    'question_endpoint' => false !== strpos( $backend, '/v1/research/questions' ),
    'ask_state_summary' => false !== strpos( $backend, '_research_state_summary(' ),
    'ask_state_prompt' => false !== strpos( $backend, 'prompt_research_state(' ),
    'rejected_context_deprioritized' => false !== strpos( $backend, 'rejected_context_objects_deprioritized' ),
    'ask_search_activity' => false !== strpos( $backend, '"event_type": "search"' ),
    'backup_import_activity' => false !== strpos( $backend, 'research_activity' ) && false !== strpos( $backend, 'save_research_activity' ),
    'backup_import_object_state' => false !== strpos( $backend, 'object_states' ) && false !== strpos( $backend, 'save_research_object_state' ),
    'backup_import_questions' => false !== strpos( $backend, 'open_questions' ) && false !== strpos( $backend, 'save_research_open_question' ),
    'wordpress_state_get_route' => false !== strpos( $module, "'/platform/v7/state'" ),
    'wordpress_activity_route' => false !== strpos( $module, "'/platform/v7/state/activity'" ),
    'wordpress_object_route' => false !== strpos( $module, "'/platform/v7/state/object'" ),
    'wordpress_question_route' => false !== strpos( $module, "'/platform/v7/state/questions'" ),
    'wordpress_scope_authorization' => false !== strpos( $module, 'state_scope_for_current_user' ) && false !== strpos( $module, 'authorized_context' ) && false !== strpos( $module, 'authorized_project' ) && false !== strpos( $module, 'authorized_library_object' ),
    'wordpress_question_owner_check' => false !== strpos( $module, 'authorized_question_id' ),
    'wordpress_nonce_boundary' => false !== strpos( $module, 'checked_json' ) && false !== strpos( $module, 'X-WP-Nonce' ),
    'workspace_state_button' => false !== strpos( $module, 'data-sc-rl-v740-state-run' ),
    'workspace_state_panel' => false !== strpos( $module, 'data-sc-rl-v740-state-panel' ),
    'workspace_question_form' => false !== strpos( $module, 'data-sc-rl-v740-question-form' ),
    'js_state_renderer' => false !== strpos( $js, 'function renderState(body)' ),
    'js_state_loader' => false !== strpos( $js, 'function loadResearchState()' ),
    'js_reading_action' => false !== strpos( $js, 'data-sc-rl-v740-reading' ),
    'js_contradiction_action' => false !== strpos( $js, 'data-sc-rl-v740-contradiction' ),
    'js_question_action' => false !== strpos( $js, 'data-sc-rl-v740-question-status' ),
    'js_state_write' => false !== strpos( $js, "request('state/object'" ) && false !== strpos( $js, "request('state/questions'" ),
    'js_not_evidence_copy' => false !== strpos( $js, 'This is inspectable workflow memory, not evidence.' ),
    'css_state_panel' => false !== strpos( $css, '.sc-rl-v740-state-panel' ),
    'css_state_summary' => false !== strpos( $css, '.sc-rl-v740-state-summary' ),
    'css_question_form' => false !== strpos( $css, '.sc-rl-v740-question-form' ),
    'manifest_version' => is_array( $manifest ) && '7.4.0' === ( $manifest['version'] ?? '' ),
    'manifest_sqlite_14' => is_array( $manifest ) && 14 === ( $manifest['storage']['ancillary_sqlite_schema_version'] ?? 0 ),
    'manifest_index_13' => is_array( $manifest ) && 'sc-research-librarian-knowledge-index/13.0' === ( $manifest['storage']['knowledge_index_schema'] ?? '' ),
    'manifest_no_postgres_migration' => is_array( $manifest ) && false === ( $manifest['storage']['new_postgres_migration_required'] ?? true ),
    'manifest_not_evidence' => is_array( $manifest ) && true === ( $manifest['governance']['not_evidence'] ?? false ),
    'manifest_rejected_not_deleted' => is_array( $manifest ) && true === ( $manifest['governance']['rejected_objects_not_deleted'] ?? false ),
    'manifest_open_questions_not_facts' => is_array( $manifest ) && true === ( $manifest['governance']['open_questions_not_facts'] ?? false ),
    'v730_manifest_preserved' => is_array( $quality_manifest ) && '7.3.0' === ( $quality_manifest['version'] ?? '' ) && 'sc-connected-research-api/1.2' === ( $quality_manifest['api_schema'] ?? '' ),
    'v730_no_truth_score_preserved' => is_array( $quality_manifest ) && false === ( $quality_manifest['governance']['truth_score'] ?? true ),
    'docs_not_chat_memory' => false !== strpos( $docs, 'workflow memory, not chat memory and not evidence' ),
    'docs_no_neon_migration' => false !== strpos( $docs, 'no Neon/Postgres knowledge-index migration' ),
    'docs_backup' => false !== strpos( $docs, 'Project backup/export now includes research activity, object state, and open questions' ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.4.0', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
