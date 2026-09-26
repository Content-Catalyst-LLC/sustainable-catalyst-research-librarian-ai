<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$core=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.5.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.5.0"')!==false,
 'contract'=>file_exists($root.'/backend/app/contracts/rag_evaluation.py'),
 'service'=>file_exists($root.'/backend/app/services/rag_evaluation.py'),
 'test'=>file_exists($root.'/backend/tests/test_v970_rag_evaluation.py'),
 'migration'=>file_exists($root.'/backend/migrations/012_rag_evaluation_evidence_grounding.sql'),
 'capability_route'=>strpos($core,'/rag-evaluation/capabilities')!==false,
 'case_route'=>strpos($core,'/rag-evaluation/evaluations/{evaluation_id}/cases')!==false,
 'claim_route'=>strpos($core,'/claim-assessments')!==false,
 'citation_route'=>strpos($core,'/citation-assessments')!==false,
 'comparison_route'=>strpos($core,'/rag-evaluation/comparisons')!==false,
 'snapshot_route'=>strpos($core,'/rag-evaluation/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'rag-evaluation-snapshot')!==false,
];
foreach($checks as $name=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $name\n");exit(1);}}
echo "PASS: Research Librarian v10.5.0 RAG Evaluation & Evidence-Grounding Framework contract\n";
