<?php
/** Static release contract checks for Research Librarian AI v7.0.2. */
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$module=file_get_contents($root.'/includes/class-sc-rl-v700-connected-platform.php');
$backend=file_get_contents($root.'/backend/app/main.py');
$service=file_get_contents($root.'/backend/app/platform_v7.py');
$adapter=file_get_contents($root.'/backend/app/generation_adapter.py');
$store=file_get_contents($root.'/backend/app/store.py');
$models=file_get_contents($root.'/backend/app/models.py');
$js=file_get_contents($root.'/assets/sc-research-platform-v7.js');
$css=file_get_contents($root.'/assets/sc-research-librarian-ai.css');
$docs=file_get_contents($root.'/docs/V700_CONNECTED_RESEARCH_INTELLIGENCE_PLATFORM.md');
$manifest=json_decode(file_get_contents($root.'/data/research_librarian_connected_platform_manifest_v7.0.2.json'),true);
$checks=array(
 'version_header'=>false!==strpos($main,'Version: 7.0.2'),
 'version_constant'=>false!==strpos($main,"const VERSION        = '7.0.2';"),
 'backend_version'=>false!==strpos(file_get_contents($root.'/backend/app/__init__.py'),'__version__ = "7.0.2"'),
 'module_loaded'=>false!==strpos($main,'class-sc-rl-v700-connected-platform.php'),
 'module_initialized'=>false!==strpos($main,'SC_RL6_V700_Connected_Platform::init()'),
 'activation'=>false!==strpos($main,"SC_RL6_V700_Connected_Platform', 'activate"),
 'module_version'=>false!==strpos($module,"const VERSION = '7.0.2';"),
 'schema_ten'=>false!==strpos($store,'SCHEMA_VERSION = 10'),
 'index_ten'=>false!==strpos($store,'sc-research-librarian-knowledge-index/10.0'),
 'project_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS research_projects'),
 'investigation_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS research_investigations'),
 'entity_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS research_project_entities'),
 'event_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS research_project_events'),
 'backup_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS connected_platform_backups'),
 'project_model'=>false!==strpos($models,'class ResearchProjectRequest'),
 'investigation_model'=>false!==strpos($models,'class ResearchInvestigationRequest'),
 'entity_model'=>false!==strpos($models,'class ProjectEntityRequest'),
 'backup_model'=>false!==strpos($models,'class PlatformBackupImportRequest'),
 'api_contract'=>false!==strpos($service,'sc-connected-research-api/1.0'),
 'project_contract'=>false!==strpos($service,'sc-research-project/1.0'),
 'investigation_contract'=>false!==strpos($service,'sc-research-investigation/1.0'),
 'workflow_contract'=>false!==strpos($service,'sc-research-workflow/1.0'),
 'uncertainty_contract'=>false!==strpos($service,'sc-uncertainty-register/1.0'),
 'backup_contract'=>false!==strpos($service,'sc-connected-research-backup/1.0'),
 'project_endpoint'=>false!==strpos($backend,'@app.post("/v1/projects"'),
 'bundle_endpoint'=>false!==strpos($backend,'@app.get("/v1/projects/{project_id}"'),
 'investigation_endpoint'=>false!==strpos($backend,'@app.post("/v1/investigations"'),
 'entity_endpoint'=>false!==strpos($backend,'@app.post("/v1/projects/entities"'),
 'workflow_endpoint'=>false!==strpos($backend,'@app.post("/v1/workflows/template"'),
 'contradiction_endpoint'=>false!==strpos($backend,'@app.post("/v1/research/contradictions"'),
 'uncertainty_endpoint'=>false!==strpos($backend,'@app.post("/v1/research/uncertainties"'),
 'backup_endpoint'=>false!==strpos($backend,'@app.post("/v1/projects/{project_id}/backup"'),
 'backup_import'=>false!==strpos($backend,'@app.post("/v1/platform/backups/import"'),
 'stable_api'=>false!==strpos($backend,'@app.get("/v1/platform/api"'),
 'workspace_two'=>false!==strpos($backend,'sc-research-librarian-public-workspace/2.0'),
 'generation_boundary'=>false!==strpos($adapter,'sc-generation-adapter/1.0')&&false!==strpos($backend,'adapter_status()'),
 'project_shortcode'=>false!==strpos($module,'sc_connected_research_workspace'),
 'summary_shortcode'=>false!==strpos($module,'sc_research_projects_summary'),
 'status_shortcode'=>false!==strpos($module,'sc_connected_research_platform_status'),
 'wordpress_project_route'=>false!==strpos($module,"'/platform/v7/projects'"),
 'wordpress_backup_route'=>false!==strpos($module,"'/platform/v7/projects/(?P<project_id>[A-Za-z0-9._-]+)/backup'"),
 'nonce_check'=>false!==strpos($module,'wp_verify_nonce( $nonce, \'wp_rest\' )'),
 'private_default'=>false!==strpos($module,"'default_visibility' => 'private'"),
 'human_review'=>false!==strpos($module,"'human_publication_review' => '1'"),
 'project_ui'=>false!==strpos($js,'data-sc-rl-v7-projects')&&false!==strpos($js,'Export backup'),
 'responsive_css'=>false!==strpos($css,'.sc-rl-v7-layout')&&false!==strpos($css,'@media(max-width:900px)'),
 'reduced_motion'=>false!==strpos($css,'prefers-reduced-motion'),
 'forced_colors'=>false!==strpos($css,'forced-colors'),
 'manifest_version'=>is_array($manifest)&&'7.0.2'===($manifest['version']??''),
 'manifest_schema'=>is_array($manifest)&&10===($manifest['sqlite_schema']??0),
 'free_first'=>is_array($manifest)&&false===($manifest['paid_infrastructure_required']??true),
 'docs'=>false!==strpos($docs,'Connected Research Intelligence Platform'),
);
$failed=array_keys(array_filter($checks,function($ok){return !$ok;}));
echo json_encode(array('version'=>'7.0.2','checks'=>$checks,'passed'=>count($checks)-count($failed),'failed'=>count($failed),'failures'=>$failed),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES).PHP_EOL;
exit($failed?1:0);
