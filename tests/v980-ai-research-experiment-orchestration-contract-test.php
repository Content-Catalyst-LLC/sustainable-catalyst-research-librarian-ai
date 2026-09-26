<?php
$root = dirname(__DIR__);
$required = [
    'backend/app/contracts/ai_research_experiment.py',
    'backend/app/services/ai_research_experiment.py',
    'backend/migrations/013_ai_research_experiment_orchestration.sql',
    'backend/tests/test_v980_ai_research_experiment.py',
];
foreach ($required as $file) {
    if (!is_file($root . '/' . $file)) { fwrite(STDERR, "Missing v10.7.0 file: $file\n"); exit(1); }
}
$core = file_get_contents($root . '/backend/app/api/core.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$service = file_get_contents($root . '/backend/app/services/ai_research_experiment.py');
foreach ([
    '/ai-research-experiments/capabilities',
    '/ai-research-experiments/experiments',
    '/execution-handoffs', '/run-receipts', '/evaluation-bindings', '/summary', '/state', '/snapshots/freeze'
] as $needle) {
    if (strpos($core, $needle) === false) { fwrite(STDERR, "Missing v9.8 route token: $needle\n"); exit(1); }
}
foreach (['ai-research-experiment-snapshot','automatic_best_model_selection','librarian_executes_training','external_runtime_executes','winner_selected'] as $needle) {
    if (strpos($jobs . $service, $needle) === false) { fwrite(STDERR, "Missing v9.8 governance/runtime token: $needle\n"); exit(1); }
}
echo "PASS: Research Librarian v10.7.0 AI Research Experiment Orchestration contract\n";
