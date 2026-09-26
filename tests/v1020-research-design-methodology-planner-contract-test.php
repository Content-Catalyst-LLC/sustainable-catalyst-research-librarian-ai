<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/research_design_methodology.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 11.0.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "11.0.0"')!==false,
 'capabilities_route'=>strpos($api,'/research-design-methodology/capabilities')!==false,
 'plan_route'=>strpos($api,'/research-design-methodology/plans')!==false,
 'comparison_route'=>strpos($api,'/research-design-methodology/plans/{plan_id}/comparison')!==false,
 'execution_handoff_route'=>strpos($api,'/research-design-methodology/plans/{plan_id}/execution-handoffs')!==false,
 'snapshot_route'=>strpos($api,'/research-design-methodology/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"research-design-methodology-snapshot"')!==false,
 'human_selection_guardrail'=>strpos($service,'human_method_selection_required')!==false,
 'no_auto_method_selection'=>strpos($service,'automatic_method_selection')!==false,
 'no_auto_execution'=>strpos($service,'automatic_execution')!==false,
 'environment_binding'=>strpos($environment,'research-design-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v11.0.0 Research Design & Methodology Planner contract\n";
