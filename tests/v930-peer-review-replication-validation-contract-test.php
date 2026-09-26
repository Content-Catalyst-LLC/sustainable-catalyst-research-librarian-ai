<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$backend = file_get_contents($root . '/backend/app/__init__.py');
$core = file_get_contents($root . '/backend/app/api/core.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$checks = [
  'plugin_version' => strpos($main, 'Version: 10.4.0') !== false,
  'backend_version' => strpos($backend, '__version__ = "10.4.0"') !== false,
  'contract' => file_exists($root . '/backend/app/contracts/peer_review.py'),
  'service' => file_exists($root . '/backend/app/services/peer_review.py'),
  'test' => file_exists($root . '/backend/tests/test_v930_peer_review.py'),
  'migration' => file_exists($root . '/backend/migrations/008_peer_review_replication_validation.sql'),
  'manifest' => file_exists($root . '/data/research_librarian_peer_review_manifest_v9.3.0.json'),
  'capability_route' => strpos($core, '/scholarly-validation/capabilities') !== false,
  'review_route' => strpos($core, '/rounds/{round_id}/reviews') !== false,
  'replication_route' => strpos($core, '/replications') !== false,
  'decision_route' => strpos($core, '/editorial-decisions') !== false,
  'package_route' => strpos($core, '/packages/freeze') !== false,
  'durable_job' => strpos($jobs, 'peer-review-validation-package') !== false,
];
foreach ($checks as $name => $ok) { if (!$ok) { fwrite(STDERR, "FAIL: $name\n"); exit(1); } }
echo "PASS: Research Librarian v10.4.0 Peer Review, Replication & Scholarly Validation Environment contract\n";
