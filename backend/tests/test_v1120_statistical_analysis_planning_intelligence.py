import asyncio
from fastapi.testclient import TestClient
from app.contracts.statistical_analysis_planning_intelligence import *
from app.services.statistical_analysis_planning_intelligence import StatisticalAnalysisPlanningIntelligenceStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeProtocols:
    def get(self,pid):
        if pid!='protocol-1': raise ValueError('missing')
        return {
            'study_protocol_id':'protocol-1','record_hash':'protocol-hash','research_program_id':'prog-1','core_project_id':'core-1',
            'registration':{'status':'preregistered','baseline_snapshot_hash':'baseline-hash'},
            'hypotheses':[{'hypothesis_id':'h1','statement':'Treatment changes outcome'}],
            'outcomes':[{'outcome_id':'o1','label':'Primary','measure':'score'}],
            'variables':[{'variable_id':'v1','name':'treatment'},{'variable_id':'v2','name':'score'}],
            'sampling_plan':{'population':'Adults','target_sample_size':200},
            'analysis_commitments':[{'commitment_id':'c1','label':'Primary model','computational_plan_id':'comp-1'}],
        }

def make_store(tmp_path): return StatisticalAnalysisPlanningIntelligenceStore(tmp_path/'statplan.sqlite3',study_protocol_store=FakeProtocols())
def make_plan(s): return s.create(StatisticalAnalysisPlanningCreateRequest(actor_ref='lead',title='Primary SAP',plan_ref='sap-2026',study_protocol_id='protocol-1'))
def populate(s,pid):
    e=s.add_estimand(pid,StatisticalEstimandAddRequest(actor_ref='statistician',label='ATE',estimand_type='average-treatment-effect',population='Eligible adults',treatment_or_exposure='Treatment',comparator='Control',outcome='Primary score',time_horizon='12 weeks',protocol_hypothesis_ids=['h1'],protocol_outcome_ids=['o1'],protocol_variable_ids=['v1','v2']))['estimands'][0]
    m=s.add_model_specification(pid,StatisticalModelSpecificationAddRequest(actor_ref='statistician',label='Primary linear model',estimand_ids=[e['estimand_id']],model_family='linear',method='OLS with prespecified covariate adjustment',outcome_variable_refs=['v2'],predictor_variable_refs=['v1']))['model_specifications'][0]
    a=s.add_assumption_check(pid,StatisticalAssumptionCheckAddRequest(actor_ref='statistician',label='Residual diagnostics',model_specification_ids=[m['model_specification_id']],assumption='Residual model adequacy',planned_diagnostic='Inspect residual-vs-fitted and Q-Q diagnostics',response_if_challenged='Use prespecified robust interval sensitivity analysis'))['assumption_checks'][0]
    r=s.add_reporting_commitment(pid,StatisticalReportingCommitmentAddRequest(actor_ref='statistician',label='Primary reporting',content='Report point estimate, uncertainty interval, sample analyzed, diagnostics, and deviations.',required_outputs=['estimate','95% interval','diagnostics'],effect_size_reporting='Report raw-scale effect size.'))['reporting_commitments'][0]
    return e,m,a,r

def test_create_inherits_preregistered_protocol_lineage_and_guardrails(tmp_path):
    s=make_store(tmp_path); rec=make_plan(s)
    assert rec['schema']==STATISTICAL_ANALYSIS_PLANNING_SCHEMA and rec['protocol_fingerprint']=='protocol-hash'
    assert rec['preregistration_baseline_snapshot_hash']=='baseline-hash' and rec['computational_plan_id']=='comp-1'
    assert rec['governance']['preregistered_protocol_lineage_is_inherited_not_rewritten'] is True and rec['governance']['automatic_significance_inference'] is False

def test_estimands_models_assumptions_and_reporting_are_idempotent(tmp_path):
    s=make_store(tmp_path); pid=make_plan(s)['statistical_analysis_plan_id']; e,m,a,r=populate(s,pid)
    s.add_estimand(pid,StatisticalEstimandAddRequest(actor_ref='statistician',label='ATE',estimand_type='average-treatment-effect',population='Eligible adults',treatment_or_exposure='Treatment',comparator='Control',outcome='Primary score',time_horizon='12 weeks',protocol_hypothesis_ids=['h1'],protocol_outcome_ids=['o1'],protocol_variable_ids=['v1','v2']))
    rec=s.get(pid); assert len(rec['estimands'])==1 and len(rec['model_specifications'])==1 and len(rec['assumption_checks'])==1 and len(rec['reporting_commitments'])==1
    assert rec['model_specifications'][0]['fit_not_executed'] is True

def test_invalid_protocol_references_fail_closed(tmp_path):
    s=make_store(tmp_path); pid=make_plan(s)['statistical_analysis_plan_id']
    try: s.add_estimand(pid,StatisticalEstimandAddRequest(actor_ref='x',label='Bad',population='P',outcome='Y',protocol_hypothesis_ids=['missing']))
    except ValueError as exc: assert 'unknown protocol_hypothesis_id' in str(exc)
    else: raise AssertionError('unknown protocol reference should fail closed')

def test_power_multiplicity_missingness_and_sensitivity_are_plans_not_execution(tmp_path):
    s=make_store(tmp_path); pid=make_plan(s)['statistical_analysis_plan_id']; e,m,_,_=populate(s,pid)
    rec=s.set_power_sample_size_plan(pid,StatisticalPowerSampleSizePlanRequest(actor_ref='statistician',target_sample_size=200,effect_size_basis='Protocol target',alpha_or_error_rate='0.05',target_power='0.80',calculation_artifact_ref='artifact:power-1'))
    rec=s.set_multiplicity_plan(pid,StatisticalMultiplicityPlanRequest(actor_ref='statistician',family='family-wise-error',hypothesis_or_estimand_ids=[e['estimand_id']],procedure='Holm'))
    rec=s.set_missing_data_plan(pid,StatisticalMissingDataPlanRequest(actor_ref='statistician',strategy='multiple-imputation',variables_or_outcomes=['v2'],missingness_assumptions=['MAR as working assumption'],implementation='Prespecified chained equations',diagnostics=['missingness patterns']))
    rec=s.add_sensitivity_analysis(pid,StatisticalSensitivityAnalysisAddRequest(actor_ref='statistician',label='Robust interval',sensitivity_type='robustness',target_model_specification_ids=[m['model_specification_id']],analysis='HC3 robust standard errors',interpretation_boundary='Sensitivity only; primary estimand unchanged.'))
    assert rec['power_sample_size_plan']['calculation_not_performed_by_librarian'] is True
    assert rec['missing_data_plan']['imputation_or_weighting_not_executed'] is True and rec['sensitivity_analyses'][0]['analysis_not_executed'] is True

def test_human_model_approval_controls_readiness(tmp_path):
    s=make_store(tmp_path); pid=make_plan(s)['statistical_analysis_plan_id']; _,m,_,_=populate(s,pid)
    assert 'model-specifications-await-human-approval' in s.readiness(pid)['blockers']
    s.decide(pid,StatisticalAnalysisDecisionRequest(actor_ref='reviewer',object_type='model-specification',object_id=m['model_specification_id'],decision='approved',rationale='Prospectively specified.'))
    assert s.readiness(pid)['ready_for_statistical_handoff'] is True

def test_runtime_handoff_uses_existing_v811_bridge_without_execution(tmp_path):
    s=make_store(tmp_path); pid=make_plan(s)['statistical_analysis_plan_id']; _,m,_,_=populate(s,pid)
    s.decide(pid,StatisticalAnalysisDecisionRequest(actor_ref='reviewer',object_type='model-specification',object_id=m['model_specification_id'],decision='approved'))
    hand=s.runtime_handoffs(pid); assert len(hand['packets'])==1
    p=hand['packets'][0]; assert p['target']=='statistical-analysis-plan' and p['existing_statistical_research_bridge']=='v8.11'
    assert p['execution_performed'] is False and p['method_selection_performed'] is False and p['significance_inference_performed'] is False

def test_core_candidate_and_snapshot_never_promote_results(tmp_path):
    s=make_store(tmp_path); pid=make_plan(s)['statistical_analysis_plan_id']; _,m,_,_=populate(s,pid)
    s.decide(pid,StatisticalAnalysisDecisionRequest(actor_ref='reviewer',object_type='model-specification',object_id=m['model_specification_id'],decision='approved'))
    cand=s.core_candidate(pid); assert cand['object_type']=='statistical-analysis-plan' and cand['promotion_performed'] is False and cand['execution_performed'] is False
    snap=s.freeze_snapshot(StatisticalAnalysisPlanningSnapshotRequest(actor_ref='reviewer',statistical_analysis_plan_id=pid)); assert snap['schema']==STATISTICAL_ANALYSIS_PLANNING_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); pid=make_plan(s)['statistical_analysis_plan_id']; assert 'statistical-analysis-planning-intelligence-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_statistical_analysis_planning_intelligence_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1120',job_type='statistical-analysis-planning-intelligence-snapshot',payload={'snapshot':{'actor_ref':'lead','statistical_analysis_plan_id':pid}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==STATISTICAL_ANALYSIS_PLANNING_SNAPSHOT_SCHEMA and events[-1]==('statistical-analysis-planning-intelligence-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/statistical-analysis-planning-intelligence/capabilities','/v1/core/statistical-analysis-planning-intelligence/plans','/v1/core/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/analysis-matrix','/v1/core/statistical-analysis-planning-intelligence/plans/{statistical_analysis_plan_id}/runtime-handoffs','/v1/core/statistical-analysis-planning-intelligence/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); status=client.get('/v1/core/statistical-analysis-planning-intelligence/capabilities').status_code; assert status in {401,503}
    ok=client.get('/v1/core/statistical-analysis-planning-intelligence/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_significance_inference'] is False

def test_unified_environment_accepts_statistical_analysis_plan_binding(tmp_path):
    s=make_store(tmp_path); pid=make_plan(s)['statistical_analysis_plan_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',statistical_analysis_planning_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='lead',title='Unified',project_ref='p',statistical_analysis_plan_ids=[pid]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['statistical_analysis_plans'])==1 and ready['dimensions']['statistical_analysis_plan_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['milestone']=='11.2' and cap['human_statistical_approval_required'] is True
    assert cap['existing_statistical_research_layer_remains_runtime_core_bridge'] is True and cap['specialist_runtimes_own_statistical_execution'] is True
    assert cap['automatic_method_selection'] is False and cap['automatic_model_selection'] is False and cap['automatic_power_calculation'] is False
    assert cap['automatic_significance_inference'] is False and cap['automatic_causality_inference'] is False and cap['automatic_result_interpretation'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
