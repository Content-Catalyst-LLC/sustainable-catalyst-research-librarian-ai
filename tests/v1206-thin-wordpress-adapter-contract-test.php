<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$adapter=file_get_contents($root.'/includes/class-sc-rl-v1206-thin-wordpress-adapter.php');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$backend_api=file_get_contents($root.'/backend/app/api/wordpress_adapter.py');
$backend_service=file_get_contents($root.'/backend/app/services/thin_wordpress_adapter.py');
$backend_contract=file_get_contents($root.'/backend/app/contracts/thin_wordpress_adapter.py');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.0.8')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.0.8';")!==false,
 'adapter_required'=>strpos($main,'class-sc-rl-v1206-thin-wordpress-adapter.php')!==false,
 'adapter_initialized'=>strpos($main,'SC_RL_V1206_Thin_WordPress_Adapter::init();')!==false,
 'contract_v2'=>strpos($adapter,"sc-research-librarian-wordpress-thin-adapter/2.0")!==false,
 'manifest_route'=>strpos($adapter,"'/thin-adapter'")!==false,
 'status_route'=>strpos($adapter,"'/thin-adapter/status'")!==false,
 'proxy_route'=>strpos($adapter,"'/thin-adapter/proxy'")!==false,
 'cookie_auth'=>strpos($adapter,'is_user_logged_in()')!==false,
 'read_capability'=>strpos($adapter,"current_user_can( 'read' )")!==false,
 'write_capability'=>strpos($adapter,"current_user_can( 'edit_posts' )")!==false,
 'nonce_header'=>strpos($adapter,"x_wp_nonce")!==false,
 'nonce_verification'=>strpos($adapter,'wp_verify_nonce( $nonce, \'wp_rest\' )')!==false,
 'fixed_read_operations'=>strpos($adapter,'private static function read_operations()')!==false,
 'fixed_write_operations'=>strpos($adapter,'private static function write_operations()')!==false,
 'no_arbitrary_path_param'=>strpos($adapter,'$body[\'path\']')===false,
 'no_arbitrary_host_param'=>strpos($adapter,'$body[\'host\']')===false,
 'no_arbitrary_url_param'=>strpos($adapter,'$body[\'url\']')===false,
 'upstream_prefix_guard'=>strpos($adapter,"#^/(health|v1/research-librarian(?:/|$))#")!==false,
 'no_redirect_follow'=>strpos($adapter,"'redirection' => 0")!==false,
 'server_integration_key'=>strpos($adapter,"'X-SC-RL-Key'")!==false,
 'key_never_manifested'=>strpos($adapter,"'backend_key_exposed'          => false")!==false,
 'actor_context'=>strpos($adapter,"X-SC-RL-WP-Actor")!==false,
 'actor_not_identity'=>strpos($adapter,"provenance-hint-not-backend-identity")!==false,
 'fail_closed'=>strpos($adapter,"fail-closed-no-wordpress-research-fallback")!==false,
 'no_canonical_storage'=>strpos($adapter,"wordpress_canonical_state")!==false,
 'no_update_option'=>strpos($adapter,'update_option(')===false,
 'no_add_option'=>strpos($adapter,'add_option(')===false,
 'no_transient_storage'=>strpos($adapter,'set_transient(')===false,
 'backend_router'=>strpos($backend_main,'thin_wordpress_adapter_router')!==false,
 'backend_health'=>strpos($backend_main,'"thin_wordpress_adapter": True')!==false,
 'backend_manifest_route'=>strpos($backend_api,'/manifest')!==false,
 'backend_capabilities_route'=>strpos($backend_api,'/capabilities')!==false,
 'backend_wordpress_false'=>strpos($backend_service,'"wordpress_required": False')!==false,
 'backend_authoritative'=>strpos($backend_service,'"backend_authoritative": True')!==false,
 'backend_fixed_allowlist'=>strpos($backend_service,'"fixed_operation_allowlist": True')!==false,
 'contract_read_ops'=>strpos($backend_contract,'READ_OPERATIONS')!==false,
 'contract_write_ops'=>strpos($backend_contract,'WRITE_OPERATIONS')!==false,
];

foreach($checks as $label=>$ok){
    if(!$ok){
        fwrite(STDERR,"FAIL: $label\n");
        exit(1);
    }
}
echo "PASS: Research Librarian v12.0.6 Thin WordPress Adapter contract.\n";
