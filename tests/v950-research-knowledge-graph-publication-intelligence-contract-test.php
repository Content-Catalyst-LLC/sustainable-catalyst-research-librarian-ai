<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$core=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.4.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.4.0"')!==false,
 'contract'=>file_exists($root.'/backend/app/contracts/research_knowledge_graph.py'),
 'service'=>file_exists($root.'/backend/app/services/research_knowledge_graph.py'),
 'test'=>file_exists($root.'/backend/tests/test_v950_research_knowledge_graph.py'),
 'migration'=>file_exists($root.'/backend/migrations/010_research_knowledge_graph_publication_intelligence.sql'),
 'capability_route'=>strpos($core,'/research-knowledge-graph/capabilities')!==false,
 'proposal_route'=>strpos($core,'/edge-proposals')!==false,
 'materialize_route'=>strpos($core,'/materialize')!==false,
 'intelligence_route'=>strpos($core,'/intelligence')!==false,
 'snapshot_route'=>strpos($core,'/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'research-knowledge-graph-snapshot')!==false,
];
foreach($checks as $name=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $name\n");exit(1);}}
echo "PASS: Research Librarian v10.4.0 Research Knowledge Graph & Publication Intelligence contract\n";
