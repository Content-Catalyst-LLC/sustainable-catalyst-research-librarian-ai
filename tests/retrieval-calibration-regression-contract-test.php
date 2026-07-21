<?php
/** Static release contract checks for Research Librarian AI v6.5.1. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$calibration = file_get_contents( $root . '/backend/app/calibration.py' );
$retrieval = file_get_contents( $root . '/backend/app/retrieval.py' );
$provider = file_get_contents( $root . '/backend/app/provider.py' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$docs = file_get_contents( $root . '/docs/V641_RETRIEVAL_CALIBRATION_REGRESSION.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_retrieval_calibration_manifest_v6.5.0.json' ), true );
$benchmarks = json_decode( file_get_contents( $root . '/data/research_librarian_retrieval_benchmarks_v6.5.0.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 7.0.2' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '7.0.2';" ),
    'module_version' => false !== strpos( $module, "const VERSION = '7.0.2';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "7.0.2"' ),
    'schema_version_six' => false !== strpos( $store, 'SCHEMA_VERSION = 10' ),
    'index_schema_six' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/10.0' ),
    'calibration_module' => false !== strpos( $calibration, 'DEFAULT_RETRIEVAL_CONFIG' ),
    'balanced_profile' => false !== strpos( $calibration, 'balanced-v6.5.0' ),
    'structural_weight' => false !== strpos( $calibration, '"structural": 1.0' ),
    'lexical_weight' => false !== strpos( $calibration, '"lexical": 24.0' ),
    'semantic_weight' => false !== strpos( $calibration, '"semantic": 160.0' ),
    'rrf_weight' => false !== strpos( $calibration, '"rrf": 1400.0' ),
    'bounded_rrf_k' => false !== strpos( $calibration, '"rrf_k"' ) && false !== strpos( $calibration, '1, 500' ),
    'minimum_score' => false !== strpos( $calibration, '"minimum_score"' ),
    'minimum_sources' => false !== strpos( $calibration, '"minimum_sources"' ),
    'lexical_floor' => false !== strpos( $calibration, '"minimum_best_lexical"' ),
    'semantic_floor' => false !== strpos( $calibration, '"minimum_best_semantic"' ),
    'ambiguity_margin' => false !== strpos( $calibration, '"ambiguity_margin"' ),
    'near_duplicate_similarity' => false !== strpos( $calibration, '"near_duplicate_title_similarity"' ),
    'unsupported_overlap' => false !== strpos( $calibration, '"unsupported_overlap"' ),
    'citation_coverage_threshold' => false !== strpos( $calibration, '"minimum_citation_coverage"' ),
    'context_budget' => false !== strpos( $calibration, '"max_context_characters"' ),
    'passage_budget' => false !== strpos( $calibration, '"max_passage_characters"' ),
    'post_type_weights' => false !== strpos( $calibration, '"post_type_weights"' ),
    'source_weights' => false !== strpos( $calibration, '"source_weights"' ),
    'record_exclusions' => false !== strpos( $calibration, '"record_ids"' ),
    'post_type_exclusions' => false !== strpos( $calibration, '"post_types"' ),
    'source_exclusions' => false !== strpos( $calibration, '"sources"' ),
    'url_prefix_exclusions' => false !== strpos( $calibration, '"url_prefixes"' ),
    'evidence_gate' => false !== strpos( $calibration, 'def evidence_gate' ),
    'calibration_update_model' => false !== strpos( $models, 'class RetrievalCalibrationUpdate(BaseModel)' ),
    'benchmark_case_model' => false !== strpos( $models, 'class BenchmarkCase(BaseModel)' ),
    'benchmark_request_model' => false !== strpos( $models, 'class BenchmarkRequest(BaseModel)' ),
    'answer_gate_payload' => false !== strpos( $models, 'evidence_gate: dict[str, Any]' ),
    'status_profile_payload' => false !== strpos( $models, 'retrieval_profile: str' ),
    'status_benchmark_payload' => false !== strpos( $models, 'benchmark_runs: int' ),
    'calibration_aware_retrieval' => false !== strpos( $retrieval, 'calibration: dict[str, Any] | None = None' ),
    'title_specificity' => false !== strpos( $retrieval, 'title_specificity' ),
    'exclusion_diagnostics' => false !== strpos( $retrieval, 'records_excluded' ) && false !== strpos( $retrieval, 'exclusion_reasons' ),
    'calibration_active_diagnostic' => false !== strpos( $retrieval, '"calibration_active": True' ),
    'profile_diagnostic' => false !== strpos( $retrieval, '"retrieval_profile"' ),
    'near_duplicate_detection' => false !== strpos( $retrieval, 'ambiguity_candidates' ),
    'ranking_latency' => false !== strpos( $retrieval, 'ranking_latency_ms' ),
    'retrieval_latency' => false !== strpos( $retrieval, 'retrieval_latency_ms' ),
    'context_budget_applied' => false !== strpos( $provider, 'max_context_characters' ) && false !== strpos( $provider, 'max_passage_characters' ),
    'verification_stopwords' => false !== strpos( $provider, '_VERIFICATION_STOPWORDS' ),
    'paragraph_overlap_verification' => false !== strpos( $provider, 'low-evidence-overlap' ),
    'numeric_claim_verification' => false !== strpos( $provider, 'unsupported_numeric_claims' ),
    'citation_coverage_verification' => false !== strpos( $provider, 'citation_coverage' ),
    'config_table_persistence' => false !== strpos( $store, 'retrieval_config' ),
    'benchmark_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS retrieval_benchmark_runs' ),
    'benchmark_retention' => false !== strpos( $store, 'ORDER BY created_utc DESC LIMIT 25' ),
    'config_setter' => false !== strpos( $store, 'def set_retrieval_config' ),
    'benchmark_save' => false !== strpos( $store, 'def save_benchmark_run' ),
    'benchmark_history' => false !== strpos( $store, 'def benchmark_history' ),
    'config_get_endpoint' => false !== strpos( $backend, '@app.get("/v1/retrieval/config"' ),
    'config_post_endpoint' => false !== strpos( $backend, '@app.post("/v1/retrieval/config"' ),
    'benchmark_endpoint' => false !== strpos( $backend, '@app.post("/v1/retrieval/benchmark"' ),
    'benchmark_history_endpoint' => false !== strpos( $backend, '@app.get("/v1/retrieval/benchmark/history"' ),
    'lexical_hybrid_metrics' => false !== strpos( $backend, '"lexical"' ) && false !== strpos( $backend, '"hybrid"' ) && false !== strpos( $backend, 'hit_at_1' ) && false !== strpos( $backend, 'mrr' ),
    'evidence_gate_before_generation' => false !== strpos( $backend, 'gate = evidence_gate' ) && false !== strpos( $backend, 'if not gate.get("ok")' ),
    'ambiguity_clarification' => false !== strpos( $backend, 'similarly titled Sustainable Catalyst records' ),
    'wordpress_config_payload' => false !== strpos( $module, 'public static function retrieval_config_payload' ),
    'wordpress_config_apply' => false !== strpos( $module, 'public static function apply_retrieval_config' ),
    'wordpress_weight_parser' => false !== strpos( $module, 'private static function parse_weight_map' ),
    'wordpress_list_parser' => false !== strpos( $module, 'private static function parse_list' ),
    'wordpress_calibration_heading' => false !== strpos( $module, 'Knowledge Index and AI Readiness' ) && false !== strpos( $module, 'Retrieval Calibration' ),
    'wordpress_evidence_controls' => false !== strpos( $module, 'Fusion and evidence gates' ),
    'wordpress_verification_controls' => false !== strpos( $module, 'Answer verification' ),
    'wordpress_post_type_controls' => false !== strpos( $module, 'Post-type weights' ),
    'wordpress_exclusion_controls' => false !== strpos( $module, 'Excluded URL prefixes' ),
    'wordpress_benchmark_action' => false !== strpos( $module, 'Run Retrieval Benchmark' ),
    'wordpress_benchmark_history' => false !== strpos( $module, 'Benchmark history' ),
    'release_documentation' => false !== strpos( $docs, 'Minimum-evidence gate' ) && false !== strpos( $docs, 'Unsupported-answer detection' ),
    'release_manifest' => is_array( $manifest ) && '6.5.0' === ( $manifest['version'] ?? '' ) && 6 === ( $manifest['backend_schema_version'] ?? 0 ),
    'free_tier_compatibility' => is_array( $manifest ) && false === ( $manifest['compatibility']['paid_vector_database_required'] ?? true ),
    'benchmark_manifest' => is_array( $benchmarks ) && '6.5.0' === ( $benchmarks['version'] ?? '' ) && count( $benchmarks['cases'] ?? array() ) >= 8,
    'benchmark_exact_title_case' => is_array( $benchmarks ) && false !== strpos( json_encode( $benchmarks ), 'exact-title' ),
    'benchmark_platform_route_case' => is_array( $benchmarks ) && false !== strpos( json_encode( $benchmarks ), 'platform-route' ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array(
    'version' => '7.0.2',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
