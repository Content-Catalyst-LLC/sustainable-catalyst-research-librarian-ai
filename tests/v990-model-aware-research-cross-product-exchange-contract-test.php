<?php
$root = dirname(__DIR__);
$required = [
    'backend/app/contracts/model_aware_exchange.py',
    'backend/app/services/model_aware_exchange.py',
    'backend/tests/test_v990_model_aware_exchange.py',
    'backend/migrations/014_model_aware_research_cross_product_exchange.sql',
    'data/research_librarian_model_aware_exchange_manifest_v9.9.0.json',
    'docs/V990_MODEL_AWARE_RESEARCH_INTELLIGENCE_CROSS_PRODUCT_EXCHANGE.md',
];
foreach ($required as $rel) {
    if (!file_exists($root . '/' . $rel)) { fwrite(STDERR, "Missing v9.9 file: $rel\n"); exit(1); }
}
$core = file_get_contents($root . '/backend/app/api/core.py');
$jobs = file_get_contents($root . '/backend/app/async_jobs.py');
$svc = file_get_contents($root . '/backend/app/services/model_aware_exchange.py');
foreach ([
    '/model-aware-research/capabilities',
    '/model-aware-research/records/{record_id}/lineage',
    '/cross-product-exchange/exchanges',
    '/cross-product-exchange/exchanges/{exchange_id}/receipts',
    '/model-aware-research/snapshots/freeze',
] as $route) {
    if (strpos($core, $route) === false) { fwrite(STDERR, "Missing v9.9 route: $route\n"); exit(1); }
}
if (strpos($jobs, 'model-aware-research-snapshot') === false) { fwrite(STDERR, "Missing v9.9 durable job\n"); exit(1); }
foreach (['automatic_delivery":False','automatic_model_selection":False','destination_acceptance_requires_receipt":True'] as $guard) {
    if (strpos(str_replace(' ', '', $svc), $guard) === false) { fwrite(STDERR, "Missing v9.9 guardrail: $guard\n"); exit(1); }
}
echo "PASS: Research Librarian v9.9 model-aware research and cross-product exchange contract\n";
