<?php
/** Functional WordPress fallback reliability checks for v7.0.8. */
define( 'ABSPATH', '/tmp/sc-rl-wordpress/' );
class WP_Error { public $code; public $message; public $data; public function __construct( $code='', $message='', $data=null ) { $this->code=$code; $this->message=$message; $this->data=$data; } public function get_error_message(){return $this->message;} }
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
function wp_generate_uuid4() { return '66100000-0000-4000-8000-000000000001'; }
function wp_json_encode( $v, $flags = 0 ) { return json_encode( $v, $flags ); }
function apply_filters( $tag, $value ) { return $value; }
function is_wp_error( $v ) { return $v instanceof WP_Error; }

require dirname( __DIR__ ) . '/includes/class-sc-rl-v660-platform-handoffs.php';
$method = new ReflectionMethod( 'SC_RL6_V660_Platform_Handoffs', 'local_handoff' );
$method->setAccessible( true );
$handoff = $method->invoke( null, array(
    'destination' => 'workbench',
    'question' => 'Calculate a reliability score and preserve provenance.',
    'research_mode' => 'analyze',
    'session_id' => 'functional-661',
    'idempotency_key' => 'functional-prepare-661',
    'evidence' => array( array( 'record_id' => 'post:661', 'title' => 'Cross Product Reliability', 'url' => 'https://example.test/reliability', 'citation_label' => 'SC1' ) ),
) );
$valid = SC_RL6_V660_Platform_Handoffs::validate_payload( $handoff );
$tampered = $handoff;
$tampered['delivery']['token'] = str_repeat( '0', 64 );
$invalid = SC_RL6_V660_Platform_Handoffs::validate_payload( $tampered );
$old_version = SC_RL6_V660_Platform_Handoffs::version_compatibility( '3.9.9', '4.0.0', true, 'https://example.test' );
$unknown_version = SC_RL6_V660_Platform_Handoffs::version_compatibility( 'unknown', '4.0.0', true, 'https://example.test' );
$result = array(
    'version' => SC_RL6_V660_Platform_Handoffs::VERSION,
    'delivery_schema' => $handoff['delivery']['schema'] ?? '',
    'token_present' => ! empty( $handoff['delivery']['token'] ),
    'token_future' => strtotime( $handoff['delivery']['token_expires_utc'] ?? '' ) > time(),
    'idempotency_key' => $handoff['idempotency_key'] ?? '',
    'valid_original' => ! empty( $valid['ok'] ),
    'tampered_rejected' => empty( $invalid['ok'] ),
    'old_version_incompatible' => 'incompatible' === ( $old_version['state'] ?? '' ) && empty( $old_version['compatible'] ),
    'unknown_version_unverified' => 'unverified' === ( $unknown_version['state'] ?? '' ) && ! empty( $unknown_version['compatible'] ),
);
echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
$passed = '7.0.8' === $result['version']
    && 'sc-research-handoff-delivery/1.0' === $result['delivery_schema']
    && $result['token_present']
    && $result['token_future']
    && 'functional-prepare-661' === $result['idempotency_key']
    && $result['valid_original']
    && $result['tampered_rejected']
    && $result['old_version_incompatible']
    && $result['unknown_version_unverified'];
exit( $passed ? 0 : 1 );
