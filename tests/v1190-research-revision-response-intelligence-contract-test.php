<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$core=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/research_revision_response_intelligence.py');
$unified=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin version'=>strpos($main,'Version: 12.0.0')!==false,
 'plugin constant'=>strpos($main,"const VERSION        = '12.0.0';")!==false,
 'response package api'=>strpos($core,'/research-revision-response-intelligence/projects/{revision_response_id}/response-package')!==false,
 'snapshot job'=>strpos($jobs,'research-revision-response-intelligence-snapshot')!==false,
 'satisfaction guardrail'=>preg_match('/automatic_comment_satisfaction.*False/',$service)===1,
 'accept reject guardrail'=>preg_match('/automatic_accept_reject.*False/',$service)===1,
 'validity guardrail'=>preg_match('/automatic_scientific_validity_verdict.*False/',$service)===1,
 'truth guardrail'=>preg_match('/automatic_truth_promotion.*False/',$service)===1,
 'unified binding'=>strpos($unified,'research-revision-response')!==false,
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}}
echo "PASS: Research Librarian v11.9.0 research revision/response intelligence contract.\n";
