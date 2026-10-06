<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$wp=file_get_contents($root.'/includes/class-sc-rl-v1210-neural-research-intelligence-foundation.php');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$backend_api=file_get_contents($root.'/backend/app/api/neural_research.py');
$backend_service=file_get_contents($root.'/backend/app/services/neural_research_intelligence.py');
$backend_contract=file_get_contents($root.'/backend/app/contracts/neural_research_intelligence.py');
$migration=file_get_contents($root.'/backend/migrations/041_neural_research_intelligence_foundation.sql');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.3.0')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.3.0';")!==false,
 'module_required'=>strpos($main,'class-sc-rl-v1210-neural-research-intelligence-foundation.php')!==false,
 'module_initialized'=>strpos($main,'SC_RL_V1210_Neural_Research_Intelligence_Foundation::init();')!==false,
 'wp_route'=>strpos($wp,"'/neural-research-foundation'")!==false,
 'wp_not_authority'=>strpos($wp,"'wordpress_runtime_authority'  => false")!==false,
 'wp_no_execution'=>strpos($wp,"'wordpress_neural_execution'   => false")!==false,
 'wp_no_weights'=>strpos($wp,"'model_weights_stored'         => false")!==false,
 'wp_no_secrets'=>strpos($wp,"'secrets_stored'               => false")!==false,
 'wp_core_authority'=>strpos($wp,"'platform_core_authority'       => true")!==false,
 'wp_specialist_execution'=>strpos($wp,"'specialist_runtime_execution' => true")!==false,
 'wp_no_remote'=>strpos($wp,'wp_remote_')===false,
 'wp_no_state_write'=>strpos($wp,'update_option(')===false && strpos($wp,'update_user_meta(')===false,
 'backend_router'=>strpos($backend_main,'neural_research_router')!==false,
 'backend_health'=>strpos($backend_main,'"neural_research_intelligence": True')!==false,
 'backend_api_prefix'=>strpos($backend_api,'prefix="/v1/research-librarian/neural-research"')!==false,
 'backend_auth'=>strpos($backend_api,'require_independent_access')!==false,
 'service_manifest'=>strpos($backend_service,'def neural_manifest()')!==false,
 'service_postgres'=>strpos($backend_service,'sc_rl_neural_research_projects')!==false,
 'service_no_execution'=>strpos($backend_service,'"librarian_execution_authority":False')!==false,
 'service_handoffs'=>strpos($backend_service,'def prepare_handoff(')!==false,
 'service_lineage'=>strpos($backend_service,'def lineage(')!==false,
 'service_core_candidate'=>strpos($backend_service,'def core_candidate(')!==false,
 'service_snapshot'=>strpos($backend_service,'def freeze_snapshot(')!==false,
 'contract_schema'=>strpos($backend_contract,'NEURAL_RESEARCH_SCHEMA')!==false,
 'contract_handoff'=>strpos($backend_contract,'NEURAL_RUNTIME_HANDOFF_SCHEMA')!==false,
 'migration_projects'=>strpos($migration,'sc_rl_neural_research_projects')!==false,
 'migration_events'=>strpos($migration,'sc_rl_neural_research_events')!==false,
 'migration_snapshots'=>strpos($migration,'sc_rl_neural_research_snapshots')!==false,
];

foreach($checks as $label=>$ok){
    if(!$ok){
        fwrite(STDERR,"FAIL: $label\n");
        exit(1);
    }
}
echo "PASS: Research Librarian v12.1.0 Neural Research Intelligence Foundation contract.\n";
