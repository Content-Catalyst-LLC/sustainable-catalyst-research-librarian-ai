<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/study_protocol_preregistration.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 12.4.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "12.4.0"')!==false,
 'capabilities_route'=>strpos($api,'/study-protocol-preregistration/capabilities')!==false,
 'preregister_route'=>strpos($api,'/study-protocol-preregistration/protocols/{study_protocol_id}/preregister')!==false,
 'amendment_route'=>strpos($api,'/study-protocol-preregistration/protocols/{study_protocol_id}/amendments')!==false,
 'snapshot_route'=>strpos($api,'/study-protocol-preregistration/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"study-protocol-preregistration-snapshot"')!==false,
 'immutable_baseline'=>strpos($service,'preregistration_baseline_is_immutable_once_frozen')!==false,
 'append_only_amendments'=>strpos($service,'amendments_are_append_only_and_linked_to_baseline')!==false,
 'human_approval'=>strpos($service,'human_preregistration_approval_required')!==false,
 'no_auto_registration'=>strpos($service,'automatic_preregistration')!==false,
 'no_auto_method'=>strpos($service,'automatic_method_selection')!==false,
 'no_auto_deviation_judgment'=>strpos($service,'automatic_deviation_judgment')!==false,
 'no_auto_execution'=>strpos($service,'automatic_execution')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_research_object_authority')!==false,
 'environment_binding'=>strpos($environment,'study-protocol')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v11.5.0 Study Protocol & Preregistration Engine contract\n";
