<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$client = file_get_contents($root . '/backend/app/clients/platform_core.py');
$api = file_get_contents($root . '/backend/app/api/core.py');
$service = file_get_contents($root . '/backend/app/services/research_intelligence_extraction.py');
$contracts = file_get_contents($root . '/backend/app/contracts/research_intelligence_extraction.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$manifest = json_decode(file_get_contents($root . '/data/research_librarian_finding_claim_evidence_extraction_manifest_v8.9.0.json'), true);
$checks = [
  'version_header' => false !== strpos($main, 'Version: 10.3.0'),
  'version_constant' => false !== strpos($main, "const VERSION        = '10.3.0';"),
  'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "10.3.0"'),
  'schema' => false !== strpos($contracts, 'sc-research-librarian-finding-claim-evidence-extraction/1.0'),
  'core_contract' => false !== strpos($contracts, 'sc.research.finding-claim-evidence.v1'),
  'capability_route' => false !== strpos($api, '/research-intelligence/capabilities'),
  'extract_route' => false !== strpos($api, '/research-intelligence/extract'),
  'promote_route' => false !== strpos($api, '/research-intelligence/promote'),
  'core_readiness' => false !== strpos($client, '/v1/research/intelligence/readiness'),
  'project_state_readiness_fix' => false !== strpos($client, '"project_state": "/v1/research/project-state/readiness"'),
  'finding_client' => false !== strpos($client, '/findings'),
  'claim_client' => false !== strpos($client, '/claims'),
  'evidence_link_client' => false !== strpos($client, '/evidence-links'),
  'human_review_gate' => false !== strpos($contracts, "review_decision='approved'"),
  'default_contextualizes' => false !== strpos($service, '"contextualizes"'),
  'proposed_registration' => false !== strpos($service, '"status": "proposed"'),
  'no_truth' => false !== strpos($service, '"automated_truth_judgment": False'),
  'async_job' => false !== strpos($jobs, '"research-intelligence-extraction"'),
  'manifest_release' => isset($manifest['release']) && '8.9.0' === $manifest['release'],
  'manifest_review_gate' => true === ($manifest['capabilities']['human_review_required_for_core_promotion'] ?? false),
];
foreach ($checks as $name => $ok) { if (!$ok) { fwrite(STDERR, "FAIL: $name\n"); exit(1); } }
echo "PASS: Research Librarian v8.9.0 Finding, Claim & Evidence Extraction Pipeline contract.\n";
