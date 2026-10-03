<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$adapter=file_get_contents($root.'/includes/class-sc-rl-v1201-runtime-authority-adapter.php');
$core=file_get_contents($root.'/backend/app/api/core.py');
$service=file_get_contents($root.'/backend/app/services/runtime_authority_wordpress_decoupling.py');
$checks=[
 'plugin version'=>strpos($main,'Version: 12.0.4')!==false,
 'plugin constant'=>strpos($main,"const VERSION        = '12.0.4';")!==false,
 'adapter required'=>strpos($main,'class-sc-rl-v1201-runtime-authority-adapter.php')!==false,
 'adapter initialized'=>strpos($main,'SC_RL_V1201_Runtime_Authority_Adapter::init();')!==false,
 'adapter backend authority'=>strpos($adapter,"'backend_authoritative'       => true")!==false,
 'adapter wordpress false'=>strpos($adapter,"'wordpress_runtime_authority' => false")!==false,
 'manifest api'=>strpos($core,'/runtime-authority/manifest')!==false,
 'python authority'=>strpos($service,'"python_runtime_authoritative": True')!==false,
 'wordpress optional'=>strpos($service,'"wordpress_required_for_backend_boot": False')!==false,
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}}
echo "PASS: Research Librarian v12.0.1 runtime authority / WordPress decoupling contract.\n";
