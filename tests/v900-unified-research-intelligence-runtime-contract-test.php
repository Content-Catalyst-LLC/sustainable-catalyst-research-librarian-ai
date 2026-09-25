<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/unified_research_runtime.py');
$checks=[
  'plugin_version'=>false!==strpos($main,'Version: 10.1.0'),
  'backend_version'=>false!==strpos(file_get_contents($root.'/backend/app/__init__.py'),'__version__ = "10.1.0"'),
  'contract'=>file_exists($root.'/backend/app/contracts/unified_research_runtime.py') && false!==strpos(file_get_contents($root.'/backend/app/contracts/unified_research_runtime.py'),'sc-research-librarian-unified-research-intelligence-runtime/1.0'),
  'service'=>file_exists($root.'/backend/app/services/unified_research_runtime.py'),
  'capabilities_route'=>false!==strpos($api,'/unified-research/capabilities'),
  'readiness_route'=>false!==strpos($api,'/unified-research/readiness'),
  'plan_route'=>false!==strpos($api,'/unified-research/plan'),
  'execute_route'=>false!==strpos($api,'/unified-research/execute'),
  'durable_job'=>false!==strpos($jobs,'unified-research-runtime'),
  'human_gate'=>false!==strpos($service,'human_review_required_for_core_promotion'),
  'no_core_write'=>false!==strpos($service,'automatic_core_writes'),
  'reproducibility'=>false!==strpos($service,'run_fingerprint'),
];
foreach($checks as $k=>$v){if(!$v){fwrite(STDERR,"FAIL: $k\n");exit(1);}}
echo "PASS: Research Librarian v10.1.0 Unified Research Intelligence Runtime contract\n";
