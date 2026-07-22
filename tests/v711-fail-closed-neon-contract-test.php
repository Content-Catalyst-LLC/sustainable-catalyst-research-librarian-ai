<?php
/** Static release contract for v7.1.1 fail-closed Neon activation. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$backend = file_get_contents( $root . '/backend/app/postgres_store.py' );
$config = file_get_contents( $root . '/backend/app/config.py' );
$factory = file_get_contents( $root . '/backend/app/store.py' );
$api = file_get_contents( $root . '/backend/app/main.py' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_fail_closed_neon_manifest_v7.1.1.json' ), true );
$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.1.1' ),
    'durable_version' => false !== strpos( $module, "const VERSION = '7.1.1';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.1.1"' ),
    'fail_closed_setting' => false !== strpos( $config, 'SC_RL_DATABASE_FAIL_CLOSED' ),
    'schema_setting' => false !== strpos( $config, 'SC_RL_DATABASE_SCHEMA' ),
    'no_silent_sqlite' => false !== strpos( $factory, 'Neon connection variables are configured but the selected database backend is SQLite' ),
    'identity_endpoint' => false !== strpos( $api, '/v1/knowledge/database/identity' ),
    'identity_verification' => false !== strpos( $backend, 'compare_live_identities' ) && false !== strpos( $backend, 'database_fingerprint' ),
    'committed_empty' => false !== strpos( $backend, 'committed-empty' ) && false !== strpos( $module, 'neon-committed-empty-or-identity-mismatch' ),
    'active_verification' => false !== strpos( $backend, 'verifying-active-generation' ),
    'admin_identity' => false !== strpos( $module, 'Neon database identity' ) && false !== strpos( $module, 'Fail closed' ),
    'manifest' => is_array( $manifest ) && '7.1.1' === ( $manifest['version'] ?? '' ) && true === ( $manifest['database']['fail_closed'] ?? false ),
);
$failed = array_keys( array_filter( $checks, static function ( $passed ) { return ! $passed; } ) );
echo json_encode( array( 'version' => '7.1.1', 'checks' => $checks, 'passed' => count( $checks ) - count( $failed ), 'failed' => count( $failed ), 'failures' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
