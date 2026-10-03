<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/reproduction_replication_intelligence.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$migration=file_get_contents($root.'/backend/migrations/030_reproduction_replication_intelligence.sql');
$checks=[
 'plugin_version'=>strpos($main,'Version: 12.0.3')!==false,
 'backend_version'=>strpos($backend,'__version__ = "12.0.3"')!==false,
 'capabilities_route'=>strpos($api,'/reproduction-replication-intelligence/capabilities')!==false,
 'attempt_route'=>strpos($api,'/reproduction-replication-intelligence/projects/{reproduction_replication_id}/reproduction-attempts')!==false,
 'replication_route'=>strpos($api,'/reproduction-replication-intelligence/projects/{reproduction_replication_id}/replication-studies')!==false,
 'comparability_route'=>strpos($api,'/reproduction-replication-intelligence/projects/{reproduction_replication_id}/comparability-criteria')!==false,
 'assessment_route'=>strpos($api,'/reproduction-replication-intelligence/projects/{reproduction_replication_id}/assessments')!==false,
 'matrix_route'=>strpos($api,'/reproduction-replication-intelligence/projects/{reproduction_replication_id}/comparison-matrix')!==false,
 'snapshot_route'=>strpos($api,'/reproduction-replication-intelligence/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"reproduction-replication-intelligence-snapshot"')!==false,
 'distinction'=>strpos($service,'reproduction_and_replication_are_distinct')!==false,
 'human_assessment'=>strpos($service,'human_outcome_assessment')!==false,
 'no_auto_repro'=>strpos($service,'automatic_reproduction_verdict')!==false,
 'no_auto_replication'=>strpos($service,'automatic_replication_verdict')!==false,
 'no_auto_claim'=>strpos($service,'automatic_claim_acceptance')!==false,
 'no_auto_execution'=>strpos($service,'automatic_execution')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_governed_research_object_authority')!==false,
 'environment_binding'=>strpos($environment,'reproduction-replication-plan')!==false,
 'migration'=>strpos($migration,'sc_rl_reproduction_replication_projects')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v11.5.0 Reproduction & Replication Intelligence contract\n";
