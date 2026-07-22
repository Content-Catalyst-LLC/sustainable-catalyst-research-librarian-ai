<?php
/** Static release contract checks for Research Librarian AI v6.5.1. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$docs = file_get_contents( $root . '/docs/V651_ACCESSIBILITY_PERFORMANCE_INTERFACE_RELIABILITY.md' );
$roadmap = file_get_contents( $root . '/docs/ROADMAP.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_accessibility_performance_manifest_v6.5.1.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.1.2' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '7.1.2';" ),
    'module_version' => false !== strpos( $module, "const VERSION = '7.1.2';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.1.2"' ),
    'workspace_schema_markup' => false !== strpos( $main, 'data-workspace-version="2.0"' ),
    'workspace_schema_backend' => false !== strpos( $backend, 'sc-research-librarian-public-workspace/2.0' ),
    'workspace_accessibility_profile' => false !== strpos( $backend, 'wcag-focused-v6.5.1' ),
    'workspace_rendering_profile' => false !== strpos( $backend, 'staged-v6.5.1' ),
    'mode_roving_tabindex_markup' => false !== strpos( $main, 'aria-checked="true" tabindex="0"' ) && false !== strpos( $main, 'aria-checked="false" tabindex="-1"' ),
    'mode_roving_tabindex_js' => false !== strpos( $js, "button.setAttribute('tabindex', active ? '0' : '-1')" ),
    'mode_arrow_navigation' => false !== strpos( $js, "['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End']" ),
    'combobox_semantics' => false !== strpos( $main, 'role="combobox"' ) && false !== strpos( $main, 'aria-haspopup="listbox"' ),
    'listbox_semantics' => false !== strpos( $main, 'role="listbox"' ) && false !== strpos( $js, 'role="option"' ),
    'active_descendant' => false !== strpos( $js, "setAttribute('aria-activedescendant'" ),
    'suggestion_selected_state' => false !== strpos( $js, "setAttribute('aria-selected'" ),
    'suggestion_enter_selection' => false !== strpos( $js, "event.key === 'Enter' && activeSuggestionIndex >= 0" ),
    'suggestion_escape' => false !== strpos( $js, "event.key === 'Escape'" ),
    'screen_reader_help' => false !== strpos( $main, 'sc-rl-sr-only' ) && false !== strpos( $main, 'Control or Command plus Enter' ),
    'status_live_region' => false !== strpos( $main, 'data-sc-rl-status role="status" aria-live="polite"' ),
    'announcer_live_region' => false !== strpos( $main, 'data-sc-rl-announcer role="status" aria-live="polite"' ),
    'progressbar_semantics' => false !== strpos( $main, 'role="progressbar"' ) && false !== strpos( $main, 'aria-valuemin="0"' ),
    'progressbar_updates' => false !== strpos( $js, "progress.setAttribute('aria-valuenow'" ) && false !== strpos( $js, "progress.setAttribute('aria-valuetext'" ),
    'result_heading_focus' => false !== strpos( $js, 'data-sc-rl-result-heading' ) && false !== strpos( $js, 'safeFocus(heading)' ),
    'error_focus' => false !== strpos( $js, 'role="alert" tabindex="-1"' ) && false !== strpos( $js, "safeFocus(answer.querySelector('[role=\"alert\"]'))" ),
    'feedback_dialog_markup' => false !== strpos( $main, 'data-sc-rl-feedback-dialog' ) && false !== strpos( $main, '<dialog class="sc-rl-ai__feedback-dialog"' ),
    'feedback_dialog_no_prompts' => false === strpos( $js, 'window.prompt(' ),
    'feedback_dialog_js' => false !== strpos( $js, 'function openFeedbackDialog' ) && false !== strpos( $js, 'function closeFeedbackDialog' ),
    'reduced_motion' => false !== strpos( $css, '@media (prefers-reduced-motion: reduce)' ),
    'forced_colors' => false !== strpos( $css, '@media (forced-colors: active)' ),
    'touch_targets' => false !== strpos( $css, 'min-height: 44px;' ),
    'shared_runtime_cache' => false !== strpos( $js, 'window.SCResearchLibrarianRuntime' ),
    'health_cache' => false !== strpos( $js, "sharedJson(aiStatusEndpoint, 'health', 45000" ),
    'route_cache' => false !== strpos( $js, "sharedJson(routesEndpoint, 'routes', 300000" ),
    'browser_suggestion_cache' => false !== strpos( $js, 'runtime.suggestions[key]' ) && false !== strpos( $js, 'nowMs() - cached.time < 300000' ),
    'wordpress_suggestion_cache' => false !== strpos( $module, "'sc_rl_v651_suggest_'" ) && false !== strpos( $module, '5 * MINUTE_IN_SECONDS' ),
    'ledger_cache_invalidation' => false !== strpos( $module, '$ledger_checksum' ) && false !== strpos( $module, 'self::VERSION . \'|\' . $ledger_checksum' ),
    'suggestion_cache_headers' => false !== strpos( $module, 'X-SC-RL-Suggestion-Cache' ) && false !== strpos( $module, 'stale-while-revalidate=240' ),
    'suggestion_abort' => false !== strpos( $js, 'suggestionController.abort()' ),
    'answer_abort' => false !== strpos( $js, 'currentAskController.abort()' ),
    'duplicate_answer_prevention' => false !== strpos( $js, 'Already researching this question' ),
    'staged_rendering' => false !== strpos( $js, 'nextFrame(function ()' ) && false !== strpos( $js, 'Preparing the direct response' ),
    'clipboard_fallback' => false !== strpos( $js, 'document.execCommand(\'copy\')' ),
    'download_cleanup_delay' => substr_count( $js, 'URL.revokeObjectURL(url); }, 1000' ) >= 2,
    'path_abort' => false !== strpos( $js, 'buildController.abort()' ),
    'deferred_script' => false !== strpos( $main, "wp_script_add_data( 'sc-research-librarian-ai', 'strategy', 'defer' )" ),
    'gzip_middleware' => false !== strpos( $backend, 'GZipMiddleware' ) && false !== strpos( $backend, 'minimum_size=900' ),
    'content_visibility' => false !== strpos( $css, 'content-visibility: auto;' ),
    'theme_scope' => false !== strpos( $css, '.sc-rl-ai--workspace button,' ) && false !== strpos( $css, 'touch-action: manipulation;' ),
    'admin_bar_offset' => false !== strpos( $css, '--wp-admin--admin-bar--height' ),
    'mobile_interface' => false !== strpos( $css, '@media (max-width: 560px)' ) && false !== strpos( $css, 'font-size: 16px;' ),
    'feedback_dialog_styles' => false !== strpos( $css, '.sc-rl-ai__feedback-dialog' ) && false !== strpos( $css, '::backdrop' ),
    'release_docs' => false !== strpos( $docs, 'Accessibility, Performance, and Interface Reliability' ),
    'roadmap_complete' => false !== strpos( $roadmap, 'v6.5.1 — Accessibility, Performance, and Interface Reliability — Complete' ),
    'manifest_version' => is_array( $manifest ) && '6.5.1' === ( $manifest['version'] ?? '' ),
    'manifest_workspace_schema' => is_array( $manifest ) && 'sc-research-librarian-public-workspace/1.1' === ( $manifest['workspace_schema'] ?? '' ),
    'manifest_free_tier' => is_array( $manifest ) && false === ( $manifest['compatibility']['paid_vector_database_required'] ?? true ),
    'black_green_prompt_preserved' => is_array( $manifest ) && true === ( $manifest['compatibility']['black_green_prompt_preserved'] ?? false ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array(
    'version' => '7.1.2',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
