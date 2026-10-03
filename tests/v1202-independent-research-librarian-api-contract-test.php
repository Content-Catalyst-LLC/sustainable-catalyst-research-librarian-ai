<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$adapter=file_get_contents($root.'/includes/class-sc-rl-v1202-independent-api-adapter.php');
$api=file_get_contents($root.'/backend/app/api/independent.py');
$service=file_get_contents($root.'/backend/app/services/independent_research_librarian_api.py');
$contract=file_get_contents($root.'/backend/app/contracts/independent_research_librarian_api.py');
$checks=[
 'plugin version'=>strpos($main,'Version: 12.0.4')!==false,
 'plugin constant'=>strpos($main,"const VERSION        = '12.0.4';")!==false,
 'adapter required'=>strpos($main,'class-sc-rl-v1202-independent-api-adapter.php')!==false,
 'adapter initialized'=>strpos($main,'SC_RL_V1202_Independent_API_Adapter::init();')!==false,
 'api prefix'=>strpos($api,'prefix="/v1/research-librarian"')!==false,
 'api auth'=>strpos($api,'X-SC-RL-Key')!==false,
 'manifest route'=>strpos($api,'@router.get("/manifest"')!==false,
 'retrieve route'=>strpos($api,'@router.post("/retrieve"')!==false,
 'projects route'=>strpos($api,'@router.get("/projects"')!==false,
 'scientist route'=>strpos($api,'/scientist-environments/{scientist_environment_id}')!==false,
 'stable envelope'=>strpos($contract,'sc-research-librarian-independent-api-envelope/1.0')!==false,
 'wordpress false'=>strpos($service,'"wordpress_required":False')!==false,
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\n");exit(1);}}
echo "PASS: Research Librarian v12.0.2 Independent Research Librarian API v1 contract.\n";
