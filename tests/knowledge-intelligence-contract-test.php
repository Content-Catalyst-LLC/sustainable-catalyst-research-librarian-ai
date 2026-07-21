<?php
/** Static contract checks for Research Librarian AI v6.5.1. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$retrieval = file_get_contents( $root . '/backend/app/retrieval.py' );
$render = file_get_contents( $root . '/render.yaml' );
$checks = array(
    'version' => false !== strpos( $main, "const VERSION        = '7.0.1';" ),
    'python_bridge_loaded' => false !== strpos( $main, 'class-sc-rl-v630-durable-index.php' ),
    'backend_first_ask_path' => false !== strpos( $main, 'SC_RL6_V621_Endpoint_Reliability::ask' ),
    'full_public_post_types' => false !== strpos( $module, "get_post_types( array( 'public' => true )" ),
    'batch_sync' => false !== strpos( $module, 'array_chunk( $records, $batch_size )' ),
    'secure_server_header' => false !== strpos( $module, "'X-SC-RL-Key'" ),
    'title_suggestions' => false !== strpos( $js, 'Indexed Sustainable Catalyst titles' ),
    'production_answer_ui' => false !== strpos( $js, 'sc-rl-production-answer' ) && false !== strpos( $css, 'v6.5.0 — Hybrid Retrieval, Durable Index, and Production UX' ),
    'fastapi' => false !== strpos( $backend, 'FastAPI(' ),
    'ask_endpoint' => false !== strpos( $backend, '@app.post("/v1/ask"' ),
    'sync_endpoint' => false !== strpos( $backend, '@app.post("/v1/knowledge/sync"' ),
    'exact_title_priority' => false !== strpos( $retrieval, 'breakdown["exact_title"] = 1000.0' ),
    'render_blueprint' => false !== strpos( $render, 'rootDir: backend' ) && false !== strpos( $render, 'uvicorn app.main:app' ),
);
$failed = array_keys( array_filter( $checks, static function( $value ) { return ! $value; } ) );
echo json_encode( array( 'version' => '7.0.1', 'checks' => $checks, 'failed' => $failed ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( empty( $failed ) ? 0 : 1 );
