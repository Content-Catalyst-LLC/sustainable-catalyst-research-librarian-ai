<?php
$root=dirname(__DIR__); $main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$checks=[
'plugin_version'=>false!==strpos($main,'Version: 9.3.0'),
'backend_version'=>false!==strpos(file_get_contents($root.'/backend/app/__init__.py'),'__version__ = "9.3.0"'),
'contract'=>file_exists($root.'/backend/app/contracts/visual_research.py') && false!==strpos(file_get_contents($root.'/backend/app/contracts/visual_research.py'),'sc-research-librarian-visual-research-intelligence/1.0'),
'service'=>file_exists($root.'/backend/app/services/visual_research.py'),
'api'=>false!==strpos(file_get_contents($root.'/backend/app/api/core.py'),'/visual-research/plan'),
'job'=>false!==strpos(file_get_contents($root.'/backend/app/async_jobs.py'),'visual-research-plan'),
'core_visual'=>false!==strpos(file_get_contents($root.'/backend/app/clients/platform_core.py'),'/v1/visual-reasoning/objects'),
'unified_binding'=>false!==strpos(file_get_contents($root.'/backend/app/clients/platform_core.py'),'/v1/research/unified-runtime/visual-bindings'),
'governance'=>false!==strpos(file_get_contents($root.'/backend/app/services/visual_research.py'),'automatic_visual_truth_promotion'),
];
foreach($checks as $k=>$v){if(!$v){fwrite(STDERR,"FAIL: $k\n");exit(1);}}
echo "PASS: Research Librarian v9.3.0 Visual Research Intelligence contract\n";
