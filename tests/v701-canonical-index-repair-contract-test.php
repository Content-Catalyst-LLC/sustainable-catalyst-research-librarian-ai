<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$durable=file_get_contents($root.'/includes/class-sc-rl-v630-durable-index.php');
$backend=file_get_contents($root.'/backend/app/main.py');
$provider=file_get_contents($root.'/backend/app/provider.py');
$store=file_get_contents($root.'/backend/app/store.py');
$manifest=json_decode(file_get_contents($root.'/data/research_librarian_v701_repair_manifest.json'),true);
$checks=array(
 'version_header'=>false!==strpos($main,'Version: 7.0.4'),
 'version_constant'=>false!==strpos($main,"const VERSION        = '7.0.4';"),
 'all_public_post_types'=>false!==strpos($main,"get_post_types( array( 'public' => true ), 'names' )"),
 'legacy_page_post_ceiling_removed'=>false===strpos($main,"'post_type' => array( 'page', 'post' )"),
 'canonical_delegation'=>false!==strpos($main,'SC_RL6_V630_Durable_Index::sync_and_complete_embeddings'),
 'embedding_hook'=>false!==strpos($durable,"const EMBEDDING_HOOK = 'sc_rl_v701_embedding_queue_event';"),
 'one_click_repair'=>false!==strpos($durable,'build_index_pipeline'),
 'provider_error_stops_auth_retry'=>false!==strpos($durable,"'sc_rl_v701_embedding_provider_error'")&&false!==strpos($durable,"'configuration-error'"),
 'fallback_index_limit_expanded'=>false!==strpos($main,"'index_max_posts'         => 5000"),
 'credential_source'=>false!==strpos($durable,'SC_RL_GEMINI_API_KEY'),
 'provider_diagnostics_endpoint'=>false!==strpos($backend,'/v1/provider/diagnostics'),
 'embedding_test_endpoint'=>false!==strpos($backend,'/v1/knowledge/embeddings/test'),
 'safe_diagnostics'=>false!==strpos($provider,'def credential_diagnostics'),
 'current_model_coverage'=>false!==strpos($store,'embedding_model=?'),
 'manifest_version'=>is_array($manifest)&&'7.0.1'===($manifest['version']??''),
);
$failed=array_keys(array_filter($checks,function($ok){return !$ok;}));
echo json_encode(array('version'=>'7.0.4','checks'=>$checks,'passed'=>count($checks)-count($failed),'failed'=>count($failed),'failures'=>$failed),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES).PHP_EOL;
exit($failed?1:0);
