<?php
/** Functional WordPress-fallback handoff and tamper-validation test for v7.0.1. */
define( 'ABSPATH', '/tmp/sc-rl-wordpress/' );
class WP_Error { public function __construct( $code='', $message='', $data=null ) {} }
function add_action() {}
function add_shortcode() {}
function register_rest_route() {}
function get_option( $name, $default = false ) { return $default; }
function update_option() { return true; }
function wp_parse_args( $args, $defaults = array() ) { return array_merge( $defaults, is_array( $args ) ? $args : array() ); }
function sanitize_key( $v ) { return preg_replace( '/[^a-z0-9_\-]/', '', strtolower( (string) $v ) ); }
function sanitize_text_field( $v ) { return trim( strip_tags( (string) $v ) ); }
function sanitize_textarea_field( $v ) { return trim( strip_tags( (string) $v ) ); }
function esc_url_raw( $v ) { return (string) $v; }
function absint( $v ) { return abs( intval( $v ) ); }
function wp_generate_uuid4() { return '66000000-0000-4000-8000-000000000001'; }
function wp_json_encode( $v, $flags = 0 ) { return json_encode( $v, $flags ); }
function apply_filters( $tag, $value ) { return $value; }
function is_wp_error( $v ) { return $v instanceof WP_Error; }

require dirname( __DIR__ ) . '/includes/class-sc-rl-v660-platform-handoffs.php';
$method = new ReflectionMethod( 'SC_RL6_V660_Platform_Handoffs', 'local_handoff' );
$method->setAccessible( true );
$handoff = $method->invoke( null, array(
    'destination' => 'workbench',
    'question' => 'Calculate power from voltage and current.',
    'research_mode' => 'analyze',
    'session_id' => 'functional-660',
    'evidence' => array( array( 'record_id' => 'post:1', 'title' => 'Power', 'url' => 'https://example.test/power', 'citation_label' => 'SC1' ) ),
) );
$valid = SC_RL6_V660_Platform_Handoffs::validate_payload( $handoff );
$tampered = $handoff;
$tampered['question'] = 'Changed after signing';
$invalid = SC_RL6_V660_Platform_Handoffs::validate_payload( $tampered );
$result = array(
    'version' => SC_RL6_V660_Platform_Handoffs::VERSION,
    'schema' => $handoff['schema'] ?? '',
    'destination_contract' => $handoff['payload']['contract'] ?? '',
    'fingerprint_present' => ! empty( $handoff['provenance']['payload_fingerprint'] ),
    'valid_original' => ! empty( $valid['ok'] ),
    'tamper_rejected' => empty( $invalid['ok'] ) && in_array( 'Payload fingerprint does not match the handoff contents.', $invalid['errors'] ?? array(), true ),
);
echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
$passed = '7.0.1' === $result['version']
    && 'sc-research-handoff/2.0' === $result['schema']
    && 'sc-workbench-task/1.0' === $result['destination_contract']
    && $result['fingerprint_present']
    && $result['valid_original']
    && $result['tamper_rejected'];
exit( $passed ? 0 : 1 );
