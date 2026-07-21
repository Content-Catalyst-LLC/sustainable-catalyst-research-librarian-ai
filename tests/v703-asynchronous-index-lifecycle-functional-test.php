<?php
error_reporting( E_ALL );
ini_set( 'display_errors', '1' );
define( 'ABSPATH', sys_get_temp_dir() . '/sc-rl-v703-lifecycle/' );
define( 'HOUR_IN_SECONDS', 3600 );
define( 'MINUTE_IN_SECONDS', 60 );
$GLOBALS['sc_rl_options'] = array(
    'sc_rl_v620_python_options' => array(
        'enabled' => '1',
        'backend_url' => 'https://example.test',
        'backend_api_key' => 'test-key',
        'source_batch_size' => 20,
        'build_stale_minutes' => 20,
    ),
);
$GLOBALS['sc_rl_scheduled'] = array();
class WP_Error {
    private $code; private $message; private $data;
    public function __construct( $code = '', $message = '', $data = array() ) { $this->code=$code; $this->message=$message; $this->data=$data; }
    public function get_error_code(){ return $this->code; }
    public function get_error_message(){ return $this->message; }
    public function get_error_data(){ return $this->data; }
}
function is_wp_error( $value ) { return $value instanceof WP_Error; }
function get_option( $name, $default = false ) { return array_key_exists( $name, $GLOBALS['sc_rl_options'] ) ? $GLOBALS['sc_rl_options'][ $name ] : $default; }
function update_option( $name, $value, $autoload = null ) { $GLOBALS['sc_rl_options'][ $name ] = $value; return true; }
function delete_option( $name ) { unset( $GLOBALS['sc_rl_options'][ $name ] ); return true; }
function wp_parse_args( $args, $defaults = array() ) { return array_merge( $defaults, is_array( $args ) ? $args : array() ); }
function sanitize_text_field( $value ) { return trim( (string) $value ); }
function sanitize_key( $value ) { return strtolower( preg_replace( '/[^a-z0-9_\-]/', '', (string) $value ) ); }
function sanitize_file_name( $value ) { return preg_replace( '/[^A-Za-z0-9._-]/', '-', (string) $value ); }
function absint( $value ) { return abs( (int) $value ); }
function wp_generate_password( $length = 12, $special = true, $extra = false ) { return substr( str_repeat( 'a1b2c3d4', 4 ), 0, $length ); }
function wp_upload_dir() { $base = ABSPATH . 'uploads'; @mkdir( $base, 0777, true ); return array( 'basedir' => $base, 'error' => false ); }
function wp_mkdir_p( $path ) { return is_dir( $path ) || @mkdir( $path, 0777, true ); }
function trailingslashit( $value ) { return rtrim( $value, '/\\' ) . '/'; }
function wp_next_scheduled( $hook, $args = array() ) { $key = $hook . '|' . json_encode( $args ); return $GLOBALS['sc_rl_scheduled'][ $key ] ?? false; }
function wp_schedule_single_event( $timestamp, $hook, $args = array() ) { $GLOBALS['sc_rl_scheduled'][ $hook . '|' . json_encode( $args ) ] = $timestamp; return true; }
function wp_clear_scheduled_hook( $hook, $args = array() ) {
    if ( $args ) { unset( $GLOBALS['sc_rl_scheduled'][ $hook . '|' . json_encode( $args ) ] ); return; }
    foreach ( array_keys( $GLOBALS['sc_rl_scheduled'] ) as $key ) { if ( 0 === strpos( $key, $hook . '|' ) ) unset( $GLOBALS['sc_rl_scheduled'][ $key ] ); }
}
function add_action() {}
function add_filter() {}
function home_url( $path = '/' ) { return 'https://example.test' . $path; }

require dirname( __DIR__ ) . '/includes/class-sc-rl-v630-durable-index.php';
$failed = array();
$started = SC_RL6_V630_Durable_Index::start_index_build( 'functional-test' );
if ( is_wp_error( $started ) ) { $failed[] = 'start: ' . $started->get_error_message(); }
if ( 'queued' !== ( $started['state'] ?? '' ) ) { $failed[] = 'start state'; }
if ( 'testing-backend' !== ( $started['stage'] ?? '' ) ) { $failed[] = 'start stage'; }
if ( empty( $started['build_filename'] ) || ! str_ends_with( $started['build_filename'], '.jsonl' ) ) { $failed[] = 'private jsonl'; }
if ( empty( $GLOBALS['sc_rl_scheduled'] ) ) { $failed[] = 'background event'; }
$paused = SC_RL6_V630_Durable_Index::pause_index_build();
if ( is_wp_error( $paused ) || 'paused' !== ( $paused['state'] ?? '' ) ) { $failed[] = 'pause'; }
$resumed = SC_RL6_V630_Durable_Index::resume_index_build();
if ( is_wp_error( $resumed ) || 'queued' !== ( $resumed['state'] ?? '' ) ) { $failed[] = 'resume'; }
$cancelled = SC_RL6_V630_Durable_Index::cancel_index_build();
if ( is_wp_error( $cancelled ) || 'cancelled' !== ( $cancelled['state'] ?? '' ) ) { $failed[] = 'cancel'; }
$directory = trailingslashit( wp_upload_dir()['basedir'] ) . 'sc-research-librarian-private/index-builds/';
if ( is_file( $directory . ( $started['build_filename'] ?? '' ) ) ) { $failed[] = 'cancel cleanup'; }
echo json_encode( array( 'version' => SC_RL6_V630_Durable_Index::VERSION, 'started' => $started['state'] ?? '', 'paused' => $paused['state'] ?? '', 'resumed' => $resumed['state'] ?? '', 'cancelled' => $cancelled['state'] ?? '', 'failed' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
