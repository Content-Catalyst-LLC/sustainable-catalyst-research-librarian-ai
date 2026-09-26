<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/dataset_discovery_data_fitness.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.8.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.8.0"')!==false,
 'capabilities_route'=>strpos($api,'/dataset-discovery-data-fitness/capabilities')!==false,
 'coverage_route'=>strpos($api,'/dataset-discovery-data-fitness/projects/{data_fitness_id}/coverage-matrix')!==false,
 'handoff_route'=>strpos($api,'/dataset-discovery-data-fitness/projects/{data_fitness_id}/computational-planning-handoff')!==false,
 'snapshot_route'=>strpos($api,'/dataset-discovery-data-fitness/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"dataset-discovery-data-fitness-snapshot"')!==false,
 'human_fitness_guardrail'=>strpos($service,'human_fitness_decision_required')!==false,
 'question_specific_fit'=>strpos($service,'fitness_is_question_specific_not_global_quality')!==false,
 'no_auto_suitability'=>strpos($service,'automatic_dataset_suitability')!==false,
 'no_auto_quality'=>strpos($service,'automatic_quality_certification')!==false,
 'no_auto_ingestion'=>strpos($service,'automatic_ingestion')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_research_object_authority')!==false,
 'environment_binding'=>strpos($environment,'dataset-fitness-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v10.8.0 Dataset Discovery & Data Fitness Intelligence contract\n";
