<?php
/** Static release contract checks for Research Librarian AI v6.5.1. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$docs = file_get_contents( $root . '/docs/V650_PRODUCTION_PUBLIC_RESEARCH_WORKSPACE.md' );
$install = file_get_contents( $root . '/docs/INSTALL.md' );
$roadmap = file_get_contents( $root . '/docs/ROADMAP.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_public_workspace_manifest_v6.5.0.json' ), true );

$modes = array( 'auto', 'title', 'subject', 'path', 'evidence', 'analyze', 'compare', 'decision' );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.1.2' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '7.1.2';" ),
    'module_version' => false !== strpos( $module, "const VERSION = '7.1.2';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.1.2"' ),
    'workspace_root_class' => false !== strpos( $main, 'sc-rl-ai--workspace' ),
    'workspace_data_version' => false !== strpos( $main, 'data-workspace-version="2.0"' ),
    'mode_picker' => false !== strpos( $main, 'data-sc-rl-mode-picker' ),
    'mode_radiogroup' => false !== strpos( $main, 'role="radiogroup"' ),
    'mode_label' => false !== strpos( $main, 'data-sc-rl-mode-label' ),
    'workspace_submit' => false !== strpos( $main, 'Start Research' ),
    'answer_first_intro' => false !== strpos( $main, 'Choose the kind of help you need' ),
    'progress_markup' => false !== strpos( $main, 'data-sc-rl-progress' ) && false !== strpos( $main, 'data-sc-rl-progress-bar' ),
    'session_bar' => false !== strpos( $main, 'data-sc-rl-session-bar' ),
    'session_reset_button' => false !== strpos( $main, 'data-sc-rl-reset-session' ),
    'follow_up_section' => false !== strpos( $main, 'data-sc-rl-follow-ups' ) && false !== strpos( $main, 'Continue this research' ),
    'copy_answer' => false !== strpos( $main, 'data-sc-rl-copy-answer' ),
    'markdown_export' => false !== strpos( $main, 'data-sc-rl-download-markdown' ),
    'json_export' => false !== strpos( $main, 'data-sc-rl-download' ),
    'research_note_export' => false !== strpos( $main, 'data-sc-rl-research-note' ),
    'print_workspace' => false !== strpos( $main, 'data-sc-rl-print' ),
    'typed_handoff_export' => false !== strpos( $main, 'data-sc-rl-handoff-download' ),
    'save_session' => false !== strpos( $main, 'data-sc-rl-save-session' ),
    'feedback_controls' => false !== strpos( $main, 'data-sc-rl-feedback-helpful' ) && false !== strpos( $main, 'data-sc-rl-feedback-issue' ),
    'example_modes' => substr_count( $main, 'data-sc-rl-example-mode=' ) >= 5,
    'title_suggestions_aria' => false !== strpos( $main, 'aria-autocomplete="list"' ) && false !== strpos( $main, 'aria-expanded="false"' ),
    'ask_request_mode_model' => false !== strpos( $models, 'research_mode: str = Field(' ),
    'ask_request_mode_pattern' => false !== strpos( $models, 'auto|title|subject|path|evidence|analyze|compare|decision' ),
    'ask_response_followups' => false !== strpos( $models, 'follow_up_prompts: list[str]' ),
    'ask_response_workspace' => false !== strpos( $models, 'workspace: dict[str, Any]' ),
    'ask_response_session_turns' => false !== strpos( $models, 'session_turns: int = 0' ),
    'session_reset_model' => false !== strpos( $models, 'class SessionResetRequest(BaseModel)' ),
    'research_modes_backend' => false !== strpos( $backend, '_RESEARCH_MODES' ),
    'mode_resolver' => false !== strpos( $backend, 'def _resolve_research_mode' ),
    'followup_builder' => false !== strpos( $backend, 'def _follow_up_prompts' ),
    'workspace_builder' => false !== strpos( $backend, 'def _workspace_summary' ),
    'workspace_schema' => false !== strpos( $backend, 'sc-research-librarian-public-workspace/2.0' ),
    'session_reset_endpoint' => false !== strpos( $backend, '@app.post("/v1/session/reset"' ),
    'ask_resolves_mode' => false !== strpos( $backend, 'research_mode = _resolve_research_mode' ),
    'ask_returns_followups' => false !== strpos( $backend, 'follow_up_prompts=_follow_up_prompts' ),
    'ask_returns_workspace' => false !== strpos( $backend, 'workspace=_workspace_summary' ),
    'ask_returns_session_turns' => false !== strpos( $backend, 'session_turns=len(_sessions[session_id]) // 2' ),
    'wordpress_forwards_mode' => false !== strpos( $module, "'research_mode' => in_array" ),
    'wordpress_normalizes_followups' => false !== strpos( $module, "\$grounding['follow_up_prompts']" ),
    'wordpress_normalizes_workspace' => false !== strpos( $module, "\$grounding['workspace']" ),
    'wordpress_normalizes_turns' => false !== strpos( $module, "\$grounding['session_turns']" ),
    'route_note_version' => false !== strpos( $module, 'sc-research-librarian-route-note/7.1.2' ),
    'public_handler_sanitizes_mode' => false !== strpos( $main, "\$research_mode = isset( \$params['research_mode'] )" ),
    'js_sends_mode' => false !== strpos( $js, 'research_mode: currentMode' ),
    'js_mode_persistence' => false !== strpos( $js, 'sc_rl_ai_research_mode' ),
    'js_workspace_markdown' => false !== strpos( $js, 'function workspaceMarkdown' ),
    'js_download_text' => false !== strpos( $js, 'function downloadText' ),
    'js_answer_workspace_header' => false !== strpos( $js, 'Production research workspace' ),
    'js_generated_fallback_label' => false !== strpos( $js, 'Verified evidence fallback' ),
    'js_progress' => false !== strpos( $js, 'function setProgress' ),
    'js_session_update' => false !== strpos( $js, 'function updateSession' ),
    'js_followup_render' => false !== strpos( $js, 'function renderFollowUps' ),
    'js_session_reset' => false !== strpos( $js, "window.localStorage.removeItem('sc_rl_ai_session_id')" ),
    'js_title_mode_on_suggestion' => false !== strpos( $js, "setMode('title', true)" ),
    'js_suggestion_arrow_navigation' => false !== strpos( $js, "event.key === 'ArrowDown'") && false !== strpos( $js, "event.key === 'ArrowUp'" ),
    'js_suggestion_escape' => false !== strpos( $js, "event.key === 'Escape'" ),
    'js_aria_expanded' => false !== strpos( $js, "setAttribute('aria-expanded', 'true')" ) && false !== strpos( $js, "setAttribute('aria-expanded', 'false')" ),
    'js_answer_busy_state' => false !== strpos( $js, "answerCard.setAttribute('aria-busy'" ),
    'css_two_pane_layout' => false !== strpos( $css, 'grid-template-columns: minmax(320px, .82fr) minmax(0, 1.38fr)' ),
    'css_sticky_prompt' => false !== strpos( $css, '.sc-rl-ai--workspace .sc-rl-ai__ask-card' ) && false !== strpos( $css, 'position: sticky' ),
    'css_mode_picker' => false !== strpos( $css, '.sc-rl-ai__mode-picker' ),
    'css_terminal_background' => false !== strpos( $css, '.sc-rl-ai__textarea {' ) && false !== strpos( $css, 'background: #000;' ),
    'css_terminal_green_text' => false !== strpos( $css, 'color: #7dff91;' ) && false !== strpos( $css, 'caret-color: #7dff91;' ),
    'css_terminal_placeholder' => false !== strpos( $css, '.sc-rl-ai__textarea::placeholder' ),
    'css_terminal_focus' => false !== strpos( $css, '.sc-rl-ai__textarea:focus-visible' ) && false !== strpos( $css, 'rgba(125,255,145,.24)' ),
    'css_light_answer_surface' => false !== strpos( $css, '.sc-rl-production-answer__response' ) && false !== strpos( $css, 'background: #fff;' ),
    'css_followups' => false !== strpos( $css, '.sc-rl-ai__follow-ups' ),
    'css_busy_state' => false !== strpos( $css, '.sc-rl-ai__answer-card[aria-busy="true"]' ),
    'css_mobile_single_column' => false !== strpos( $css, '@media (max-width: 1100px)' ) && false !== strpos( $css, 'grid-template-columns: 1fr;' ),
    'css_print_workspace' => false !== strpos( $css, '@media print' ) && false !== strpos( $css, '.sc-rl-ai.is-printing' ),
    'release_documentation' => false !== strpos( $docs, 'Production Public Research Workspace' ) && false !== strpos( $docs, 'Accessible title suggestions' ),
    'install_verification' => false !== strpos( $install, 'Verify the public workspace' ) && false !== strpos( $install, 'all eight research-mode controls' ),
    'roadmap_complete' => false !== strpos( $roadmap, 'v6.5.0 — Production Public Research Workspace — Complete' ),
    'release_manifest' => is_array( $manifest ) && '6.5.0' === ( $manifest['version'] ?? '' ) && 'sc-research-librarian-public-workspace/1.0' === ( $manifest['workspace_schema'] ?? '' ),
    'manifest_eight_modes' => is_array( $manifest ) && 8 === count( $manifest['research_modes'] ?? array() ),
    'manifest_deterministic_fallback' => is_array( $manifest ) && true === ( $manifest['compatibility']['deterministic_fallback_available'] ?? false ),
    'manifest_free_tier' => is_array( $manifest ) && false === ( $manifest['compatibility']['paid_vector_database_required'] ?? true ),
);
foreach ( $modes as $mode ) {
    $checks[ 'mode_markup_' . $mode ] = false !== strpos( $main, 'data-sc-rl-mode="' . $mode . '"' );
    $checks[ 'mode_backend_' . $mode ] = false !== strpos( $backend, '"' . $mode . '": {' );
}
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array(
    'version' => '7.1.2',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
