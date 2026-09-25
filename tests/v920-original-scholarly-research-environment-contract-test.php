<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$backend = file_get_contents($root . '/backend/app/__init__.py');
$core = file_get_contents($root . '/backend/app/api/core.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$required = [
  'plugin_version' => strpos($main, 'Version: 9.9.0') !== false,
  'backend_version' => strpos($backend, '__version__ = "9.9.0"') !== false,
  'contract' => file_exists($root . '/backend/app/contracts/scholarly_research.py'),
  'service' => file_exists($root . '/backend/app/services/scholarly_research.py'),
  'migration' => file_exists($root . '/backend/migrations/007_original_scholarly_research_environment.sql'),
  'python_tests' => file_exists($root . '/backend/tests/test_v920_scholarly_research.py'),
  'manifest' => file_exists($root . '/data/research_librarian_scholarly_research_manifest_v9.2.0.json'),
  'capability_route' => strpos($core, '/scholarly-research/capabilities') !== false,
  'package_route' => strpos($core, '/scholarly-research/studies/{study_id}/packages/freeze') !== false,
  'async_job' => strpos($jobs, 'scholarly-research-package') !== false,
];
foreach ($required as $name => $ok) {
  if (!$ok) { fwrite(STDERR, "FAIL: $name\n"); exit(1); }
}
echo "PASS: Research Librarian v9.9.0 Original Research & Scholarly Research Environment contract\n";
