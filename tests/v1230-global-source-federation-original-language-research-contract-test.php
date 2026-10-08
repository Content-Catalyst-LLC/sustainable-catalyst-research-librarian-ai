<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$wp=file_get_contents($root.'/includes/class-sc-rl-v1230-global-source-federation-original-language.php');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$backend_api=file_get_contents($root.'/backend/app/api/global_source_federation.py');
$backend_service=file_get_contents($root.'/backend/app/services/global_source_federation_original_language.py');
$backend_contract=file_get_contents($root.'/backend/app/contracts/global_source_federation_original_language.py');
$migration=file_get_contents($root.'/backend/migrations/043_global_source_federation_original_language_research.sql');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.4.0')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.4.0';")!==false,
 'module_loaded'=>strpos($main,'class-sc-rl-v1230-global-source-federation-original-language.php')!==false,
 'module_initialized'=>strpos($main,'SC_RL_V1230_Global_Source_Federation_Original_Language::init();')!==false,
 'wp_route'=>strpos($wp,"'/global-source-federation'")!==false,
 'wp_quality_trust_separation'=>strpos($wp,"'source_quality_trust_separation'")!==false,
 'wp_no_entity_resolution'=>strpos($wp,"'automatic_entity_resolution'")!==false,
 'wp_no_remote'=>strpos($wp,'wp_remote_')===false,
 'wp_no_state_write'=>strpos($wp,'update_option(')===false && strpos($wp,'update_user_meta(')===false,
 'backend_router'=>strpos($backend_main,'global_source_federation_router')!==false,
 'backend_health'=>strpos($backend_main,'"global_source_federation": True')!==false,
 'api_prefix'=>strpos($backend_api,'prefix="/v1/research-librarian/global-source-federation"')!==false,
 'api_auth'=>strpos($backend_api,'require_independent_access')!==false,
 'service_original_language'=>strpos($backend_service,'"original_language_is_primary_representation": True')!==false,
 'service_quality_trust'=>strpos($backend_service,'"source_quality_separate_from_user_trust": True')!==false,
 'service_no_entity_resolution'=>strpos($backend_service,'"automatic_entity_resolution": False')!==false,
 'service_no_toponym_resolution'=>strpos($backend_service,'"automatic_toponym_resolution": False')!==false,
 'service_lineage'=>strpos($backend_service,'def lineage(')!==false,
 'service_multilingual_candidate'=>strpos($backend_service,'def multilingual_candidate(')!==false,
 'service_core_candidate'=>strpos($backend_service,'def core_candidate(')!==false,
 'service_snapshot'=>strpos($backend_service,'def freeze_snapshot(')!==false,
 'contract_source'=>strpos($backend_contract,'class FederatedSourceAddRequest')!==false,
 'contract_acquisition'=>strpos($backend_contract,'class OriginalLanguageAcquisitionAddRequest')!==false,
 'contract_ingestion'=>strpos($backend_contract,'class SourceIngestionReceiptAddRequest')!==false,
 'contract_trust'=>strpos($backend_contract,'class SourceTrustPreferenceAddRequest')!==false,
 'migration_projects'=>strpos($migration,'sc_rl_global_source_federation_projects')!==false,
 'migration_events'=>strpos($migration,'sc_rl_global_source_federation_events')!==false,
 'migration_snapshots'=>strpos($migration,'sc_rl_global_source_federation_snapshots')!==false,
];
foreach($checks as $label=>$ok){
    if(!$ok){ fwrite(STDERR,"FAIL: $label\n"); exit(1); }
}
echo "PASS: Research Librarian v12.3.0 Global Source Federation & Original-Language Research contract.\n";
