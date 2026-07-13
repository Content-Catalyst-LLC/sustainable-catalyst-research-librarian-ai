<?php
/** Functional retry and alert-suppression tests for v6.3.1. */
error_reporting( E_ALL );
ini_set( 'display_errors', '1' );

define( 'ABSPATH', sys_get_temp_dir() . '/sc-rl-v631-functional/' );
define( 'MINUTE_IN_SECONDS', 60 );
define( 'HOUR_IN_SECONDS', 3600 );

class WP_Error {
    private $code; private $message; private $data;
    public function __construct( $code = '', $message = '', $data = null ) { $this->code=$code; $this->message=$message; $this->data=$data; }
    public function get_error_code(){ return $this->code; }
    public function get_error_message(){ return $this->message; }
    public function get_error_data(){ return $this->data; }
}

$GLOBALS['sc_rl_v631_options'] = array();
$GLOBALS['sc_rl_v631_cron'] = array();
function get_option( $name, $default = false ) { return array_key_exists( $name, $GLOBALS['sc_rl_v631_options'] ) ? $GLOBALS['sc_rl_v631_options'][ $name ] : $default; }
function update_option( $name, $value, $autoload = null ) { $GLOBALS['sc_rl_v631_options'][ $name ] = $value; return true; }
function delete_option( $name ) { unset( $GLOBALS['sc_rl_v631_options'][ $name ] ); return true; }
function wp_parse_args( $args, $defaults = array() ) { return array_merge( $defaults, is_array( $args ) ? $args : array() ); }
function absint( $value ) { return abs( (int) $value ); }
function sanitize_text_field( $value ) { return trim( strip_tags( (string) $value ) ); }
function sanitize_key( $value ) { return strtolower( preg_replace( '/[^a-z0-9_\-]/', '', (string) $value ) ); }
function wp_next_scheduled( $hook ) { return $GLOBALS['sc_rl_v631_cron'][ $hook ] ?? false; }
function wp_schedule_single_event( $timestamp, $hook ) { $GLOBALS['sc_rl_v631_cron'][ $hook ] = $timestamp; return true; }
function wp_clear_scheduled_hook( $hook ) { unset( $GLOBALS['sc_rl_v631_cron'][ $hook ] ); return true; }
function is_wp_error( $value ) { return $value instanceof WP_Error; }

require dirname( __DIR__ ) . '/includes/class-sc-rl-v630-durable-index.php';

$GLOBALS['sc_rl_v631_options'][ SC_RL6_V630_Durable_Index::OPTION_NAME ] = array(
    'backend_url' => 'https://example.onrender.com',
    'retry_base_seconds' => 10,
    'retry_max_seconds' => 40,
    'max_retry_attempts' => 3,
    'alert_suppression_minutes' => 15,
);

$failed = array();
$retry_delay = new ReflectionMethod( 'SC_RL6_V630_Durable_Index', 'retry_delay' );
$retry_delay->setAccessible( true );
$delays = array();
foreach ( array( 1, 2, 3, 4 ) as $attempt ) { $delays[] = $retry_delay->invoke( null, $attempt ); }
if ( array( 10, 20, 40, 40 ) !== $delays ) { $failed[] = 'Unexpected exponential retry delays: ' . json_encode( $delays ); }

$schedule_retry = new ReflectionMethod( 'SC_RL6_V630_Durable_Index', 'schedule_full_retry' );
$schedule_retry->setAccessible( true );
for ( $attempt = 1; $attempt <= 3; $attempt++ ) {
    wp_clear_scheduled_hook( SC_RL6_V630_Durable_Index::SYNC_RETRY_HOOK );
    if ( true !== $schedule_retry->invoke( null, 'temporary failure ' . $attempt ) ) { $failed[] = 'Retry attempt ' . $attempt . ' was not scheduled'; }
}
wp_clear_scheduled_hook( SC_RL6_V630_Durable_Index::SYNC_RETRY_HOOK );
if ( false !== $schedule_retry->invoke( null, 'permanent failure' ) ) { $failed[] = 'Retry ceiling did not stop scheduling'; }
$retry_state = get_option( SC_RL6_V630_Durable_Index::SYNC_RETRY_OPTION, array() );
if ( 'exhausted' !== ( $retry_state['state'] ?? '' ) || 3 !== ( $retry_state['attempt'] ?? 0 ) ) { $failed[] = 'Retry exhaustion state is incorrect'; }

$alert = new ReflectionMethod( 'SC_RL6_V630_Durable_Index', 'register_public_alert' );
$alert->setAccessible( true );
$first = $alert->invoke( null, 'backend-cold-start' );
$second = $alert->invoke( null, 'backend-cold-start' );
$permanent = $alert->invoke( null, 'integration-key-mismatch' );
if ( ! empty( $first['suppress_notice'] ) ) { $failed[] = 'First transient notice was incorrectly suppressed'; }
if ( empty( $second['suppress_notice'] ) || 2 !== ( $second['alert_occurrences'] ?? 0 ) ) { $failed[] = 'Repeated transient notice was not suppressed'; }
if ( ! empty( $permanent['suppress_notice'] ) ) { $failed[] = 'Permanent configuration notice was incorrectly suppressed'; }

$result = array(
    'version' => SC_RL6_V630_Durable_Index::VERSION,
    'retry_delays' => $delays,
    'retry_state' => $retry_state,
    'first_alert_suppressed' => ! empty( $first['suppress_notice'] ),
    'second_alert_suppressed' => ! empty( $second['suppress_notice'] ),
    'failed' => $failed,
);
echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
