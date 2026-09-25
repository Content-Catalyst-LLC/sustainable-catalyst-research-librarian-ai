<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$client = file_get_contents($root . '/backend/app/clients/platform_core.py');
$api = file_get_contents($root . '/backend/app/api/core.py');
$service = file_get_contents($root . '/backend/app/services/core_research_sync.py');
$contracts = file_get_contents($root . '/backend/app/contracts/research_sync.py');
$manifest = json_decode(file_get_contents($root . '/data/research_librarian_core_research_sync_manifest_v8.8.0.json'), true);
$checks = [
  'version_header' => false !== strpos($main, 'Version: 9.9.0'),
  'version_constant' => false !== strpos($main, "const VERSION        = '9.9.0';"),
  'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "9.9.0"'),
  'sync_schema' => false !== strpos($contracts, 'sc-research-librarian-core-research-sync/1.0'),
  'core_state_contract' => false !== strpos($contracts, 'sc.research.project-state-versioning-reproducibility.v1'),
  'capability_route' => false !== strpos($api, '/research-sync/capabilities'),
  'plan_route' => false !== strpos($api, '/research-sync/plan'),
  'sync_route' => false !== strpos($api, '/research-sync/synchronize'),
  'project_state_client' => false !== strpos($client, '/v1/research/project-state/states'),
  'freeze_client' => false !== strpos($client, '/freeze'),
  'snapshot_client' => false !== strpos($client, '/snapshots'),
  'idempotent_sync' => false !== strpos($service, 'idempotent_replay'),
  'declared_lineage' => false !== strpos($service, 'declared_not_inferred'),
  'no_truth' => false !== strpos($service, 'synchronization_does_not_determine_truth'),
  'manifest_release' => isset($manifest['release']) && '8.8.0' === $manifest['release'],
  'immutable_versions' => true === ($manifest['capabilities']['immutable_project_state_versions'] ?? false),
];
foreach ($checks as $name => $ok) { if (!$ok) { fwrite(STDERR, "FAIL: $name\n"); exit(1); } }
echo "PASS: Research Librarian v8.8.0 Core Research Object Synchronization contract.\n";
