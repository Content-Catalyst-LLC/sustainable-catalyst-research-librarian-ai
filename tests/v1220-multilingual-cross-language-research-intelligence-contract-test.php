<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$wp=file_get_contents($root.'/includes/class-sc-rl-v1220-multilingual-cross-language-research.php');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$backend_api=file_get_contents($root.'/backend/app/api/multilingual_research.py');
$backend_service=file_get_contents($root.'/backend/app/services/multilingual_cross_language_research.py');
$backend_contract=file_get_contents($root.'/backend/app/contracts/multilingual_cross_language_research.py');
$migration=file_get_contents($root.'/backend/migrations/042_multilingual_cross_language_research_intelligence.sql');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.3.0')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.3.0';")!==false,
 'module_loaded'=>strpos($main,'class-sc-rl-v1220-multilingual-cross-language-research.php')!==false,
 'module_initialized'=>strpos($main,'SC_RL_V1220_Multilingual_Cross_Language_Research::init();')!==false,
 'wp_route'=>strpos($wp,"'/multilingual-research'")!==false,
 'wp_original_first'=>strpos($wp,"'analyze_original_language_first'")!==false,
 'wp_translation_derived'=>strpos($wp,"'translation_is_derived'")!==false,
 'wp_federation_deferred'=>strpos($wp,"'global_source_federation'            => false")!==false,
 'wp_entity_resolution_deferred'=>strpos($wp,"'automatic_entity_resolution'         => false")!==false,
 'wp_no_remote'=>strpos($wp,'wp_remote_')===false,
 'wp_no_state_write'=>strpos($wp,'update_option(')===false && strpos($wp,'update_user_meta(')===false,
 'backend_router'=>strpos($backend_main,'multilingual_research_router')!==false,
 'backend_health'=>strpos($backend_main,'"multilingual_cross_language_research": True')!==false,
 'api_prefix'=>strpos($backend_api,'prefix="/v1/research-librarian/multilingual-research"')!==false,
 'api_auth'=>strpos($backend_api,'require_independent_access')!==false,
 'service_original_first'=>strpos($backend_service,'"analyze_original_language_first": True')!==false,
 'service_translation_derived'=>strpos($backend_service,'"translation_is_derived_representation": True')!==false,
 'service_no_entity_resolution'=>strpos($backend_service,'"automatic_entity_resolution": False')!==false,
 'service_lineage'=>strpos($backend_service,'def lineage(')!==false,
 'service_core_candidate'=>strpos($backend_service,'def core_candidate(')!==false,
 'service_snapshot'=>strpos($backend_service,'def freeze_snapshot(')!==false,
 'contract_language_profile'=>strpos($backend_contract,'class LanguageProfileAddRequest')!==false,
 'contract_derived_representation'=>strpos($backend_contract,'class DerivedLanguageRepresentationAddRequest')!==false,
 'contract_alignment'=>strpos($backend_contract,'class TextAlignmentAddRequest')!==false,
 'contract_query_plan'=>strpos($backend_contract,'class CrossLanguageQueryPlanAddRequest')!==false,
 'migration_projects'=>strpos($migration,'sc_rl_multilingual_research_projects')!==false,
 'migration_events'=>strpos($migration,'sc_rl_multilingual_research_events')!==false,
 'migration_snapshots'=>strpos($migration,'sc_rl_multilingual_research_snapshots')!==false,
];
foreach($checks as $label=>$ok){
    if(!$ok){
        fwrite(STDERR,"FAIL: $label\n");
        exit(1);
    }
}
echo "PASS: Research Librarian v12.2.0 Multilingual & Cross-Language Research Intelligence contract.\n";
