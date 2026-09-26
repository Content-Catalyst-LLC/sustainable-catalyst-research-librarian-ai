<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/research_gap_novelty_intelligence.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.8.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.8.0"')!==false,
 'capabilities_route'=>strpos($api,'/research-gap-novelty-intelligence/capabilities')!==false,
 'signals_route'=>strpos($api,'/research-gap-novelty-intelligence/projects/{gap_novelty_id}/structural-signals')!==false,
 'landscape_route'=>strpos($api,'/research-gap-novelty-intelligence/projects/{gap_novelty_id}/landscape')!==false,
 'planning_handoff_route'=>strpos($api,'/research-gap-novelty-intelligence/projects/{gap_novelty_id}/research-planning-handoff')!==false,
 'snapshot_route'=>strpos($api,'/research-gap-novelty-intelligence/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"research-gap-novelty-intelligence-snapshot"')!==false,
 'human_gap_guardrail'=>strpos($service,'human_gap_acceptance_required')!==false,
 'human_novelty_guardrail'=>strpos($service,'human_novelty_acceptance_required')!==false,
 'no_auto_gap'=>strpos($service,'automatic_gap_certification')!==false,
 'no_auto_novelty'=>strpos($service,'automatic_novelty_certification')!==false,
 'no_auto_originality'=>strpos($service,'automatic_originality_claims')!==false,
 'no_auto_priority'=>strpos($service,'automatic_priority_ranking')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_research_object_authority')!==false,
 'environment_binding'=>strpos($environment,'research-gap-novelty-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v10.8.0 Research Gap & Novelty Intelligence contract\n";
