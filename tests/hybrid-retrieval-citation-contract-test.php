<?php
/** Static release contract checks for Research Librarian AI v6.5.0. */
$root = dirname( __DIR__ );
$main = file_get_contents( $root . '/sustainable-catalyst-research-librarian-ai.php' );
$module = file_get_contents( $root . '/includes/class-sc-rl-v630-durable-index.php' );
$js = file_get_contents( $root . '/assets/sc-research-librarian-ai.js' );
$css = file_get_contents( $root . '/assets/sc-research-librarian-ai.css' );
$config = file_get_contents( $root . '/backend/app/config.py' );
$models = file_get_contents( $root . '/backend/app/models.py' );
$chunking = file_get_contents( $root . '/backend/app/chunking.py' );
$retrieval = file_get_contents( $root . '/backend/app/retrieval.py' );
$provider = file_get_contents( $root . '/backend/app/provider.py' );
$backend = file_get_contents( $root . '/backend/app/main.py' );
$store = file_get_contents( $root . '/backend/app/store.py' );
$render = file_get_contents( $root . '/render.yaml' );
$docs = file_get_contents( $root . '/docs/V640_HYBRID_RETRIEVAL_CITATION_ENGINE.md' );
$manifest = json_decode( file_get_contents( $root . '/data/research_librarian_hybrid_retrieval_manifest_v6.4.0.json' ), true );

$checks = array(
    'version_header' => false !== strpos( $main, 'Version: 6.5.0' ),
    'version_constant' => false !== strpos( $main, "const VERSION        = '6.5.0';" ),
    'module_version' => false !== strpos( $module, "const VERSION = '6.5.0';" ),
    'backend_version' => false !== strpos( file_get_contents( $root . '/backend/app/__init__.py' ), '__version__ = "6.5.0"' ),
    'schema_version_six_or_newer' => false !== strpos( $store, 'SCHEMA_VERSION = 6' ),
    'index_schema_six_or_newer' => false !== strpos( $store, 'sc-research-librarian-knowledge-index/6.0' ),
    'knowledge_chunk_model' => false !== strpos( $models, 'class KnowledgeChunk(BaseModel)' ),
    'evidence_citation_model' => false !== strpos( $models, 'class EvidenceCitation(BaseModel)' ),
    'page_aware_models' => substr_count( $models, 'page: int | None = None' ) >= 2,
    'source_evidence_identifier' => false !== strpos( $models, 'evidence_id: str' ) && false !== strpos( $models, 'citation_label: str' ),
    'answer_evidence_payload' => false !== strpos( $models, 'evidence: list[EvidenceCitation]' ),
    'answer_citation_verification' => false !== strpos( $models, 'citation_verification: dict[str, Any]' ),
    'answer_retrieval_diagnostics' => false !== strpos( $models, 'retrieval_diagnostics: dict[str, Any]' ),
    'section_aware_chunker' => false !== strpos( $chunking, 'def chunk_record' ) && false !== strpos( $chunking, 'record.metadata.get("sections"' ),
    'deterministic_chunk_ids' => false !== strpos( $chunking, 'def _chunk_id' ) && false !== strpos( $chunking, 'def _content_hash' ),
    'page_aware_chunks' => false !== strpos( $chunking, 'PDF/library records may provide a page number per section' ),
    'bounded_chunking' => false !== strpos( $chunking, 'max_words: int = 220' ) && false !== strpos( $chunking, 'overlap_words: int = 35' ),
    'retrieval_chunks_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS retrieval_chunks' ),
    'embedding_runs_table' => false !== strpos( $store, 'CREATE TABLE IF NOT EXISTS embedding_runs' ),
    'chunk_rebuild_on_index_change' => false !== strpos( $store, 'def _rebuild_all_chunks' ) && substr_count( $store, '_rebuild_all_chunks(' ) >= 3,
    'unchanged_embedding_retention' => false !== strpos( $store, 'existing_embeddings' ) && false !== strpos( $store, 'content_hash' ),
    'embedding_queue' => false !== strpos( $store, 'def pending_chunks' ) && false !== strpos( $store, 'def save_chunk_embedding' ),
    'embedding_run_ledger' => false !== strpos( $store, 'def begin_embedding_run' ) && false !== strpos( $store, 'def finish_embedding_run' ),
    'semantic_coverage_status' => false !== strpos( $store, 'semantic_coverage' ) && false !== strpos( $models, 'semantic_coverage: float' ),
    'intent_classification' => false !== strpos( $retrieval, 'def classify_intent' ) && false !== strpos( $retrieval, 'exact-title-lookup' ),
    'exact_title_priority' => false !== strpos( $retrieval, 'breakdown["exact_title"] = 1000.0' ),
    'bm25_retrieval' => false !== strpos( $retrieval, 'def _bm25_scores' ) && false !== strpos( $retrieval, 'bm25-section-match' ),
    'semantic_similarity' => false !== strpos( $retrieval, 'def _cosine' ),
    'reciprocal_rank_fusion' => false !== strpos( $retrieval, 'reciprocal_rank_fusion' ) && false !== strpos( $retrieval, 'exact-title+bm25+semantic+rrf' ),
    'retrieval_explanation' => false !== strpos( $retrieval, 'retrieval_reasons' ) && false !== strpos( $retrieval, 'score_breakdown' ),
    'evidence_assembly' => false !== strpos( $retrieval, 'def evidence_from_matches' ),
    'gemini_embedding_function' => false !== strpos( $provider, 'def generate_embedding' ) && false !== strpos( $provider, ':embedContent' ),
    'citation_prompt_contract' => false !== strpos( $provider, 'supplied citation tokens such as [SC1]' ),
    'citation_verifier' => false !== strpos( $provider, 'def verify_citations' ),
    'invalid_citation_rejection' => false !== strpos( $provider, 'invalid_citations' ),
    'unknown_url_rejection' => false !== strpos( $provider, 'unknown_urls' ),
    'required_citation_enforcement' => false !== strpos( $provider, 'missing_required_citations' ),
    'embedding_status_endpoint' => false !== strpos( $backend, '@app.get("/v1/knowledge/embeddings/status"' ),
    'embedding_process_endpoint' => false !== strpos( $backend, '@app.post("/v1/knowledge/embeddings/process"' ),
    'retrieve_endpoint' => false !== strpos( $backend, '@app.post("/v1/retrieve"' ),
    'retrieve_explain_endpoint' => false !== strpos( $backend, '@app.post("/v1/retrieve/explain"' ),
    'hybrid_ask_path' => false !== strpos( $backend, 'matches, retrieval_diagnostics = await _hybrid_retrieve' ),
    'unverified_ai_answer_blocked' => false !== strpos( $backend, 'if not citation_verification.get("ok")' ),
    'deterministic_evidence_fallback' => false !== strpos( $backend, 'def _deterministic_answer' ) && false !== strpos( $backend, 'citation_verification["fallback"] = True' ),
    'wordpress_section_extraction' => false !== strpos( $module, 'private static function extract_content_sections' ),
    'wordpress_section_metadata' => false !== strpos( $module, "'sections' => '1' === (string) \$options['include_content'] ? self::extract_content_sections( \$raw_content, \$limit ) : array()" ),
    'wordpress_section_budget' => false !== strpos( $module, '$remaining = max( 0, min( 60000, absint( $character_limit ) ) )' ),
    'wordpress_evidence_normalization' => false !== strpos( $module, 'sanitize_evidence_record' ) && false !== strpos( $module, "'citation_verification'" ),
    'embedding_admin_action' => false !== strpos( $module, 'Process Embedding Batch' ) && false !== strpos( $module, '/v1/knowledge/embeddings/process' ),
    'embedding_admin_status' => false !== strpos( $module, 'Semantic coverage' ) && false !== strpos( $module, '/v1/knowledge/embeddings/status' ),
    'public_evidence_location' => false !== strpos( $js, 'source.section' ) && false !== strpos( $js, 'source.page' ) && false !== strpos( $js, 'source.passage' ),
    'public_citation_verification' => false !== strpos( $js, 'citationVerification' ) && false !== strpos( $js, 'retrievalDiagnostics' ),
    'evidence_card_styles' => false !== strpos( $css, 'section-aware evidence and citation locations' ),
    'semantic_enabled_in_render' => false !== strpos( $render, 'SC_RL_SEMANTIC_ENABLED' ) && false !== strpos( $render, 'value: "true"' ),
    'embedding_model_in_render' => false !== strpos( $render, 'SC_RL_GEMINI_EMBEDDING_MODEL' ) && false !== strpos( $render, 'gemini-embedding-001' ),
    'semantic_query_embedding_setting' => false !== strpos( $config, 'SC_RL_SEMANTIC_QUERY_EMBEDDINGS' ),
    'bounded_embedding_setting' => false !== strpos( $config, 'SC_RL_EMBEDDING_BATCH_LIMIT' ),
    'citation_required_setting' => false !== strpos( $config, 'SC_RL_CITATION_REQUIRED' ),
    'release_documentation' => false !== strpos( $docs, 'Citation-verified synthesis' ) && false !== strpos( $docs, 'Deterministic fallback' ),
    'release_manifest' => is_array( $manifest ) && '6.4.0' === ( $manifest['version'] ?? '' ) && 5 === ( $manifest['backend_schema_version'] ?? 0 ),
    'free_tier_compatibility' => is_array( $manifest ) && false === ( $manifest['compatibility']['paid_vector_database_required'] ?? true ),
    'lexical_fallback_contract' => is_array( $manifest ) && true === ( $manifest['compatibility']['lexical_fallback_available'] ?? false ),
);
$failed = array_keys( array_filter( $checks, static function ( $value ) { return ! $value; } ) );
echo json_encode( array(
    'version' => '6.5.0',
    'checks' => $checks,
    'passed' => count( $checks ) - count( $failed ),
    'failed' => count( $failed ),
    'failures' => $failed,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) . PHP_EOL;
exit( $failed ? 1 : 0 );
