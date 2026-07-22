<?php
/** Static release contract checks for Research Librarian AI v7.1.1. */
$root=dirname(__DIR__);
$main=file_get_contents($root.'/sustainable-catalyst-research-librarian-ai.php');
$module=file_get_contents($root.'/includes/class-sc-rl-v670-governance-center.php');
$backend=file_get_contents($root.'/backend/app/main.py');
$governance=file_get_contents($root.'/backend/app/governance.py');
$store=file_get_contents($root.'/backend/app/store.py');
$models=file_get_contents($root.'/backend/app/models.py');
$docs=file_get_contents($root.'/docs/V670_RESEARCH_QUALITY_GOVERNANCE_CENTER.md');
$manifest=json_decode(file_get_contents($root.'/data/research_librarian_quality_governance_manifest_v7.1.1.json'),true);
$checks=array(
 'version_header'=>false!==strpos($main,'Version: 7.1.1'),
 'version_constant'=>false!==strpos($main,"const VERSION        = '7.1.1';"),
 'module_loaded'=>false!==strpos($main,'class-sc-rl-v670-governance-center.php'),
 'module_version'=>false!==strpos($module,"const VERSION = '7.1.1';"),
 'activation'=>false!==strpos($main,"SC_RL6_V670_Governance_Center', 'activate"),
 'schema_nine'=>false!==strpos($store,'SCHEMA_VERSION = 12'),
 'index_nine'=>false!==strpos($store,'sc-research-librarian-knowledge-index/12.0'),
 'policy_contract'=>false!==strpos($governance,'sc-research-governance-policy/1.0'),
 'source_contract'=>false!==strpos($governance,'sc-research-source-review/1.0'),
 'trace_contract'=>false!==strpos($governance,'sc-research-answer-trace/1.0'),
 'evaluation_contract'=>false!==strpos($governance,'sc-research-quality-evaluation/1.0'),
 'release_gate_contract'=>false!==strpos($governance,'sc-research-release-gate/1.0'),
 'methodology_contract'=>false!==strpos($governance,'sc-research-methodology/1.0'),
 'policy_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS governance_policies'),
 'source_review_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS source_governance_reviews'),
 'trace_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS answer_traces'),
 'quality_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS quality_evaluations'),
 'gate_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS release_gate_runs'),
 'event_table'=>false!==strpos($store,'CREATE TABLE IF NOT EXISTS governance_events'),
 'policy_model'=>false!==strpos($models,'class GovernancePolicyUpdate'),
 'source_model'=>false!==strpos($models,'class SourceReviewRequest'),
 'gate_model'=>false!==strpos($models,'class ReleaseGateRequest'),
 'policy_endpoint'=>false!==strpos($backend,'@app.get("/v1/governance/policy"'),
 'source_endpoint'=>false!==strpos($backend,'@app.post("/v1/governance/sources"'),
 'trace_endpoint'=>false!==strpos($backend,'@app.get("/v1/governance/traces"'),
 'metrics_endpoint'=>false!==strpos($backend,'@app.get("/v1/governance/metrics"'),
 'gate_endpoint'=>false!==strpos($backend,'@app.post("/v1/governance/release-gate"'),
 'retention_endpoint'=>false!==strpos($backend,'@app.post("/v1/governance/retention/run"'),
 'methodology_endpoint'=>false!==strpos($backend,'@app.get("/v1/governance/methodology"'),
 'trace_in_ask'=>false!==strpos($backend,'build_answer_trace('),
 'privacy_default'=>false!==strpos($governance,'"store_query_text": False')&&false!==strpos($governance,'"store_answer_text": False'),
 'no_autopublish'=>false!==strpos($governance,'"allow_automatic_publication": False'),
 'human_override'=>false!==strpos($governance,'required_for_release_override'),
 'admin_page'=>false!==strpos($module,'Research Quality and Governance Center'),
 'methodology_shortcode'=>false!==strpos($module,'sc_research_librarian_methodology'),
 'status_shortcode'=>false!==strpos($module,'sc_research_librarian_governance_status'),
 'manifest_version'=>is_array($manifest)&&'7.1.1'===($manifest['version']??''),
 'docs'=>false!==strpos($docs,'Research Quality and Governance Center'),
);
$failed=array_keys(array_filter($checks,function($ok){return !$ok;}));
echo json_encode(array('version'=>'7.1.1','checks'=>$checks,'passed'=>count($checks)-count($failed),'failed'=>count($failed),'failures'=>$failed),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES).PHP_EOL;
exit($failed?1:0);
