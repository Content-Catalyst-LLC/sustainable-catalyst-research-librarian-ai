<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$api=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$service=file_get_contents($root.'/backend/app/services/systematic_review_evidence_synthesis.py');
$environment=file_get_contents($root.'/backend/app/services/unified_scholarly_ai_environment.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.5.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.5.0"')!==false,
 'capabilities_route'=>strpos($api,'/systematic-review-evidence-synthesis/capabilities')!==false,
 'screening_route'=>strpos($api,'/systematic-review-evidence-synthesis/reviews/{review_id}/screening-decisions')!==false,
 'extraction_matrix_route'=>strpos($api,'/systematic-review-evidence-synthesis/reviews/{review_id}/extraction-matrix')!==false,
 'synthesis_handoff_route'=>strpos($api,'/systematic-review-evidence-synthesis/reviews/{review_id}/synthesis-handoffs')!==false,
 'snapshot_route'=>strpos($api,'/systematic-review-evidence-synthesis/snapshots/freeze')!==false,
 'durable_job'=>strpos($jobs,'"systematic-review-evidence-synthesis-snapshot"')!==false,
 'human_screening_guardrail'=>strpos($service,'human_screening_decisions_required')!==false,
 'no_auto_inclusion'=>strpos($service,'automatic_study_inclusion')!==false,
 'no_auto_bias_judgment'=>strpos($service,'automatic_risk_of_bias_judgment')!==false,
 'no_auto_meta_analysis'=>strpos($service,'automatic_meta_analysis_execution')!==false,
 'library_boundary'=>strpos($service,'knowledge_library_remains_source_authority')!==false,
 'core_boundary'=>strpos($service,'platform_core_remains_authority')!==false,
 'environment_binding'=>strpos($environment,'systematic-review-plan')!==false,
];
foreach($checks as $k=>$ok){ if(!$ok){ fwrite(STDERR,"FAIL: $k\n"); exit(1);} }
echo "PASS: Research Librarian v10.5.0 Systematic Review & Evidence Synthesis Intelligence contract\n";
