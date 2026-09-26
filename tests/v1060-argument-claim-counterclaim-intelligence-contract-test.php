<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/argument_claim_counterclaim_intelligence.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.9.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.9.0"')!==false,
 'capabilities_route'=>strpos($api,'/argument-claim-counterclaim-intelligence/capabilities')!==false,
 'claims_route'=>strpos($api,'/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/claims')!==false,
 'evidence_matrix_route'=>strpos($api,'/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/claim-evidence-matrix')!==false,
 'argument_map_route'=>strpos($api,'/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/argument-map')!==false,
 'contradiction_register_route'=>strpos($api,'/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/contradiction-register')!==false,
 'synthesis_handoff_route'=>strpos($api,'/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/argument-synthesis-handoff')!==false,
 'snapshot_route'=>strpos($api,'/argument-claim-counterclaim-intelligence/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"argument-claim-counterclaim-intelligence-snapshot"')!==false,
 'analysis_not_truth_guardrail'=>strpos($service,'claim_acceptance_is_for_analysis_not_truth_status')!==false,
 'no_auto_argument_rank'=>strpos($service,'automatic_argument_ranking')!==false,
 'no_auto_best_argument'=>strpos($service,'automatic_best_argument_selection')!==false,
 'no_auto_contradiction_resolution'=>strpos($service,'automatic_contradiction_resolution')!==false,
 'no_auto_truth'=>strpos($service,'automatic_truth_promotion')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_argument_object_authority')!==false,
 'environment_binding'=>strpos($environment,'argument-intelligence-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v10.9.0 Argument, Claim & Counterclaim Intelligence contract\n";
