<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$client = file_get_contents($root . '/backend/app/clients/platform_core.py');
$api = file_get_contents($root . '/backend/app/api/core.py');
$service = file_get_contents($root . '/backend/app/services/argument_synthesis.py');
$contracts = file_get_contents($root . '/backend/app/contracts/argument_synthesis.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$manifest = json_decode(file_get_contents($root . '/data/research_librarian_argument_synthesis_manifest_v8.10.0.json'), true);
$checks = [
  'version_header' => false !== strpos($main, 'Version: 10.6.0'),
  'version_constant' => false !== strpos($main, "const VERSION        = '10.6.0';"),
  'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "10.6.0"'),
  'schema' => false !== strpos($contracts, 'sc-research-librarian-argument-contradiction-synthesis/1.0'),
  'core_contract' => false !== strpos($contracts, 'sc.research.argument-evidentiary-synthesis.v1'),
  'capability_route' => false !== strpos($api, '/argument-synthesis/capabilities'),
  'plan_route' => false !== strpos($api, '/argument-synthesis/plan'),
  'contradiction_route' => false !== strpos($api, '/argument-synthesis/contradictions/{core_project_id:path}'),
  'promote_route' => false !== strpos($api, '/argument-synthesis/promote'),
  'argument_readiness' => false !== strpos($client, '/v1/research/arguments/readiness'),
  'argument_node_client' => false !== strpos($client, '/nodes'),
  'argument_edge_client' => false !== strpos($client, '/edges'),
  'synthesis_client' => false !== strpos($client, '/syntheses'),
  'tension_client' => false !== strpos($client, '/tensions'),
  'human_review_gate' => false !== strpos($contracts, "review_decision='approved'"),
  'no_relation_inference' => false !== strpos($service, '"relation_inferred": False'),
  'no_truth' => false !== strpos($service, '"truth_determined": False'),
  'async_job' => false !== strpos($jobs, '"argument-synthesis-plan"'),
  'manifest_release' => isset($manifest['release']) && '8.10.0' === $manifest['release'],
  'manifest_review_gate' => true === ($manifest['capabilities']['human_review_required_for_core_promotion'] ?? false),
  'manifest_no_rank' => false === ($manifest['governance']['automatic_argument_ranking'] ?? true),
];
foreach ($checks as $name => $ok) { if (!$ok) { fwrite(STDERR, "FAIL: $name\n"); exit(1); } }
echo "PASS: Research Librarian v10.6.0 Argument, Contradiction & Synthesis Integration contract.\n";
