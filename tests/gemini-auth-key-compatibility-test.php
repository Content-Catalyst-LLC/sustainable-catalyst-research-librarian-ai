<?php
/**
 * Static regression checks for Research Librarian AI v6.2.1 Gemini auth-key support.
 */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$admin = file_get_contents( $root . '/includes/class-sc-rl-v610-live-ai-admin.php' );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 6.2.1' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '6.2.1';" ),
    'modern_key_regex' => false !== strpos( $main, 'preg_match( \'/^[A-Za-z0-9._~\\-]+$/\', $raw )' ),
    'authorization_key_guidance' => false !== strpos( $admin, 'Gemini authorization key detected.' ),
    'standard_key_guidance' => false !== strpos( $admin, 'Google rejects unrestricted standard keys after June 19, 2026' ),
    'http_403_guidance' => false !== strpos( $main, 'Gemini denied this standard API key.' ),
    'http_429_guidance' => false !== strpos( $main, 'Gemini quota or rate limits were exhausted' ),
    'model_guidance' => false !== strpos( $main, 'Use List Available Gemini Models' ),
);
$failed = array_keys( array_filter( $checks, static function ( $passed ) { return ! $passed; } ) );
$result = array( 'version' => '6.2.1', 'checks' => $checks, 'failed' => $failed );
echo wp_json_encode_exists_for_cli( $result );
exit( empty( $failed ) ? 0 : 1 );

function wp_json_encode_exists_for_cli( $value ) {
    return json_encode( $value, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
}
