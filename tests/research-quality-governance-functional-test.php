<?php
/** Functional WordPress governance defaults and methodology checks for v7.0.5. */
define( 'ABSPATH', '/tmp/sc-rl-wordpress/' );
class WP_Error { public function __construct($c='',$m='',$d=null){} }
function add_action() {}
function add_shortcode() {}
function register_rest_route() {}
function add_submenu_page() {}
function get_option( $name, $default = false ) { return $default; }
function update_option() { return true; }
function wp_parse_args( $args, $defaults = array() ) { return array_merge( $defaults, is_array( $args ) ? $args : array() ); }
function sanitize_text_field( $v ) { return trim( strip_tags( (string) $v ) ); }
function absint( $v ) { return abs( intval( $v ) ); }
function is_wp_error( $v ) { return $v instanceof WP_Error; }
require dirname( __DIR__ ) . '/includes/class-sc-rl-v670-governance-center.php';
$policy = SC_RL6_V670_Governance_Center::local_policy();
$methodology = SC_RL6_V670_Governance_Center::methodology();
$result = array(
    'version' => SC_RL6_V670_Governance_Center::VERSION,
    'policy_schema' => $policy['schema'] ?? '',
    'profile' => $policy['profile'] ?? '',
    'query_text_stored' => ! empty( $policy['retention']['store_query_text'] ),
    'answer_text_stored' => ! empty( $policy['retention']['store_answer_text'] ),
    'automatic_publication' => ! empty( $policy['human_review']['allow_automatic_publication'] ),
    'methodology_schema' => $methodology['schema'] ?? '',
    'limitations' => count( $methodology['limitations'] ?? array() ),
);
echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
$passed = '7.0.5' === $result['version']
    && 'sc-research-governance-policy/1.0' === $result['policy_schema']
    && 'public-trust-v7.0.5' === $result['profile']
    && ! $result['query_text_stored']
    && ! $result['answer_text_stored']
    && ! $result['automatic_publication']
    && 'sc-research-methodology/1.0' === $result['methodology_schema']
    && $result['limitations'] >= 3;
exit( $passed ? 0 : 1 );
