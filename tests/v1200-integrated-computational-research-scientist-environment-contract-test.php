<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$core=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/integrated_computational_research_scientist_environment.py');
$checks=[
 'plugin version'=>strpos($main,'Version: 12.0.8')!==false,
 'plugin constant'=>strpos($main,"const VERSION        = '12.0.8';")!==false,
 'scientist dossier api'=>strpos($core,'/integrated-computational-research-scientist-environment/environments/{scientist_environment_id}/dossier')!==false,
 'snapshot job'=>strpos($jobs,'integrated-computational-research-scientist-environment-snapshot')!==false,
 'execution guardrail'=>preg_match('/automatic_execution.*False/',$service)===1,
 'model selection guardrail'=>preg_match('/automatic_model_selection.*False/',$service)===1,
 'validity guardrail'=>preg_match('/automatic_scientific_validity_verdict.*False/',$service)===1,
 'truth guardrail'=>preg_match('/automatic_truth_promotion.*False/',$service)===1,
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}}
echo "PASS: Research Librarian v12.0.0 integrated computational research scientist environment contract.\n";
