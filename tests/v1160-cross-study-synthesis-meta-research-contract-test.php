<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$core = file_get_contents($root . '/backend/app/api/core.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$service = file_get_contents($root . '/backend/app/services/cross_study_synthesis_meta_research.py');
$unified = file_get_contents($root . '/backend/app/services/unified_scholarly_ai_environment.py');
$assertions = [
    'plugin version' => strpos($main, 'Version: 11.6.0') !== false,
    'plugin constant' => strpos($main, "const VERSION        = '11.6.0';") !== false,
    'cross-study API' => strpos($core, '/cross-study-synthesis-meta-research/projects/{cross_study_synthesis_id}/runtime-handoffs') !== false,
    'snapshot job' => strpos($jobs, 'cross-study-synthesis-meta-research-snapshot') !== false,
    'meta-analysis guardrail' => preg_match('/automatic_meta_analysis.*False/', $service) === 1,
    'truth guardrail' => preg_match('/automatic_truth_promotion.*False/', $service) === 1,
    'unified binding' => strpos($unified, 'cross-study-synthesis-plan') !== false,
];
foreach ($assertions as $label => $ok) { if (!$ok) { fwrite(STDERR, "FAIL: $label\n"); exit(1); } }
echo "PASS: Research Librarian v11.6.0 cross-study synthesis/meta-research contract.\n";
