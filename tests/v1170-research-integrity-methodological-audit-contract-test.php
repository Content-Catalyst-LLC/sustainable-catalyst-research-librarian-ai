<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$core = file_get_contents($root . '/backend/app/api/core.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$service = file_get_contents($root . '/backend/app/services/research_integrity_methodological_audit.py');
$unified = file_get_contents($root . '/backend/app/services/unified_scholarly_ai_environment.py');
$assertions = [
    'plugin version' => strpos($main, 'Version: 12.0.7') !== false,
    'plugin constant' => strpos($main, "const VERSION        = '12.0.7';") !== false,
    'integrity audit API' => strpos($core, '/research-integrity-methodological-audit/audits/{audit_id}/verification-handoffs') !== false,
    'snapshot job' => strpos($jobs, 'research-integrity-methodological-audit-snapshot') !== false,
    'misconduct guardrail' => preg_match('/automatic_misconduct_inference.*False/', $service) === 1,
    'invalidity guardrail' => preg_match('/automatic_invalidity_verdict.*False/', $service) === 1,
    'methodological scoring guardrail' => preg_match('/automatic_methodological_scoring.*False/', $service) === 1,
    'truth guardrail' => preg_match('/automatic_truth_promotion.*False/', $service) === 1,
    'unified binding' => strpos($unified, 'research-integrity-audit') !== false,
];
foreach ($assertions as $label => $ok) { if (!$ok) { fwrite(STDERR, "FAIL: $label\n"); exit(1); } }
echo "PASS: Research Librarian v11.7.0 research integrity/methodological audit contract.\n";
