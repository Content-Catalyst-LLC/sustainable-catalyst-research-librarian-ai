<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$backend = file_get_contents($root . '/backend/app/source_identity.py');
$api = file_get_contents($root . '/backend/app/api/sources.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$worker = file_get_contents($root . '/backend/app/services/document_jobs.py');
$manifest = json_decode(file_get_contents($root . '/data/research_librarian_source_identity_manifest_v8.6.0.json'), true);
$checks = [
  'version_header' => false !== strpos($main, 'Version: 8.9.0'),
  'version_constant' => false !== strpos($main, "const VERSION        = '8.9.0';"),
  'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "8.9.0"'),
  'source_schema' => false !== strpos($backend, 'sc-research-librarian-source-identity/1.0'),
  'citation_schema' => false !== strpos($backend, 'sc-research-librarian-citation-graph/1.0'),
  'stable_identifiers' => false !== strpos($backend, 'IDENTITY_PRIORITY = ("doi", "arxiv", "pmid", "isbn", "url")'),
  'conflict' => false !== strpos($backend, 'SourceIdentityConflict'),
  'citation_stub' => false !== strpos($backend, '_create_stub'),
  'postgres_tables' => false !== strpos($backend, 'sc_rl_canonical_sources') && false !== strpos($backend, 'sc_rl_citation_edges'),
  'routes' => false !== strpos($api, 'APIRouter(prefix="/v1/sources"'),
  'job_type' => false !== strpos($jobs, '"source-identity"'),
  'ingestion_integration' => false !== strpos($worker, 'get_source_graph_store().resolve'),
  'migration' => file_exists($root . '/backend/migrations/005_source_identity_citation_graph.sql'),
  'manifest_release' => isset($manifest['release']) && '8.6.0' === $manifest['release'],
  'core_boundary' => isset($manifest['governance']['platform_core_governs_promoted_evidence']) && true === $manifest['governance']['platform_core_governs_promoted_evidence'],
];
foreach ($checks as $name => $ok) { if (!$ok) { fwrite(STDERR, "FAIL: $name\n"); exit(1); } }
echo "PASS: Research Librarian v8.6.0 source identity, deduplication, and citation graph contract.\n";
