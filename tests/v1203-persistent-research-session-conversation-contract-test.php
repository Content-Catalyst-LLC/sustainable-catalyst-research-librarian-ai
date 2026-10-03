<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$adapter=file_get_contents($root.'/includes/class-sc-rl-v1203-persistent-session-adapter.php');
$independent=file_get_contents($root.'/backend/app/api/independent.py');
$service=file_get_contents($root.'/backend/app/services/persistent_research_session_conversation.py');
$backend_main=file_get_contents($root.'/backend/app/main.py');
$checks=[
 'plugin version'=>strpos($main,'Version: 12.0.3')!==false,
 'plugin constant'=>strpos($main,"const VERSION        = '12.0.3';")!==false,
 'adapter required'=>strpos($main,'class-sc-rl-v1203-persistent-session-adapter.php')!==false,
 'adapter initialized'=>strpos($main,'SC_RL_V1203_Persistent_Session_Adapter::init();')!==false,
 'session api'=>strpos($independent,'@router.post("/sessions"')!==false,
 'turn api'=>strpos($independent,'/sessions/{session_id}/turns')!==false,
 'snapshot api'=>strpos($independent,'/sessions/{session_id}/snapshots/freeze')!==false,
 'postgres sessions'=>strpos($service,'sc_rl_persistent_research_sessions')!==false,
 'turn hash chain'=>strpos($service,'previous_turn_hash')!==false,
 'client ref not identity'=>strpos($service,'"client_ref_is_identity": False')!==false,
 'legacy ask persistent store'=>strpos($backend_main,'persistent_session_store.history_for_generation')!==false,
 'legacy in-memory append removed'=>strpos($backend_main,'_sessions[session_id].extend')===false,
];
foreach($checks as $label=>$ok){if(!$ok){fwrite(STDERR,"FAIL: $label\\n");exit(1);}}
echo "PASS: Research Librarian v12.0.3 Persistent Research Session & Conversation Runtime contract.\\n";
