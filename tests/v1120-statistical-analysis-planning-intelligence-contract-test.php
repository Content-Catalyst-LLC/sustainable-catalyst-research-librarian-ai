<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/statistical_analysis_planning_intelligence.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 12.1.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "12.1.0"')!==false,
 'capabilities_route'=>strpos($api,'/statistical-analysis-planning-intelligence/capabilities')!==false,
 'estimand_route'=>strpos($api,'/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/estimands')!==false,
 'model_route'=>strpos($api,'/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/model-specifications')!==false,
 'handoff_route'=>strpos($api,'/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/runtime-handoffs')!==false,
 'snapshot_route'=>strpos($api,'/statistical-analysis-planning-intelligence/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"statistical-analysis-planning-intelligence-snapshot"')!==false,
 'human_approval'=>strpos($service,'human_statistical_approval_required')!==false,
 'protocol_lineage'=>strpos($service,'preregistered_protocol_lineage_is_inherited_not_rewritten')!==false,
 'v811_bridge'=>strpos($service,'existing_statistical_research_layer_remains_runtime_core_bridge')!==false,
 'no_auto_model'=>strpos($service,'automatic_model_selection')!==false,
 'no_auto_power'=>strpos($service,'automatic_power_calculation')!==false,
 'no_auto_significance'=>strpos($service,'automatic_significance_inference')!==false,
 'no_auto_causality'=>strpos($service,'automatic_causality_inference')!==false,
 'no_auto_execution'=>strpos($service,'automatic_execution')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_statistical_reasoning_authority')!==false,
 'environment_binding'=>strpos($environment,'statistical-analysis-plan-intelligence')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v11.5.0 Statistical Analysis Planning Intelligence contract\n";
