<?php
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$backend=file_get_contents($root.'/backend/app/main.py');
$store=file_get_contents($root.'/backend/app/store.py');
$models=file_get_contents($root.'/backend/app/models.py');
$lifecycle=file_get_contents($root.'/backend/app/research_lifecycle.py');
$module=file_get_contents($root.'/includes/class-sc-rl-v700-connected-platform.php');
$js=file_get_contents($root.'/assets/sc-research-platform-v800-lifecycle.js');
$css=file_get_contents($root.'/assets/sc-research-librarian-ai.css');
$state=file_get_contents($root.'/backend/app/research_state.py');
$docs=file_get_contents($root.'/docs/V800_UNIFIED_RESEARCH_INTELLIGENCE_LIFECYCLE.md');
$readme=file_get_contents($root.'/README.md');
$manifest=json_decode(file_get_contents($root.'/data/research_librarian_unified_lifecycle_manifest_v8.0.0.json'),true);
$v770=json_decode(file_get_contents($root.'/data/research_librarian_federated_discovery_manifest_v7.7.0.json'),true);
$migrations=glob($root.'/backend/migrations/*.sql');
$checks=array(
 'version_header'=>false!==strpos($main,'Version: 9.6.0'),
 'version_constant'=>false!==strpos($main,"const VERSION        = '9.6.0';"),
 'backend_version'=>false!==strpos(file_get_contents($root.'/backend/app/__init__.py'),'__version__ = "9.6.0"'),
 'module_version'=>false!==strpos($module,"const VERSION = '8.0.0';"),
 'api_20'=>false!==strpos($module,'sc-connected-research-api/2.0') && false!==strpos(file_get_contents($root.'/backend/app/platform_v7.py'),'sc-connected-research-api/2.0'),
 'workspace_30'=>false!==strpos($module,'sc-research-librarian-public-workspace/3.0') && false!==strpos($backend,'sc-research-librarian-public-workspace/3.0'),
 'sqlite_18'=>false!==strpos($store,'SCHEMA_VERSION = 19'),
 'knowledge_index_13'=>false!==strpos($store,'sc-research-librarian-knowledge-index/13.0'),
 'no_postgres_migration'=>is_file($root.'/backend/migrations/004_async_document_processing_runtime.sql'),
 'lifecycle_module'=>file_exists($root.'/backend/app/research_lifecycle.py'),
 'lifecycle_schema'=>false!==strpos($lifecycle,'sc-research-lifecycle/1.0'),
 'summary_schema'=>false!==strpos($lifecycle,'sc-research-lifecycle-summary/1.0'),
 'event_schema'=>false!==strpos($lifecycle,'sc-research-lifecycle-event/1.0'),
 'checkpoint_schema'=>false!==strpos($lifecycle,'sc-research-lifecycle-checkpoint/1.0'),
 'frame_stage'=>false!==strpos($lifecycle,'"stage": "frame"'),
 'discover_stage'=>false!==strpos($lifecycle,'"stage": "discover"'),
 'evaluate_stage'=>false!==strpos($lifecycle,'"stage": "evaluate"'),
 'organize_stage'=>false!==strpos($lifecycle,'"stage": "organize"'),
 'collaborate_stage'=>false!==strpos($lifecycle,'"stage": "collaborate"'),
 'synthesize_stage'=>false!==strpos($lifecycle,'"stage": "synthesize"'),
 'promote_stage'=>false!==strpos($lifecycle,'"stage": "promote"'),
 'preserve_stage'=>false!==strpos($lifecycle,'"stage": "preserve"'),
 'human_confirmed'=>false!==strpos($lifecycle,'"human_confirmed_transitions": True'),
 'no_auto_advance'=>false!==strpos($lifecycle,'"automatic_stage_advancement": False'),
 'not_evidence'=>false!==strpos($lifecycle,'"not_evidence": True'),
 'not_truth'=>false!==strpos($lifecycle,'"not_truth_judgment": True'),
 'transition_confirmation'=>false!==strpos($lifecycle,'Lifecycle stage transitions require explicit human confirmation.'),
 'checkpoint_fingerprint'=>false!==strpos($lifecycle,'body["fingerprint"] = fingerprint'),
 'request_lifecycle'=>false!==strpos($models,'class ResearchLifecycleRequest'),
 'request_transition'=>false!==strpos($models,'class ResearchLifecycleTransitionRequest'),
 'request_checkpoint'=>false!==strpos($models,'class ResearchLifecycleCheckpointRequest'),
 'lifecycle_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS research_lifecycles'),
 'event_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS research_lifecycle_events'),
 'checkpoint_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS research_lifecycle_checkpoints'),
 'save_lifecycle'=>false!==strpos($store,'def save_research_lifecycle('),
 'list_lifecycles'=>false!==strpos($store,'def research_lifecycles('),
 'save_event'=>false!==strpos($store,'def save_lifecycle_event('),
 'save_checkpoint'=>false!==strpos($store,'def save_lifecycle_checkpoint('),
 'backup_lifecycle'=>false!==strpos($store,'"research_lifecycles":lifecycle_bundles'),
 'import_lifecycle'=>false!==strpos($backend,'for lifecycle_bundle in body.get("research_lifecycles") or []:'),
 'catalog_endpoint'=>false!==strpos($backend,'@app.get("/v1/research/lifecycle/catalog"'),
 'list_endpoint'=>false!==strpos($backend,'@app.get("/v1/research/lifecycles"'),
 'save_endpoint'=>false!==strpos($backend,'@app.post("/v1/research/lifecycles"'),
 'detail_endpoint'=>false!==strpos($backend,'@app.get("/v1/research/lifecycles/{lifecycle_id}"'),
 'summary_endpoint'=>false!==strpos($backend,'@app.get("/v1/research/lifecycles/{lifecycle_id}/summary"'),
 'transition_endpoint'=>false!==strpos($backend,'@app.post("/v1/research/lifecycles/{lifecycle_id}/transition"'),
 'checkpoint_endpoint'=>false!==strpos($backend,'@app.post("/v1/research/lifecycles/{lifecycle_id}/checkpoint"'),
 'owner_boundary'=>false!==strpos($backend,'Research lifecycle does not belong to this owner.'),
 'actor_boundary'=>false!==strpos($backend,'Lifecycle transition actor must match the authenticated lifecycle owner'),
 'activity_transition'=>false!==strpos($state,'"lifecycle-stage-transition"'),
 'activity_checkpoint'=>false!==strpos($state,'"lifecycle-checkpoint"'),
 'wp_lifecycle_schema'=>false!==strpos($module,"const LIFECYCLE_SCHEMA = 'sc-research-lifecycle/1.0';"),
 'wp_capability'=>false!==strpos($module,"'research_lifecycle_orchestration' => '1'"),
 'wp_catalog_route'=>false!==strpos($module,"'/platform/v7/lifecycle/catalog'"),
 'wp_lifecycle_route'=>false!==strpos($module,"'/platform/v7/lifecycles'"),
 'wp_transition_route'=>false!==strpos($module,"/transition'"),
 'wp_checkpoint_route'=>false!==strpos($module,"/checkpoint'"),
 'wp_owner_server_side'=>false!==strpos($module,"'owner_ref' => self::owner_ref()"),
 'wp_actor_server_side'=>false!==strpos($module,"'actor_ref' => self::owner_ref()"),
 'wp_context_auth'=>false!==strpos($module,'self::authorized_context( $context_id )'),
 'wp_project_auth'=>false!==strpos($module,'self::authorized_project( $project_id, false )'),
 'wp_room_auth'=>false!==strpos($module,'self::authorized_room( $room_id, false, false )'),
 'wp_asset'=>false!==strpos($module,'sc-research-platform-v800-lifecycle.js'),
 'wp_button'=>false!==strpos($module,'data-sc-rl-v800-lifecycle-run>Research lifecycle'),
 'wp_panel'=>false!==strpos($module,'data-sc-rl-v800-lifecycle-panel'),
 'js_stage_order'=>false!==strpos($js,"['frame', 'discover', 'evaluate', 'organize', 'collaborate', 'synthesize', 'promote', 'preserve']"),
 'js_readiness'=>false!==strpos($js,'stage_readiness'),
 'js_confirmation'=>false!==strpos($js,'window.confirm'),
 'js_transition'=>false!==strpos($js,"/transition"),
 'js_checkpoint'=>false!==strpos($js,"/checkpoint"),
 'js_boundary'=>false!==strpos($js,'not evidence, a truth score, editorial approval, or publication'),
 'css_panel'=>false!==strpos($css,'.sc-rl-v800-lifecycle-panel'),
 'css_stage'=>false!==strpos($css,'.sc-rl-v800-stage'),
 'css_current'=>false!==strpos($css,'.sc-rl-v800-stage.is-current'),
 'manifest_version'=>is_array($manifest)&&'8.0.0'===($manifest['version']??''),
 'manifest_api'=>is_array($manifest)&&'sc-connected-research-api/2.0'===($manifest['api_schema']??''),
 'manifest_workspace'=>is_array($manifest)&&'sc-research-librarian-public-workspace/3.0'===($manifest['workspace_schema']??''),
 'manifest_sqlite'=>is_array($manifest)&&18===($manifest['storage']['ancillary_sqlite_schema_version']??0),
 'manifest_no_neon'=>is_array($manifest)&&false===($manifest['storage']['new_postgres_migration_required']??true),
 'manifest_human'=>is_array($manifest)&&true===($manifest['orchestration']['human_confirmed_transitions']??false),
 'manifest_no_auto'=>is_array($manifest)&&false===($manifest['orchestration']['automatic_stage_advancement']??true),
 'manifest_backup'=>is_array($manifest)&&true===($manifest['orchestration']['project_backup_includes_lifecycle_lineage']??false),
 'manifest_not_evidence'=>is_array($manifest)&&true===($manifest['governance']['lifecycle_state_is_not_evidence']??false),
 'v770_preserved'=>is_array($v770)&&'7.7.0'===($v770['version']??'')&&17===($v770['storage']['ancillary_sqlite_schema_version']??0),
 'docs_no_auto'=>false!==strpos($docs,'system never advances a lifecycle stage automatically'),
 'docs_no_neon'=>false!==strpos($docs,'No Neon/Postgres knowledge-index migration is required for v8.0.0'),
 'docs_compat_namespace'=>false!==strpos($docs,'`/platform/v7/` REST route namespace is intentionally retained'),
 'readme_v8'=>false!==strpos($readme,'# Sustainable Catalyst Research Librarian AI v9.6.0'),
);
$failed=array_keys(array_filter($checks,static function($v){return !$v;}));
echo json_encode(array('version'=>'8.0.0','checks'=>$checks,'passed'=>count($checks)-count($failed),'failed'=>count($failed),'failures'=>$failed),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES).PHP_EOL;
exit($failed?1:0);
