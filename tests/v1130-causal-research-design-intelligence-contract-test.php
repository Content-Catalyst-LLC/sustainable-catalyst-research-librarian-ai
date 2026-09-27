<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/causal_research_design_intelligence.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 11.5.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "11.5.0"')!==false,
 'capabilities_route'=>strpos($api,'/causal-research-design-intelligence/capabilities')!==false,
 'role_route'=>strpos($api,'/causal-research-design-intelligence/designs/{causal_design_id}/variable-roles')!==false,
 'strategy_route'=>strpos($api,'/causal-research-design-intelligence/designs/{causal_design_id}/identification-strategies')!==false,
 'graph_route'=>strpos($api,'/causal-research-design-intelligence/designs/{causal_design_id}/causal-graph')!==false,
 'handoff_route'=>strpos($api,'/causal-research-design-intelligence/designs/{causal_design_id}/runtime-handoffs')!==false,
 'snapshot_route'=>strpos($api,'/causal-research-design-intelligence/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"causal-research-design-intelligence-snapshot"')!==false,
 'human_approval'=>strpos($service,'human_causal_design_approval_required')!==false,
 'statistical_lineage'=>strpos($service,'statistical_plan_lineage_is_inherited_not_rewritten')!==false,
 'dag_boundary'=>strpos($service,'dag_represents_assumptions_not_proven_structure')!==false,
 'no_auto_identification'=>strpos($service,'automatic_causal_identification')!==false,
 'no_auto_adjustment'=>strpos($service,'automatic_adjustment_set_selection')!==false,
 'no_auto_instrument'=>strpos($service,'automatic_instrument_validation')!==false,
 'no_auto_estimation'=>strpos($service,'automatic_causal_estimation')!==false,
 'no_auto_causality'=>strpos($service,'automatic_causality_inference')!==false,
 'no_auto_execution'=>strpos($service,'automatic_execution')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_governed_causal_object_authority')!==false,
 'environment_binding'=>strpos($environment,'causal-research-design')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v11.5.0 Causal Research Design Intelligence contract\n";
