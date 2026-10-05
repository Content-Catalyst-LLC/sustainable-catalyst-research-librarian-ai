<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$auth=file_get_contents($root.'/backend/app/api/auth.py');
$access=file_get_contents($root.'/backend/app/services/identity_session_access.py');
$contract=file_get_contents($root.'/backend/app/contracts/identity_session_access.py');
$web=file_get_contents($root.'/backend/app/webapp/app.js');
$web_service=file_get_contents($root.'/backend/app/services/independent_web_app.py');
$migration=file_get_contents($root.'/backend/migrations/039_identity_session_access_runtime.sql');
$adapter=file_get_contents($root.'/includes/class-sc-rl-v1205-identity-session-access-adapter.php');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.1.0')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.1.0';")!==false,
 'adapter_required'=>strpos($main,'class-sc-rl-v1205-identity-session-access-adapter.php')!==false,
 'adapter_initialized'=>strpos($main,'SC_RL_V1205_Identity_Session_Access_Adapter::init();')!==false,
 'identity_schema'=>strpos($contract,'sc-research-librarian-identity/1.0')!==false,
 'session_schema'=>strpos($contract,'sc-research-librarian-auth-session/1.0')!==false,
 'scrypt'=>strpos($access,'hashlib.scrypt')!==false,
 'random_token'=>strpos($access,'secrets.token_urlsafe(48)')!==false,
 'token_hash'=>strpos($access,'sha256')!==false,
 'lockout'=>strpos($access,'identity_login_failure_limit')!==false,
 'cookie_http_only'=>strpos($auth,'httponly=True')!==false,
 'cookie_strict'=>strpos($auth,'samesite="strict"')!==false,
 'login_route'=>strpos($auth,'@router.post("/login")')!==false,
 'logout_route'=>strpos($auth,'@router.post("/logout")')!==false,
 'me_route'=>strpos($auth,'@router.get("/me")')!==false,
 'provision_route'=>strpos($auth,'@router.post("/provision")')!==false,
 'web_login'=>strpos($web,'"/auth/login"')!==false,
 'web_me'=>strpos($web,'"/auth/me"')!==false,
 'web_no_api_key'=>strpos($web,'X-SC-RL-Key')===false,
 'web_no_local_storage'=>strpos($web,'localStorage')===false,
 'web_identity_mode'=>strpos($web_service,'"mode": "backend-identity-session"')!==false,
 'web_wordpress_false'=>strpos($web_service,'"wordpress_required": False')!==false,
 'migration_identities'=>strpos($migration,'sc_rl_identities')!==false,
 'migration_sessions'=>strpos($migration,'sc_rl_identity_sessions')!==false,
 'wp_not_identity_authority'=>strpos($adapter,"'wordpress_identity_authority' => false")!==false,
];
foreach($checks as $label=>$ok){
    if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}
}
echo "PASS: Research Librarian v12.0.5 Identity, Session & Access Runtime contract.\n";
