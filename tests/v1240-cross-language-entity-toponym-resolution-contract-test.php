<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$wp=file_get_contents($root.'/includes/class-sc-rl-v1240-cross-language-entity-toponym-resolution.php');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$backend_api=file_get_contents($root.'/backend/app/api/cross_language_entity_toponym_resolution.py');
$backend_service=file_get_contents($root.'/backend/app/services/cross_language_entity_toponym_resolution.py');
$backend_contract=file_get_contents($root.'/backend/app/contracts/cross_language_entity_toponym_resolution.py');
$migration=file_get_contents($root.'/backend/migrations/044_cross_language_entity_toponym_resolution.sql');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.4.0')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.4.0';")!==false,
 'module_loaded'=>strpos($main,'class-sc-rl-v1240-cross-language-entity-toponym-resolution.php')!==false,
 'module_initialized'=>strpos($main,'SC_RL_V1240_Cross_Language_Entity_Toponym_Resolution::init();')!==false,
 'wp_route'=>strpos($wp,"'/cross-language-entity-toponym-resolution'")!==false,
 'wp_entity_resolution'=>strpos($wp,"'cross_language_entity_resolution'")!==false,
 'wp_toponym_resolution'=>strpos($wp,"'cross_language_toponym_resolution'")!==false,
 'wp_no_identity_promotion'=>strpos($wp,"'automatic_identity_promotion'")!==false,
 'wp_no_remote'=>strpos($wp,'wp_remote_')===false,
 'wp_no_state_write'=>strpos($wp,'update_option(')===false && strpos($wp,'update_user_meta(')===false,
 'backend_router'=>strpos($backend_main,'cross_language_resolution_router')!==false,
 'backend_health'=>strpos($backend_main,'"cross_language_entity_toponym_resolution": True')!==false,
 'api_prefix'=>strpos($backend_api,'prefix="/v1/research-librarian/cross-language-entity-toponym-resolution"')!==false,
 'api_auth'=>strpos($backend_api,'require_independent_access')!==false,
 'service_human_review'=>strpos($backend_service,'"accepted_resolution_requires_human_review": True')!==false,
 'service_no_identity_promotion'=>strpos($backend_service,'"automatic_identity_promotion": False')!==false,
 'service_no_geocoding'=>strpos($backend_service,'"automatic_remote_geocoding": False')!==false,
 'service_entity_resolution'=>strpos($backend_service,'def resolve_entity(')!==false,
 'service_toponym_resolution'=>strpos($backend_service,'def resolve_toponym(')!==false,
 'service_alias'=>strpos($backend_service,'def add_alias_alignment(')!==false,
 'service_core_candidate'=>strpos($backend_service,'def core_candidate(')!==false,
 'service_snapshot'=>strpos($backend_service,'def freeze_snapshot(')!==false,
 'contract_entity_mention'=>strpos($backend_contract,'class EntityMentionAddRequest')!==false,
 'contract_entity_candidate'=>strpos($backend_contract,'class EntityCandidateAddRequest')!==false,
 'contract_toponym_candidate'=>strpos($backend_contract,'class ToponymCandidateAddRequest')!==false,
 'contract_alias'=>strpos($backend_contract,'class AliasAlignmentAddRequest')!==false,
 'migration_projects'=>strpos($migration,'sc_rl_cross_language_resolution_projects')!==false,
 'migration_events'=>strpos($migration,'sc_rl_cross_language_resolution_events')!==false,
 'migration_snapshots'=>strpos($migration,'sc_rl_cross_language_resolution_snapshots')!==false,
];
foreach($checks as $label=>$ok){
    if(!$ok){ fwrite(STDERR,"FAIL: $label\n"); exit(1); }
}
echo "PASS: Research Librarian v12.4.0 Cross-Language Entity & Toponym Resolution contract.\n";
