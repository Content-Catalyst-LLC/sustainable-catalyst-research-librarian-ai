<?php
$root=dirname(__DIR__);

$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$wp=file_get_contents($root.'/includes/class-sc-rl-v1207-wordpress-state-migration-compatibility.php');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$backend_api=file_get_contents($root.'/backend/app/api/wordpress_migration.py');
$backend_service=file_get_contents($root.'/backend/app/services/wordpress_state_migration.py');
$backend_contract=file_get_contents($root.'/backend/app/contracts/wordpress_state_migration.py');
$migration=file_get_contents($root.'/backend/migrations/040_wordpress_state_migration_compatibility.sql');
$session_service=file_get_contents($root.'/backend/app/services/persistent_research_session_conversation.py');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.2.0')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.2.0';")!==false,
 'adapter_required'=>strpos($main,'class-sc-rl-v1207-wordpress-state-migration-compatibility.php')!==false,
 'adapter_initialized'=>strpos($main,'SC_RL_V1207_WordPress_State_Migration_Compatibility::init();')!==false,

 'wp_contract'=>strpos($wp,'sc-research-librarian-wordpress-state-migration/1.0')!==false,
 'wp_manifest_route'=>strpos($wp,"'/state-migration'")!==false,
 'wp_inventory_route'=>strpos($wp,"'/state-migration/inventory'")!==false,
 'wp_prepare_route'=>strpos($wp,"'/state-migration/prepare'")!==false,
 'wp_apply_route'=>strpos($wp,"/apply'")!==false,
 'wp_resolve_route'=>strpos($wp,"'/state-migration/resolve'")!==false,
 'wp_admin_capability'=>strpos($wp,"current_user_can( 'manage_options' )")!==false,
 'wp_read_capability'=>strpos($wp,"current_user_can( 'read' )")!==false,
 'wp_nonce'=>strpos($wp,'wp_verify_nonce( $nonce, \'wp_rest\' )')!==false,
 'wp_explicit_confirmation'=>strpos($wp,'\'MIGRATE\' !== $confirmation')!==false,
 'wp_no_auto_migration'=>strpos($wp,"'automatic_migration'              => false")!==false,
 'wp_no_legacy_delete'=>strpos($wp,"'legacy_state_deleted'             => false")!==false,
 'wp_noncanonical'=>strpos($wp,"'wordpress_canonical_state'        => false")!==false,
 'wp_secret_filter'=>strpos($wp,'private static function is_secret_name')!==false,
 'wp_secret_export_false'=>strpos($wp,"'secret_fields_exported'           => false")!==false,
 'wp_option_prefix'=>strpos($wp,"sc_rl_")!==false,
 'wp_long_prefix'=>strpos($wp,"sc_research_librarian_")!==false,
 'wp_user_meta_inventory'=>strpos($wp,'$wpdb->usermeta')!==false,
 'wp_option_inventory'=>strpos($wp,'$wpdb->options')!==false,
 'wp_fixed_migration_path'=>strpos($wp,"#^/v1/research-librarian/wordpress-migration(?:/|$)#")!==false,
 'wp_server_key'=>strpos($wp,"'X-SC-RL-Key'")!==false,
 'wp_no_redirects'=>strpos($wp,"'redirection' => 0")!==false,
 'wp_no_update_option'=>strpos($wp,'update_option(')===false,
 'wp_no_delete_option'=>strpos($wp,'delete_option(')===false,
 'wp_no_delete_user_meta'=>strpos($wp,'delete_user_meta(')===false,
 'wp_no_transient'=>strpos($wp,'set_transient(')===false,
 'wp_compat_resolver'=>strpos($wp,'resolve_legacy_reference')!==false,
 'wp_compat_does_not_authorize'=>strpos($wp,"'compatibility_aliases_authorize'  => false")!==false,

 'backend_router'=>strpos($backend_main,'wordpress_state_migration_router')!==false,
 'backend_health'=>strpos($backend_main,'"wordpress_state_migration": True')!==false,
 'backend_manifest_route'=>strpos($backend_api,'/manifest')!==false,
 'backend_prepare_route'=>strpos($backend_api,'/prepare')!==false,
 'backend_apply_route'=>strpos($backend_api,'/runs/{run_id}/apply')!==false,
 'backend_resolve_route'=>strpos($backend_api,'/resolve')!==false,
 'backend_admin_access'=>strpos($backend_api,'require_admin_access')!==false,

 'service_prepare_apply'=>strpos($backend_service,'"migration_mode":"explicit-prepare-apply"')!==false,
 'service_no_auto'=>strpos($backend_service,'"automatic_migration":False')!==false,
 'service_receipts'=>strpos($backend_service,'WORDPRESS_MIGRATION_RECEIPT_SCHEMA')!==false,
 'service_aliases'=>strpos($backend_service,'WORDPRESS_COMPATIBILITY_ALIAS_SCHEMA')!==false,
 'service_conflict_closed'=>strpos($backend_service,'"conflicts_fail_closed":True')!==false,
 'service_secret_block'=>strpos($backend_service,'blocked-secret-bearing')!==false,
 'service_owner_map'=>strpos($backend_service,'blocked-owner-map')!==false,
 'service_deterministic_target'=>strpos($backend_service,'_canonical_target_id')!==false,
 'service_legacy_preserved'=>strpos($backend_service,'"legacy_state_deleted":False')!==false,
 'service_alias_no_access'=>strpos($backend_service,'"alias_grants_access":False')!==false,

 'contract_types'=>strpos($backend_contract,'MigrationSourceType')!==false,
 'contract_prepare'=>strpos($backend_contract,'WordPressMigrationPrepareRequest')!==false,
 'contract_apply'=>strpos($backend_contract,'WordPressMigrationApplyRequest')!==false,
 'contract_resolve'=>strpos($backend_contract,'WordPressCompatibilityResolveRequest')!==false,

 'migration_runs'=>strpos($migration,'sc_rl_wordpress_migration_runs')!==false,
 'migration_candidates'=>strpos($migration,'sc_rl_wordpress_migration_candidates')!==false,
 'migration_receipts'=>strpos($migration,'sc_rl_wordpress_migration_receipts')!==false,
 'migration_aliases'=>strpos($migration,'sc_rl_wordpress_compatibility_aliases')!==false,
 'migration_unique_alias'=>strpos($migration,'UNIQUE(source_site,source_type,legacy_id)')!==false,

 'idempotent_turn_id'=>strpos($session_service,'requested_turn_id')!==false,
];

foreach($checks as $label=>$ok){
    if(!$ok){
        fwrite(STDERR,"FAIL: $label\n");
        exit(1);
    }
}
echo "PASS: Research Librarian v12.0.7 WordPress State Migration & Compatibility Layer contract.\n";
