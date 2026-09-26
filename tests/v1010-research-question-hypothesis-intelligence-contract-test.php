<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/research_question_hypothesis.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.8.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.8.0"')!==false,
 'capabilities_route'=>strpos($api,'/research-question-hypothesis/capabilities')!==false,
 'plan_route'=>strpos($api,'/research-question-hypothesis/plans')!==false,
 'review_route'=>strpos($api,'/research-question-hypothesis/plans/{plan_id}/review-state')!==false,
 'core_candidates_route'=>strpos($api,'/research-question-hypothesis/plans/{plan_id}/core-candidates')!==false,
 'snapshot_route'=>strpos($api,'/research-question-hypothesis/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"research-question-hypothesis-snapshot"')!==false,
 'core_authority_guardrail'=>strpos($service,'platform_core_is_governed_question_hypothesis_authority')!==false,
 'human_approval_guardrail'=>strpos($service,'human_approval_required_for_governed_handoff')!==false,
 'truth_guardrail'=>strpos($service,'automatic_truth_promotion')!==false,
 'causal_guardrail'=>strpos($service,'automatic_causal_inference')!==false,
 'environment_binding'=>strpos($environment,'research-question-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v10.8.0 Research Question & Hypothesis Intelligence contract\n";
