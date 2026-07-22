<?php
$root = dirname(__DIR__);
$module = file_get_contents($root . '/includes/class-sc-rl-v630-durable-index.php');
$checks = array(
 'version' => false !== strpos($module, "const VERSION = '7.1.2'"),
 'bounded_stage' => false !== strpos($module, "'finalizing-discovery'"),
 'bounded_processor' => false !== strpos($module, 'process_build_finalization_step'),
 'cursor_saved' => false !== strpos($module, "'finalization_offset'"),
 'legacy_skipped_default' => false !== strpos($module, "'migrate_legacy' => false"),
 'no_finalize_full_scan' => false === strpos(substr($module, strpos($module, 'private static function finalize_build_discovery'), 2500), 'scan_build_file'),
 'ledger_reuses_finalization' => false !== strpos($module, "finalization_hashes"),
 'admin_validation_metrics' => false !== strpos($module, 'Staging file'),
);
foreach ($checks as $name => $pass) { if (!$pass) { fwrite(STDERR, "FAIL: $name\n"); exit(1); } }
echo "v7.1.2 bounded finalization contract passed (" . count($checks) . " checks).\n";
