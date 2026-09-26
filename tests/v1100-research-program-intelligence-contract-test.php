<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/research_program_intelligence.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 11.0.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "11.0.0"')!==false,
 'capabilities_route'=>strpos($api,'/research-program-intelligence/capabilities')!==false,
 'program_graph_route'=>strpos($api,'/research-program-intelligence/programs/{research_program_id}/program-graph')!==false,
 'handoff_route'=>strpos($api,'/research-program-intelligence/programs/{research_program_id}/handoffs')!==false,
 'snapshot_route'=>strpos($api,'/research-program-intelligence/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"research-program-intelligence-snapshot"')!==false,
 'human_approval_guardrail'=>strpos($service,'human_program_approval_required')!==false,
 'no_auto_priority'=>strpos($service,'automatic_research_prioritization')!==false,
 'no_auto_resource_allocation'=>strpos($service,'automatic_resource_allocation')!==false,
 'no_auto_milestone_completion'=>strpos($service,'automatic_milestone_completion')!==false,
 'no_auto_science'=>strpos($service,'automatic_scientific_judgment')!==false,
 'no_auto_execution'=>strpos($service,'automatic_execution')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_research_object_authority')!==false,
 'environment_binding'=>strpos($environment,'research-program')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v11.0.0 Research Program Intelligence contract\n";
