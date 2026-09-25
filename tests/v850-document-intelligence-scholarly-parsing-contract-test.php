<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$backend = file_get_contents($root . '/backend/app/main.py');
$doc = file_get_contents($root . '/backend/app/document_intelligence.py');
$jobs = file_get_contents($root . '/backend/app/services/document_jobs.py');
$requirements = file_get_contents($root . '/backend/requirements.txt');
$manifest = json_decode(file_get_contents($root . '/data/research_librarian_document_intelligence_manifest_v8.5.0.json'), true);
$checks = array(
  'version_header' => false !== strpos($main, 'Version: 9.8.0'),
  'version_constant' => false !== strpos($main, "const VERSION        = '9.8.0';"),
  'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "9.8.0"'),
  'document_schema' => false !== strpos($doc, 'DOCUMENT_INTELLIGENCE_SCHEMA'),
  'sections' => false !== strpos($doc, 'DOCUMENT_SECTION_SCHEMA'),
  'references' => false !== strpos($doc, 'DOCUMENT_REFERENCE_SCHEMA'),
  'citations' => false !== strpos($doc, 'DOCUMENT_CITATION_SCHEMA'),
  'doi' => false !== strpos($doc, '_DOI_RE'),
  'pdf' => false !== strpos($requirements, 'pypdf'),
  'parse_endpoint' => false !== strpos($backend, 'app.include_router(documents_router)'),
  'async_job' => false !== strpos($jobs, 'document-intelligence'),
  'core_boundary' => !empty($manifest['governance']['platform_core_governs_promoted_evidence']),
  'release' => isset($manifest['release']) && '8.5.0' === $manifest['release'],
);
$failed = array_keys(array_filter($checks, static fn($ok) => !$ok));
if ($failed) { fwrite(STDERR, 'FAILED: ' . implode(', ', $failed) . PHP_EOL); exit(1); }
echo 'PASS: Research Librarian v8.5.0 document intelligence + scholarly parsing contract.' . PHP_EOL;
