<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/simulation_model_study_planner.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 12.0.4')!==false,
 'backend_version'=>strpos($backend,'__version__ = "12.0.4"')!==false,
 'capabilities_route'=>strpos($api,'/simulation-model-study-planner/capabilities')!==false,
 'models_route'=>strpos($api,'/simulation-model-study-planner/studies/{simulation_study_id}/model-specifications')!==false,
 'scenario_route'=>strpos($api,'/simulation-model-study-planner/studies/{simulation_study_id}/scenario-sets')!==false,
 'validation_route'=>strpos($api,'/simulation-model-study-planner/studies/{simulation_study_id}/validation-plans')!==false,
 'matrix_route'=>strpos($api,'/simulation-model-study-planner/studies/{simulation_study_id}/study-matrix')!==false,
 'handoff_route'=>strpos($api,'/simulation-model-study-planner/studies/{simulation_study_id}/runtime-handoffs')!==false,
 'snapshot_route'=>strpos($api,'/simulation-model-study-planner/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"simulation-model-study-planner-snapshot"')!==false,
 'human_approval'=>strpos($service,'human_model_study_approval_required')!==false,
 'causal_lineage'=>strpos($service,'causal_design_lineage_is_inherited_not_rewritten')!==false,
 'no_auto_model'=>strpos($service,'automatic_model_selection')!==false,
 'no_auto_calibration'=>strpos($service,'automatic_calibration')!==false,
 'no_auto_validation'=>strpos($service,'automatic_validation')!==false,
 'no_auto_execution'=>strpos($service,'automatic_simulation_execution')!==false,
 'no_auto_forecast_acceptance'=>strpos($service,'automatic_forecast_acceptance')!==false,
 'no_auto_causality'=>strpos($service,'automatic_causal_inference')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_governed_model_object_authority')!==false,
 'environment_binding'=>strpos($environment,'simulation-model-study-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v11.5.0 Simulation & Model Study Planner contract\n";
