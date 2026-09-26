<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/__init__.py');
$core=file_get_contents($root.'/backend/app/api/core.py');
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');
$checks=[
 'plugin_version'=>strpos($main,'Version: 10.4.0')!==false,
 'backend_version'=>strpos($backend,'__version__ = "10.4.0"')!==false,
 'contract'=>file_exists($root.'/backend/app/contracts/scholarly_publication.py'),
 'service'=>file_exists($root.'/backend/app/services/scholarly_publication.py'),
 'test'=>file_exists($root.'/backend/tests/test_v940_scholarly_publication.py'),
 'migration'=>file_exists($root.'/backend/migrations/009_scholarly_publication_dissemination.sql'),
 'manifest'=>file_exists($root.'/data/research_librarian_scholarly_publication_manifest_v9.4.0.json'),
 'capability_route'=>strpos($core,'/scholarly-publication/capabilities')!==false,
 'citation_route'=>strpos($core,'/citation-exports')!==false,
 'library_handoff_route'=>strpos($core,'/knowledge-library-handoffs')!==false,
 'package_route'=>strpos($core,'/packages/freeze')!==false,
 'durable_job'=>strpos($jobs,'scholarly-publication-package')!==false,
];
foreach($checks as $name=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $name\n");exit(1);}}
echo "PASS: Research Librarian v10.4.0 Scholarly Publication, Citation & Research Dissemination Environment contract\n";
