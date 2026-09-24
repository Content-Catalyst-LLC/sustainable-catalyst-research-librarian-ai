<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$backend = file_get_contents($root . '/backend/app/async_jobs.py');
$worker = file_get_contents($root . '/backend/app/workers/document_worker.py');
$service = file_get_contents($root . '/backend/app/services/document_jobs.py');
$api = file_get_contents($root . '/backend/app/api/jobs.py');
$compose = file_get_contents($root . '/compose.yml');
$checks = array(
    'version_header' => false !== strpos($main, 'Version: 8.11.0'),
    'version_constant' => false !== strpos($main, "const VERSION        = '8.11.0';"),
    'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "8.11.0"'),
    'durable_job_table' => false !== strpos($backend, 'sc_rl_async_jobs'),
    'skip_locked' => false !== strpos($backend, 'FOR UPDATE SKIP LOCKED'),
    'lease_recovery' => false !== strpos($backend, 'lease_expires_utc'),
    'idempotency' => false !== strpos($backend, 'idempotency_key'),
    'worker_runtime' => false !== strpos($worker, 'DocumentWorker'),
    'document_pipeline' => false !== strpos($service, 'process_document_job'),
    'job_api' => false !== strpos($api, '/documents'),
    'compose_release' => false !== strpos($compose, '8.11.0'),
);
$failed = array_keys(array_filter($checks, fn($ok) => !$ok));
if ($failed) {
    fwrite(STDERR, 'Failed v8.4.0 contract checks: ' . implode(', ', $failed) . PHP_EOL);
    exit(1);
}
echo "Research Librarian v8.4.0 asynchronous ingestion/document-processing contract passed.\n";
