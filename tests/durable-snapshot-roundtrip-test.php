<?php
/** Functional round-trip test for v6.3.0 private WordPress snapshots. */
error_reporting( E_ALL );
ini_set( 'display_errors', '1' );

define( 'ABSPATH', sys_get_temp_dir() . '/sc-rl-v630-snapshot-wp/' );
define( 'HOUR_IN_SECONDS', 3600 );
define( 'MINUTE_IN_SECONDS', 60 );

class WP_Error {
    private $code; private $message; private $data;
    public function __construct( $code = '', $message = '', $data = null ) { $this->code=$code; $this->message=$message; $this->data=$data; }
    public function get_error_code(){ return $this->code; }
    public function get_error_message(){ return $this->message; }
    public function get_error_data(){ return $this->data; }
}

$GLOBALS['sc_rl_snapshot_options'] = array();
$GLOBALS['sc_rl_snapshot_uploads'] = sys_get_temp_dir() . '/sc-rl-v630-snapshot-' . bin2hex( random_bytes( 4 ) );

function get_option( $name, $default = false ) { return array_key_exists( $name, $GLOBALS['sc_rl_snapshot_options'] ) ? $GLOBALS['sc_rl_snapshot_options'][ $name ] : $default; }
function update_option( $name, $value, $autoload = null ) { $GLOBALS['sc_rl_snapshot_options'][ $name ] = $value; return true; }
function wp_parse_args( $args, $defaults = array() ) { return array_merge( $defaults, is_array( $args ) ? $args : array() ); }
function wp_upload_dir() { return array( 'basedir' => $GLOBALS['sc_rl_snapshot_uploads'], 'error' => false ); }
function wp_mkdir_p( $path ) { return is_dir( $path ) || mkdir( $path, 0777, true ); }
function trailingslashit( $value ) { return rtrim( (string) $value, '/\\' ) . '/'; }
function home_url( $path = '' ) { return 'https://sustainablecatalyst.com' . $path; }
function sanitize_text_field( $value ) { return trim( strip_tags( (string) $value ) ); }
function sanitize_file_name( $value ) { return preg_replace( '/[^A-Za-z0-9._-]/', '-', (string) $value ); }
function wp_generate_password( $length = 12, $special_chars = true, $extra_special_chars = false ) { return substr( bin2hex( random_bytes( max( 4, (int) ceil( $length / 2 ) ) ) ), 0, $length ); }
function wp_json_encode( $value, $flags = 0, $depth = 512 ) { return json_encode( $value, $flags, $depth ); }
function absint( $value ) { return abs( (int) $value ); }
function is_wp_error( $value ) { return $value instanceof WP_Error; }

require dirname( __DIR__ ) . '/includes/class-sc-rl-v630-durable-index.php';

$records = array(
    array(
        'id' => 'wp:post:1',
        'title' => 'Durable Index Test',
        'url' => 'https://sustainablecatalyst.com/durable-index-test/',
        'summary' => 'A canonical snapshot test record.',
        'content' => 'Snapshot content.',
        'metadata' => array( 'post_id' => 1 ),
    ),
);
$manifest = SC_RL6_V630_Durable_Index::create_wordpress_snapshot( $records, 'contract-test' );
$failed = array();
if ( is_wp_error( $manifest ) ) {
    $failed[] = $manifest->get_error_message();
} else {
    $directory = trailingslashit( $GLOBALS['sc_rl_snapshot_uploads'] ) . 'sc-research-librarian-private/index-snapshots';
    $path = trailingslashit( $directory ) . $manifest['filename'];
    foreach ( array( $path, $directory . '/.htaccess', $directory . '/index.php', $directory . '/web.config' ) as $required ) {
        if ( ! is_file( $required ) ) { $failed[] = 'Missing ' . basename( $required ); }
    }
    if ( ! hash_equals( $manifest['file_sha256'], hash_file( 'sha256', $path ) ) ) { $failed[] = 'File checksum mismatch'; }

    $method = new ReflectionMethod( 'SC_RL6_V630_Durable_Index', 'read_wordpress_snapshot' );
    $method->setAccessible( true );
    $roundtrip = $method->invoke( null, $manifest );
    if ( is_wp_error( $roundtrip ) ) {
        $failed[] = $roundtrip->get_error_message();
    } elseif ( 'wp:post:1' !== ( $roundtrip['records'][0]['id'] ?? '' ) || empty( $roundtrip['records'][0]['content_hash'] ) ) {
        $failed[] = 'Round-trip record or content hash missing';
    }
}

$result = array(
    'version' => SC_RL6_V630_Durable_Index::VERSION,
    'snapshot_created' => ! is_wp_error( $manifest ),
    'record_count' => is_array( $manifest ) ? ( $manifest['record_count'] ?? 0 ) : 0,
    'compressed' => is_array( $manifest ) ? ( $manifest['compressed'] ?? false ) : false,
    'failed' => $failed,
);
echo json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;

function sc_rl_v630_remove_tree( $path ) {
    if ( ! is_dir( $path ) ) { return; }
    foreach ( array_diff( scandir( $path ), array( '.', '..' ) ) as $item ) {
        $full = $path . DIRECTORY_SEPARATOR . $item;
        is_dir( $full ) ? sc_rl_v630_remove_tree( $full ) : unlink( $full );
    }
    rmdir( $path );
}
sc_rl_v630_remove_tree( $GLOBALS['sc_rl_snapshot_uploads'] );
exit( $failed ? 1 : 0 );
