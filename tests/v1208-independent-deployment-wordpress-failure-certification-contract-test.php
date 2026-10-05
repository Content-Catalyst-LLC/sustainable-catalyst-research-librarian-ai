<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$wp=file_get_contents($root.'/includes/class-sc-rl-v1208-independent-deployment-certification.php');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$backend_api=file_get_contents($root.'/backend/app/api/independence.py');
$backend_service=file_get_contents($root.'/backend/app/services/independent_deployment_certification.py');
$backend_contract=file_get_contents($root.'/backend/app/contracts/independent_deployment_certification.py');

$checks=[
 'plugin_version'=>strpos($main,'Version: 12.2.0')!==false,
 'plugin_constant'=>strpos($main,"const VERSION        = '12.2.0';")!==false,
 'module_required'=>strpos($main,'class-sc-rl-v1208-independent-deployment-certification.php')!==false,
 'module_initialized'=>strpos($main,'SC_RL_V1208_Independent_Deployment_Certification::init();')!==false,

 'wp_contract'=>strpos($wp,'sc-research-librarian-independent-deployment-certification/1.0')!==false,
 'wp_route'=>strpos($wp,"'/independent-certification'")!==false,
 'wp_optional'=>strpos($wp,"'wordpress_optional'           => true")!==false,
 'wp_not_runtime_authority'=>strpos($wp,"'wordpress_runtime_authority'  => false")!==false,
 'wp_not_identity_authority'=>strpos($wp,"'wordpress_identity_authority' => false")!==false,
 'wp_not_session_authority'=>strpos($wp,"'wordpress_session_authority'  => false")!==false,
 'wp_not_canonical'=>strpos($wp,"'wordpress_canonical_state'    => false")!==false,
 'wp_no_proxy'=>strpos($wp,"'wordpress_proxies_report'     => false")!==false,
 'wp_no_credentials'=>strpos($wp,"'wordpress_holds_credentials'  => false")!==false,
 'wp_next_boundary'=>strpos($wp,"'next_boundary'                => 'neural-research-intelligence-foundation'")!==false,
 'wp_no_remote_request'=>strpos($wp,'wp_remote_')===false,
 'wp_no_option_write'=>strpos($wp,'update_option(')===false,
 'wp_no_user_meta_write'=>strpos($wp,'update_user_meta(')===false,

 'backend_router'=>strpos($backend_main,'independent_deployment_certification_router')!==false,
 'backend_health_flag'=>strpos($backend_main,'"independent_deployment_certification": True')!==false,
 'backend_failure_runtime'=>strpos($backend_main,'"wordpress_failure_certification_runtime": "12.0.8"')!==false,

 'backend_api_prefix'=>strpos($backend_api,'prefix="/v1/research-librarian/independence"')!==false,
 'backend_manifest_route'=>strpos($backend_api,'@router.get("/manifest")')!==false,
 'backend_report_route'=>strpos($backend_api,'@router.get("/report")')!==false,
 'backend_report_auth'=>strpos($backend_api,'require_independent_access')!==false,

 'service_manifest'=>strpos($backend_service,'def certification_manifest()')!==false,
 'service_report'=>strpos($backend_service,'def certification_report(')!==false,
 'service_target'=>strpos($backend_service,'"certification_target":"wordpress-unreachable-or-absent"')!==false,
 'service_wp_false'=>strpos($backend_service,'"wordpress_required":False')!==false,
 'service_dns_blackout'=>strpos($backend_service,'"wordpress_dns_blackout_probe":True')!==false,
 'service_no_state_mod'=>strpos($backend_service,'"research_state_modified":False')!==false,
 'service_fingerprint'=>strpos($backend_service,'"certificate_fingerprint"')!==false,
 'service_route_surface'=>strpos($backend_service,'REQUIRED_INDEPENDENT_ROUTES')!==false,
 'service_next_boundary'=>strpos($backend_service,'"next_boundary":"neural-research-intelligence-foundation"')!==false,

 'contract_schema'=>strpos($backend_contract,'INDEPENDENT_DEPLOYMENT_CERTIFICATION_SCHEMA')!==false,
 'contract_report'=>strpos($backend_contract,'INDEPENDENT_DEPLOYMENT_REPORT_SCHEMA')!==false,
];

foreach($checks as $label=>$ok){
    if(!$ok){
        fwrite(STDERR,"FAIL: $label\n");
        exit(1);
    }
}
echo "PASS: Research Librarian v12.0.8 Independent Deployment & WordPress-Failure Certification contract.\n";
