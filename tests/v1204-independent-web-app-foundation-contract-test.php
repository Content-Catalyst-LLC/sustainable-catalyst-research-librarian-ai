<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$adapter=file_get_contents($root.'/includes/class-sc-rl-v1204-independent-web-app-adapter.php');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$web_router=file_get_contents($root.'/backend/app/api/webapp.py');
$web_service=file_get_contents($root.'/backend/app/services/independent_web_app.py');
$web_js=file_get_contents($root.'/backend/app/webapp/app.js');
$web_html=file_get_contents($root.'/backend/app/webapp/index.html');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.0.6')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.0.6';")!==false,
 'adapter_required'=>strpos($main,'class-sc-rl-v1204-independent-web-app-adapter.php')!==false,
 'adapter_initialized'=>strpos($main,'SC_RL_V1204_Independent_Web_App_Adapter::init();')!==false,
 'standalone_route'=>strpos($web_router,'/research-librarian/')!==false,
 'manifest_route'=>strpos($web_router,'app-manifest.json')!==false,
 'backend_router_registered'=>strpos($backend_main,'independent_web_app_router')!==false,
 'health_web_app'=>strpos($backend_main,'"independent_web_app": True')!==false,
 'wordpress_false'=>strpos($web_service,'"wordpress_required": False')!==false,
 'canonical_backend'=>strpos($web_service,'"canonical_state_location": "python-postgres-backend"')!==false,
 'no_local_storage'=>strpos($web_js,'localStorage')===false,
 'no_session_storage'=>strpos($web_js,'sessionStorage')===false,
 'no_embedded_backend_secret'=>strpos($web_js,'SC_RL_BACKEND_API_KEY')===false,
 'identity_login'=>strpos($web_js,'/auth/login')!==false && strpos($web_js,'X-SC-RL-Key')===false,
 'independent_api'=>strpos($web_html,'/v1/research-librarian')!==false,
 'persistent_sessions'=>strpos($web_js,'/sessions?limit=100')!==false,
 'retrieval'=>strpos($web_js,'"/retrieve"')!==false,
];
foreach($checks as $label=>$ok){
    if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}
}
echo "PASS: Research Librarian v12.0.4 Independent Web App Foundation contract.\n";
