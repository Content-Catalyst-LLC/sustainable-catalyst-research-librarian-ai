<?php
$root = dirname(__DIR__);
$main = file_get_contents($root . '/sustainable-catalyst-research-librarian-ai.php');
$config = file_get_contents($root . '/backend/app/config.py');
$client = file_get_contents($root . '/backend/app/clients/platform_core.py');
$service = file_get_contents($root . '/backend/app/services/platform_core_integration.py');
$api = file_get_contents($root . '/backend/app/api/core.py');
$store = file_get_contents($root . '/backend/app/store.py');
$compose = file_get_contents($root . '/compose.yml');
$checks = array(
    'version_header' => false !== strpos($main, 'Version: 10.4.0'),
    'version_constant' => false !== strpos($main, "const VERSION        = '10.4.0';"),
    'backend_version' => false !== strpos(file_get_contents($root . '/backend/app/__init__.py'), '__version__ = "10.4.0"'),
    'sqlite_schema_19' => false !== strpos($store, 'SCHEMA_VERSION = 19'),
    'core_client' => false !== strpos($client, 'class PlatformCoreClient'),
    'core_private_write_header' => false !== strpos($client, 'X-SC-API-Key'),
    'core_compatibility' => false !== strpos($client, 'CORE_MINIMUM_VERSION'),
    'core_bindings' => false !== strpos($store, 'platform_core_bindings'),
    'core_readiness_route' => false !== strpos($api, '/readiness'),
    'core_project_sync_route' => false !== strpos($api, '/research-projects/synchronize'),
    'core_object_promotion_route' => false !== strpos($api, '/research-objects/promote'),
    'deterministic_core_ids' => false !== strpos($service, '_core_entity_id'),
    'no_auto_truth_promotion' => false !== strpos($api, 'automatic_truth_promotion') && false !== strpos($api, 'False'),
    'vps_core_dns' => false !== strpos($compose, 'http://sc-core:8090'),
    'core_enabled_setting' => false !== strpos($config, 'SC_RL_CORE_ENABLED'),
);
$failed = array_keys(array_filter($checks, static fn($ok) => !$ok));
if ($failed) {
    fwrite(STDERR, 'FAIL: ' . implode(', ', $failed) . PHP_EOL);
    exit(1);
}
echo 'PASS: Research Librarian v8.4.0 Python service architecture + Platform Core client contract.' . PHP_EOL;
