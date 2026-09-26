<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.7.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.7.0"')!==false,
 'capabilities_route'=>strpos($api,'/unified-research-environment/capabilities')!==false,
 'dossier_route'=>strpos($api,'/unified-research-environment/environments/{environment_id}/dossier')!==false,
 'snapshot_route'=>strpos($api,'/unified-research-environment/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"unified-research-environment-snapshot"')!==false,
 'source_authority_guardrail'=>strpos($service,'component_authority_remains_with_source_system')!==false,
 'truth_guardrail'=>strpos($service,'automatic_truth_promotion')!==false,
 'model_guardrail'=>strpos($service,'automatic_model_selection')!==false,
 'judgment_guardrail'=>strpos($service,'automatic_scholarly_judgment')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v10.7.0 Unified Scholarly & AI Research Intelligence Environment contract\n";
