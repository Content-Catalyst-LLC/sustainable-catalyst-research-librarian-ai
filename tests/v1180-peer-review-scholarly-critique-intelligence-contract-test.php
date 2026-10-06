<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$core=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/peer_review_scholarly_critique_intelligence.py');
$unified=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin version'=>strpos($main,'Version: 12.3.0')!==false,
 'plugin constant'=>strpos($main,"const VERSION        = '12.3.0';")!==false,
 'editorial handoff api'=>strpos($core,'/peer-review-scholarly-critique-intelligence/critique-projects/{critique_project_id}/editorial-handoff')!==false,
 'snapshot job'=>strpos($jobs,'peer-review-scholarly-critique-intelligence-snapshot')!==false,
 'accept/reject guardrail'=>preg_match('/automatic_accept_reject.*False/',$service)===1,
 'editorial decision guardrail'=>preg_match('/automatic_editorial_decision.*False/',$service)===1,
 'reviewer ranking guardrail'=>preg_match('/automatic_reviewer_ranking.*False/',$service)===1,
 'validity guardrail'=>preg_match('/automatic_scientific_validity_verdict.*False/',$service)===1,
 'truth guardrail'=>preg_match('/automatic_truth_promotion.*False/',$service)===1,
 'unified binding'=>strpos($unified,'scholarly-critique')!==false,
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}}
echo "PASS: Research Librarian v11.8.0 peer review/scholarly critique intelligence contract.\n";
