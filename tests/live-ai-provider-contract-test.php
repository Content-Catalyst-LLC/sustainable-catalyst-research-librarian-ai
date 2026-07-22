<?php
/**
 * Static release contract checks for Research Librarian AI v7.1.0.
 *
 * Run: php tests/live-ai-provider-contract-test.php
 */

$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$admin = file_get_contents( $root . '/includes/class-sc-rl-v610-live-ai-admin.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$countries = json_decode( file_get_contents( $root . '/data/research_librarian_countries_v6.1.0.json' ), true );

$checks = array();
$failures = array();

$assert = static function ( $name, $condition, $detail = '' ) use ( &$checks, &$failures ) {
    $checks[ $name ] = (bool) $condition;
    if ( ! $condition ) {
        $failures[] = $name . ( $detail ? ': ' . $detail : '' );
    }
};

$assert( 'plugin_version_710', 1 === preg_match( "/const\s+VERSION\s*=\s*'7\.1\.0';/", $main ) );
$assert( 'public_ai_status_endpoint', false !== strpos( $main, "'/ai/status'" ) );
$assert( 'admin_ai_test_endpoint', false !== strpos( $main, "'/ai/test'" ) );
$assert( 'admin_ai_models_endpoint', false !== strpos( $main, "'/ai/models'" ) );
$assert( 'gemini_header_authentication', false !== strpos( $main, "'X-goog-api-key' => \$api_key" ) );
$assert( 'gemini_system_instruction', false !== strpos( $main, "'systemInstruction'" ) );
$assert( 'gemini_generation_url_has_no_query_key', 0 === preg_match( '#generateContent[^\n\r]*[?&]key=#i', $main ) );
$assert( 'gemini_model_prefix_normalized', false !== strpos( $main, "preg_replace( '#^models/#', '', sanitize_text_field( \$options['gemini_model'] ) )" ) );
$assert( 'current_sources_always_prepend_saved_index', false !== strpos( $main, '$records = array_merge( $this->source_records(), $records );' ) );
$assert( 'pakistan_evaluation_case', false !== strpos( $main, "'id' => 'pakistan-country-intelligence'" ) );
$assert( 'site_intelligence_evaluation_case', false !== strpos( $main, "'id' => 'climate-dashboard'" ) );
$assert( 'top_level_admin_menu', false !== strpos( $admin, "add_menu_page(" ) && false !== strpos( $admin, "Research Librarian AI" ) );
$assert( 'legacy_settings_cleanup', false !== strpos( $admin, "remove_submenu_page( 'options-general.php', \$slug )" ) );
$assert( 'provider_fallback_screen', false !== strpos( $admin, 'WordPress AI Provider Fallback' ) && false !== strpos( $admin, 'render_provider_page' ) );
$v630 = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$retrieval = file_get_contents( $root . '/backend/app/retrieval.py' );
$assert( 'python_intelligence_module', false !== strpos( $v630, 'SC_RL6_V630_Durable_Index' ) );
$assert( 'python_admin_submenu', false !== strpos( $v630, "'sc-rl-python-intelligence'" ) );
$assert( 'full_library_limit', false !== strpos( $v630, "'max_records' => 5000" ) );
$assert( 'render_fastapi_backend', false !== strpos( $backend, 'FastAPI(' ) && false !== strpos( $backend, '/v1/knowledge/sync' ) && false !== strpos( $backend, '/v1/ask' ) );
$assert( 'exact_title_ranking', false !== strpos( $retrieval, 'exact_title' ) && false !== strpos( $retrieval, '1000.0' ) );
$assert( 'public_status_simplified', false !== strpos( $js, "publicLabels" ) && false !== strpos( $js, "Research service online" ) );
$assert( 'public_status_state_handling', false !== strpos( $js, "state === 'not-configured'" ) && false !== strpos( $js, "state === 'offline'" ) );
$assert( 'public_status_styles', false !== strpos( $css, 'data-ai-health="online"' ) && false !== strpos( $css, 'data-ai-health="offline"' ) );
$assert( 'country_registry_shape', is_array( $countries ) && isset( $countries['countries'] ) && is_array( $countries['countries'] ) );
$assert( 'country_registry_count', isset( $countries['countries'] ) && 249 === count( $countries['countries'] ) );

$pakistan = null;
foreach ( (array) ( $countries['countries'] ?? array() ) as $country ) {
    if ( isset( $country['alpha3'] ) && 'PAK' === $country['alpha3'] ) {
        $pakistan = $country;
        break;
    }
}
$assert( 'pakistan_registry_record', is_array( $pakistan ) && 'Pakistan' === ( $pakistan['name'] ?? '' ) && 'PK' === ( $pakistan['alpha2'] ?? '' ) );

$result = array(
    'version' => '7.1.0',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failures ),
    'failed' => count( $failures ),
    'failures' => $failures,
);

echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failures ? 1 : 0 );
