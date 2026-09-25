<?php
$root=dirname(__DIR__); $main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$checks=[
'plugin_version'=>false!==strpos($main,'Version: 10.1.0'),
'backend_version'=>false!==strpos(file_get_contents($root.'/backend/app/__init__.py'),'__version__ = "10.1.0"'),
'contract'=>false!==strpos(file_get_contents($root.'/backend/app/contracts/statistical_research.py'),'sc.core.statistical-reasoning-object-model.v1'),
'service'=>file_exists($root.'/backend/app/services/statistical_research.py'),
'api'=>false!==strpos(file_get_contents($root.'/backend/app/api/core.py'),'/statistical-research/plan'),
'job'=>false!==strpos(file_get_contents($root.'/backend/app/async_jobs.py'),'statistical-analysis-plan'),
'governance'=>false!==strpos(file_get_contents($root.'/backend/app/services/statistical_research.py'),'automatic_significance_inference'),
];
foreach($checks as $k=>$v){if(!$v){fwrite(STDERR,"FAIL: $k\n");exit(1);}}
echo "PASS: Research Librarian v10.1.0 statistical and analytical research integration contract\n";
