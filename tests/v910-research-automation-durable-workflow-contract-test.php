<?php
$root=dirname(__DIR__);
$checks=[
 'backend/app/contracts/research_workflow.py'=>'RESEARCH_WORKFLOW_SCHEMA',
 'backend/app/services/research_workflow.py'=>'class ResearchWorkflowStore',
 'backend/tests/test_v910_research_workflow.py'=>'test_safe_stage_enqueued_idempotently',
 'backend/migrations/006_research_workflow_automation.sql'=>'sc_rl_research_workflows',
];
foreach($checks as $f=>$needle){$p=$root.'/'.$f;if(!is_file($p)||strpos(file_get_contents($p),$needle)===false){fwrite(STDERR,"FAIL: $f\n");exit(1);}}
$core=file_get_contents($root.'/backend/app/api/core.py');foreach(['/research-workflows/capabilities','/research-workflows/{workflow_id}/advance','/research-workflows/{workflow_id}/approvals'] as $needle){if(strpos($core,$needle)===false){fwrite(STDERR,"FAIL route $needle\n");exit(1);}}
$jobs=file_get_contents($root.'/backend/app/async_jobs.py');if(strpos($jobs,'research-workflow-advance')===false){fwrite(STDERR,"FAIL workflow job\n");exit(1);}echo "PASS: Research Librarian v10.6.0 research automation durable workflow contract\n";
