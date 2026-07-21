<?php
error_reporting( E_ALL );
ini_set( 'display_errors', '1' );
define( 'ABSPATH', sys_get_temp_dir() . '/sc-rl-v702-source-discovery/' );
define( 'HOUR_IN_SECONDS', 3600 );
define( 'MINUTE_IN_SECONDS', 60 );

function sanitize_key( $value ) { return strtolower( preg_replace( '/[^a-z0-9_\-]/', '', (string) $value ) ); }
function apply_filters( $tag, $value ) { return $value; }
function absint( $value ) { return abs( (int) $value ); }
function gmdate_stub() { return ''; }
function get_post_types( $args = array(), $output = 'names' ) {
    $objects = array(
        'post' => (object) array( 'public' => true, 'publicly_queryable' => true, 'show_in_rest' => true, 'rewrite' => array( 'slug' => 'post' ) ),
        'page' => (object) array( 'public' => true, 'publicly_queryable' => true, 'show_in_rest' => true, 'rewrite' => array( 'slug' => 'page' ) ),
        'knowledge_document' => (object) array( 'public' => false, 'publicly_queryable' => true, 'show_in_rest' => true, 'rewrite' => array( 'slug' => 'library' ) ),
        'support_article' => (object) array( 'public' => false, 'publicly_queryable' => false, 'show_in_rest' => true, 'rewrite' => array( 'slug' => 'support' ) ),
        'private_note' => (object) array( 'public' => false, 'publicly_queryable' => false, 'show_in_rest' => false, 'rewrite' => false ),
        'attachment' => (object) array( 'public' => true, 'publicly_queryable' => true, 'show_in_rest' => true, 'rewrite' => array() ),
    );
    return 'objects' === $output ? $objects : array_keys( $objects );
}
function wp_count_posts( $type ) {
    $counts = array( 'post' => 4, 'page' => 8, 'knowledge_document' => 312, 'support_article' => 45, 'private_note' => 99, 'attachment' => 500 );
    return (object) array( 'publish' => $counts[ $type ] ?? 0 );
}

require dirname( __DIR__ ) . '/includes/class-sc-rl-v630-durable-index.php';
$result = SC_RL6_V630_Durable_Index::source_discovery_summary();
$types = $result['post_types'] ?? array();
$failed = array();
foreach ( array( 'post', 'page', 'knowledge_document', 'support_article' ) as $expected ) {
    if ( ! in_array( $expected, $types, true ) ) { $failed[] = 'Missing ' . $expected; }
}
foreach ( array( 'private_note', 'attachment' ) as $excluded ) {
    if ( in_array( $excluded, $types, true ) ) { $failed[] = 'Unexpected ' . $excluded; }
}
if ( 369 !== ( $result['published_records'] ?? 0 ) ) { $failed[] = 'Published count mismatch'; }
echo json_encode( array( 'version' => SC_RL6_V630_Durable_Index::VERSION, 'post_types' => $types, 'published_records' => $result['published_records'] ?? 0, 'failed' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
