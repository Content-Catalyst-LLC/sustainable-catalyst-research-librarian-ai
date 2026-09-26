<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/evidence_search_strategy.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.4.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.4.0"')!==false,
 'capabilities_route'=>strpos($api,'/evidence-search-strategy/capabilities')!==false,
 'strategy_route'=>strpos($api,'/evidence-search-strategy/strategies')!==false,
 'coverage_route'=>strpos($api,'/evidence-search-strategy/strategies/{strategy_id}/coverage')!==false,
 'execution_handoff_route'=>strpos($api,'/evidence-search-strategy/strategies/{strategy_id}/execution-handoffs')!==false,
 'snapshot_route'=>strpos($api,'/evidence-search-strategy/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"evidence-search-strategy-snapshot"')!==false,
 'human_protocol_guardrail'=>strpos($service,'human_search_protocol_approval_required')!==false,
 'no_auto_search'=>strpos($service,'automatic_external_search_execution')!==false,
 'no_auto_source_acceptance'=>strpos($service,'automatic_source_acceptance')!==false,
 'library_boundary'=>strpos($service,'knowledge_library_owns_source_ingestion_and_retrieval')!==false,
 'environment_binding'=>strpos($environment,'evidence-search-strategy-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v10.4.0 Evidence Search Strategy Engine contract\n";
