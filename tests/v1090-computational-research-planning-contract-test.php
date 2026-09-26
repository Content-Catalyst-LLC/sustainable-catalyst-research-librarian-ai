<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/computational_research_planning.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.9.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.9.0"')!==false,
 'capabilities_route'=>strpos($api,'/computational-research-planning/capabilities')!==false,
 'graph_route'=>strpos($api,'/computational-research-planning/plans/{computational_plan_id}/execution-graph')!==false,
 'handoff_route'=>strpos($api,'/computational-research-planning/plans/{computational_plan_id}/execution-handoffs')!==false,
 'snapshot_route'=>strpos($api,'/computational-research-planning/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"computational-research-planning-snapshot"')!==false,
 'human_approval_guardrail'=>strpos($service,'human_method_and_runtime_approval_required')!==false,
 'no_auto_method'=>strpos($service,'automatic_method_selection')!==false,
 'no_auto_runtime'=>strpos($service,'automatic_runtime_selection')!==false,
 'no_auto_execution'=>strpos($service,'automatic_execution')!==false,
 'specialist_runtime_boundary'=>strpos($service,'specialist_runtimes_own_execution')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_research_object_authority')!==false,
 'environment_binding'=>strpos($environment,'computational-research-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k
"); exit(1);} }
echo "PASS: Research Librarian v10.9.0 Computational Research Planning contract
";
