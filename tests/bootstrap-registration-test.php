<?php
/**
 * Standalone regression test for Research Librarian AI v6.5.1.
 * Run: php tests/bootstrap-registration-test.php
 */
error_reporting( E_ALL );
ini_set( 'display_errors', '1' );

define( 'ABSPATH', '/tmp/sc-rl-wordpress/' );
define( 'WP_PLUGIN_DIR', dirname( __DIR__, 2 ) );
define( 'HOUR_IN_SECONDS', 3600 );
define( 'DAY_IN_SECONDS', 86400 );
define( 'WEEK_IN_SECONDS', 604800 );
define( 'MONTH_IN_SECONDS', 2592000 );

class WP_REST_Server { const READABLE = 'GET'; const CREATABLE = 'POST'; }
class WP_REST_Request {}
class WP_REST_Response { public function __construct( $data = null, $status = 200 ) {} }
class WP_Error {
    private $code; private $message; private $data;
    public function __construct( $code = '', $message = '', $data = null ) { $this->code=$code; $this->message=$message; $this->data=$data; }
    public function get_error_code(){ return $this->code; }
    public function get_error_message(){ return $this->message; }
    public function get_error_data(){ return $this->data; }
    public function add_data( $data, $code = '' ){ $this->data=$data; }
}

$GLOBALS['sc_rl_test_actions'] = array();
$GLOBALS['sc_rl_test_filters'] = array();
$GLOBALS['sc_rl_test_shortcodes'] = array();
$GLOBALS['sc_rl_test_rest'] = array();
$GLOBALS['sc_rl_test_top_pages'] = array();
$GLOBALS['sc_rl_test_sub_pages'] = array();
$GLOBALS['sc_rl_test_removed_settings'] = array();
$GLOBALS['sc_rl_test_options'] = array();

function add_action( $hook, $callback, $priority = 10, $accepted_args = 1 ) { $GLOBALS['sc_rl_test_actions'][ $hook ][] = array( 'callback'=>$callback, 'priority'=>$priority ); return true; }
function add_filter( $hook, $callback, $priority = 10, $accepted_args = 1 ) { $GLOBALS['sc_rl_test_filters'][ $hook ][] = array( 'callback'=>$callback, 'priority'=>$priority ); return true; }
function add_shortcode( $tag, $callback ) { $GLOBALS['sc_rl_test_shortcodes'][ $tag ] = $callback; return true; }
function register_rest_route( $namespace, $route, $args ) { $GLOBALS['sc_rl_test_rest'][ $namespace . $route ] = $args; return true; }
function register_activation_hook( $file, $callback ) {}
function register_deactivation_hook( $file, $callback ) {}
function plugin_basename( $file ) { return basename( dirname( $file ) ) . '/' . basename( $file ); }
function plugin_dir_path( $file ) { return rtrim( dirname( $file ), '/' ) . '/'; }
function plugins_url( $path = '', $file = '' ) { return 'https://example.test/plugins/' . trim( $path, '/' ); }
function get_option( $name, $default = false ) { return array_key_exists( $name, $GLOBALS['sc_rl_test_options'] ) ? $GLOBALS['sc_rl_test_options'][ $name ] : $default; }
function update_option( $name, $value, $autoload = null ) { $GLOBALS['sc_rl_test_options'][ $name ] = $value; return true; }
function is_admin() { return true; }
function current_user_can( $capability ) { return true; }
function esc_html( $value ) { return (string) $value; }
function esc_attr( $value ) { return (string) $value; }
function esc_url( $value ) { return (string) $value; }
function admin_url( $path = '' ) { return 'https://example.test/wp-admin/' . $path; }
function home_url( $path = '' ) { return 'https://example.test' . $path; }
function rest_url( $path = '' ) { return 'https://example.test/wp-json/' . ltrim( $path, '/' ); }
function add_menu_page( $page_title, $menu_title, $capability, $menu_slug, $callback, $icon = '', $position = null ) { $GLOBALS['sc_rl_test_top_pages'][ $menu_slug ] = array( 'title'=>$page_title, 'callback'=>$callback ); return $menu_slug; }
function add_submenu_page( $parent, $page_title, $menu_title, $capability, $menu_slug, $callback ) { $GLOBALS['sc_rl_test_sub_pages'][ $parent ][ $menu_slug ] = array( 'title'=>$page_title, 'callback'=>$callback ); return $menu_slug; }
function add_options_page( $page_title, $menu_title, $capability, $menu_slug, $callback ) { return add_submenu_page( 'options-general.php', $page_title, $menu_title, $capability, $menu_slug, $callback ); }
function remove_submenu_page( $parent, $slug ) { $GLOBALS['sc_rl_test_removed_settings'][] = $slug; if(isset($GLOBALS['sc_rl_test_sub_pages'][$parent][$slug])) unset($GLOBALS['sc_rl_test_sub_pages'][$parent][$slug]); return true; }
function register_setting( $group, $name, $args = array() ) { $GLOBALS['sc_rl_test_settings'][ $name ] = array( 'group'=>$group, 'args'=>$args ); return true; }
function add_settings_section( $id, $title, $callback, $page ) { return true; }
function add_settings_field( $id, $title, $callback, $page, $section = 'default', $args = array() ) { return true; }
function __( $text, $domain = 'default' ) { return $text; }
function esc_html__( $text, $domain = 'default' ) { return $text; }
function sanitize_text_field( $value ) { return trim( strip_tags( (string) $value ) ); }
function sanitize_textarea_field( $value ) { return trim( strip_tags( (string) $value ) ); }
function sanitize_key( $value ) { return preg_replace( '/[^a-z0-9_\-]/', '', strtolower( (string) $value ) ); }
function wp_strip_all_tags( $value ) { return strip_tags( (string) $value ); }
function wp_unslash( $value ) { return $value; }
function wp_parse_args( $args, $defaults = array() ) { return array_merge( $defaults, is_array($args) ? $args : array() ); }
function absint( $value ) { return abs( (int) $value ); }
function esc_url_raw( $value ) { return (string) $value; }
function sanitize_email( $value ) { return (string) $value; }
function is_wp_error( $value ) { return $value instanceof WP_Error; }
function wp_json_encode( $value ) { return json_encode( $value ); }
function wp_next_scheduled( $hook ) { return false; }
function wp_schedule_event( $timestamp, $recurrence, $hook, $args = array() ) { return true; }
function wp_schedule_single_event( $timestamp, $hook, $args = array() ) { return true; }
function wp_clear_scheduled_hook( $hook ) { return true; }
function add_settings_error() {}

// Simulate a legacy historic class. v6.2 must still bootstrap under its unique core class.
class Sustainable_Catalyst_Research_Librarian_AI { const VERSION = 'legacy-test'; }

require dirname( __DIR__ ) . '/sustainable-catalyst-research-librarian-ai.php';

foreach ( array( 'init', 'rest_api_init', 'admin_menu', 'admin_init' ) as $hook ) {
    $callbacks = $GLOBALS['sc_rl_test_actions'][ $hook ] ?? array();
    usort( $callbacks, function( $a, $b ){ return $a['priority'] <=> $b['priority']; } );
    foreach ( $callbacks as $row ) { call_user_func( $row['callback'] ); }
}

$core = SC_RL6_Core::instance();
$pakistan = $core->resolve_route( 'What Sustainable Catalyst resources should I use to research climate and infrastructure in Pakistan?' );
$dashboard = $core->resolve_route( 'Show me a climate dashboard with public indicators and Earth observation data.' );

$required_shortcodes = array( 'sustainable_catalyst_research_librarian_ai', 'sc_research_librarian', 'sc_research_guidance_platform', 'sc_research_guidance_journey', 'sc_research_librarian_platform_handoffs' );
$missing_shortcodes = array_values( array_filter( $required_shortcodes, function( $tag ){ return empty( $GLOBALS['sc_rl_test_shortcodes'][ $tag ] ); } ) );
$required_rest = array(
    'sc-research-librarian-ai/v1/ai/status',
    'sc-research-librarian-ai/v1/ai/test',
    'sc-research-librarian-ai/v1/ai/models',
    'sc-research-librarian-ai/v1/python/status',
    'sc-research-librarian-ai/v1/python/suggest',
    'sc-research-librarian-ai/v1/python/sync',
    'sc-research-librarian-ai/v1/python/diagnostics',
    'sc-research-librarian-ai/v1/python/sync-report',
    'sc-research-librarian-ai/v1/python/repair',
    'sc-research-librarian-ai/v1/python/manifest',
    'sc-research-librarian-ai/v1/python/snapshots',
    'sc-research-librarian-ai/v1/python/recover',
    'sc-research-librarian-ai/v1/python/rollback',
    'sc-research-librarian-ai/v1/nonce',
    'sc-research-librarian-ai/v1/rate-limit/status',
    'sc-research-librarian-ai/v1/rate-limit/reset',
    'sc-research-librarian-ai/v1/platform/capabilities',
    'sc-research-librarian-ai/v1/platform/handoff/prepare',
    'sc-research-librarian-ai/v1/platform/handoff/validate',
    'sc-research-librarian-ai/v1/platform/artifact/return',
    'sc-research-librarian-ai/v1/platform/handoffs/export',
);
$missing_rest = array_values( array_filter( $required_rest, function( $route ){ return empty( $GLOBALS['sc_rl_test_rest'][ $route ] ); } ) );

$result = array(
    'version' => SC_RL6_Core::VERSION,
    'core_loaded' => class_exists( 'SC_RL6_Core', false ),
    'legacy_class_detected' => defined( 'SC_RL6_LEGACY_CLASS_WAS_PRESENT' ) && SC_RL6_LEGACY_CLASS_WAS_PRESENT,
    'missing_shortcodes' => $missing_shortcodes,
    'missing_ai_rest_routes' => $missing_rest,
    'top_level_menu' => isset( $GLOBALS['sc_rl_test_top_pages']['sc-research-librarian-ai'] ),
    'settings_menu_cleaned' => in_array( 'sc-rl-integrated-guidance', $GLOBALS['sc_rl_test_removed_settings'], true ) && ! isset( $GLOBALS['sc_rl_test_sub_pages']['options-general.php']['sc-rl-integrated-guidance'] ),
    'python_submenu' => isset( $GLOBALS['sc_rl_test_sub_pages']['sc-research-librarian-ai']['sc-rl-python-intelligence'] ),
    'provider_fallback_hidden_page' => isset( $GLOBALS['sc_rl_test_sub_pages']['']['sc-rl-ai-provider'] ) || isset( $GLOBALS['sc_rl_test_sub_pages'][null]['sc-rl-ai-provider'] ),
    'pakistan_route_id' => $pakistan['id'] ?? '',
    'pakistan_alpha3' => $pakistan['matched_country']['alpha3'] ?? '',
    'pakistan_url' => $pakistan['url'] ?? '',
    'dashboard_route_id' => $dashboard['id'] ?? '',
);

echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;

$passed = '7.0.5' === $result['version']
    && $result['core_loaded']
    && $result['legacy_class_detected']
    && empty( $result['missing_shortcodes'] )
    && empty( $result['missing_ai_rest_routes'] )
    && $result['top_level_menu']
    && $result['settings_menu_cleaned']
    && $result['python_submenu']
    && $result['provider_fallback_hidden_page']
    && 'country-intelligence' === $result['pakistan_route_id']
    && 'PAK' === $result['pakistan_alpha3']
    && false !== strpos( $result['pakistan_url'], 'country=PAK' )
    && 'site-intelligence' === $result['dashboard_route_id'];

exit( $passed ? 0 : 1 );
