<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/scholarly_literature_intelligence.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.6.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.6.0"')!==false,
 'capabilities_route'=>strpos($api,'/scholarly-literature-intelligence/capabilities')!==false,
 'citation_context_route'=>strpos($api,'/scholarly-literature-intelligence/projects/{intelligence_id}/citation-contexts')!==false,
 'landscape_route'=>strpos($api,'/scholarly-literature-intelligence/projects/{intelligence_id}/landscape')!==false,
 'citation_matrix_route'=>strpos($api,'/scholarly-literature-intelligence/projects/{intelligence_id}/citation-matrix')!==false,
 'graph_handoff_route'=>strpos($api,'/scholarly-literature-intelligence/projects/{intelligence_id}/graph-handoffs')!==false,
 'snapshot_route'=>strpos($api,'/scholarly-literature-intelligence/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"scholarly-literature-intelligence-snapshot"')!==false,
 'human_gap_guardrail'=>strpos($service,'human_gap_declaration_required')!==false,
 'no_auto_authority_rank'=>strpos($service,'automatic_authority_ranking')!==false,
 'no_auto_seminal'=>strpos($service,'automatic_seminal_work_classification')!==false,
 'graph_boundary'=>strpos($service,'research_knowledge_graph_remains_citation_graph_authority')!==false,
 'library_boundary'=>strpos($service,'knowledge_library_remains_source_authority')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_authority')!==false,
 'environment_binding'=>strpos($environment,'literature-intelligence-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v10.6.0 Scholarly Citation & Literature Intelligence contract\n";
