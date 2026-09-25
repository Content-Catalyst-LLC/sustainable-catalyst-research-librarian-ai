<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$client = file_get_contents($root . '/backend/app/clients/platform_core.py');
$api = file_get_contents($root . '/backend/app/api/core.py');
$service = file_get_contents($root . '/backend/app/services/core_evidence_bridge.py');
$contracts = file_get_contents($root . '/backend/app/contracts/evidence_bridge.py');
$manifest = json_decode(file_get_contents($root . '/data/research_librarian_core_evidence_bridge_manifest_v8.7.0.json'), true);
$checks = [
  'version_header' => false !== strpos($main, 'Version: 10.2.0'),
  'version_constant' => false !== strpos($main, "const VERSION        = '10.2.0';"),
  'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "10.2.0"'),
  'bridge_schema' => false !== strpos($contracts, 'sc-research-librarian-core-evidence-bridge/1.0'),
  'core_snapshot_client' => false !== strpos($client, '/v1/source-snapshots'),
  'core_evidence_client' => false !== strpos($client, '/v1/evidence-records'),
  'snapshot_route' => false !== strpos($api, '/evidence/source-snapshots/promote'),
  'passage_route' => false !== strpos($api, '/evidence/passages/promote'),
  'stub_fail_closed' => false !== strpos($service, 'Citation-only source stubs cannot be promoted'),
  'snapshot_before_evidence' => false !== strpos($service, 'cannot be promoted until its Librarian source snapshot has a synced Platform Core binding'),
  'neutral_default' => false !== strpos($contracts, '= "neutral"'),
  'unreviewed_default' => false !== strpos($contracts, 'default="unreviewed"'),
  'no_truth_judgment' => false !== strpos($service, '"automated_truth_judgment": False'),
  'manifest_release' => isset($manifest['release']) && '8.7.0' === $manifest['release'],
  'core_authority' => isset($manifest['governance']['platform_core_is_governed_evidence_authority']) && true === $manifest['governance']['platform_core_is_governed_evidence_authority'],
];
foreach ($checks as $name => $ok) { if (!$ok) { fwrite(STDERR, "FAIL: $name\n"); exit(1); } }
echo "PASS: Research Librarian v8.7.0 Core Evidence Bridge contract.\n";
