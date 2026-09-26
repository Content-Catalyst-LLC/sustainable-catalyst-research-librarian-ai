<?php
$root=dirname(__DIR__); $main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php'); $backend=file_get_contents($root.'/backend/app/__init__.py'); $core=file_get_contents($root.'/backend/app/api/core.py'); $jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.9.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.9.0"')!==false,
 'contract'=>file_exists($root.'/backend/app/contracts/ai_research_context.py'),
 'service'=>file_exists($root.'/backend/app/services/ai_research_context.py'),
 'migration'=>file_exists($root.'/backend/migrations/011_ai_aware_retrieval_context_engineering.sql'),
 'capability_route'=>strpos($core,'/ai-research-context/capabilities')!==false,
 'run_route'=>strpos($core,'/ai-research-context/retrieval-runs')!==false,
 'lineage_route'=>strpos($core,'/ai-research-context/contexts/{context_id}/lineage')!==false,
 'durable_job'=>strpos($jobs,'ai-research-context-snapshot')!==false,
];
foreach($checks as $k=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $k\n");exit(1);}}
echo "PASS: Research Librarian v10.9.0 AI-Aware Retrieval & Research Context Engineering contract\n";
