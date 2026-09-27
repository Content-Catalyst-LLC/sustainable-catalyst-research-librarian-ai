import asyncio
from fastapi.testclient import TestClient
from app.contracts.simulation_model_study_planner import *
from app.services.simulation_model_study_planner import SimulationModelStudyPlannerStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeCausal:
    def get(self,cid):
        if cid!='causal-1': raise ValueError('missing')
        return {'causal_design_id':'causal-1','record_hash':'causal-hash','statistical_analysis_plan_id':'stat-1','study_protocol_id':'protocol-1','research_program_id':'prog-1','core_project_id':'core-1','variable_roles':[{'causal_role_id':'r1','role':'treatment'},{'causal_role_id':'r2','role':'outcome'}],'identification_strategies':[{'identification_strategy_id':'id1','strategy':'backdoor-adjustment'}],'causal_assumptions':[{'causal_assumption_id':'a1','statement':'exchangeability'}]}

def make_store(tmp_path): return SimulationModelStudyPlannerStore(tmp_path/'sim.sqlite3',causal_design_store=FakeCausal())
def make_study(s): return s.create(SimulationModelStudyCreateRequest(actor_ref='lead',title='Policy system simulation',study_ref='sim-2026',causal_design_id='causal-1'))
def populate(s,sid):
    m=s.add_model_specification(sid,SimulationModelSpecificationAddRequest(actor_ref='lead',label='System dynamics baseline',model_class='system-dynamics',purpose='Explore dynamic response under prespecified scenarios.',equations_or_rules_ref='model/system-v1',preferred_runtime='research-lab',assumptions=['closed population']))['model_specifications'][0]
    v=s.add_variable(sid,SimulationVariableAddRequest(actor_ref='lead',variable_ref='stock-carbon',label='Carbon stock',kind='state',units='MtCO2e',definition='Modeled stock.'))['variables'][0]
    p=s.add_parameter(sid,SimulationParameterAddRequest(actor_ref='lead',parameter_ref='decay-rate',label='Decay rate',role='sampled',units='1/year',baseline_value='0.05',plausible_range='0.02-0.10'))['parameters'][0]
    sc=s.add_scenario_set(sid,SimulationScenarioSetAddRequest(actor_ref='lead',label='Policy scenarios',model_specification_ids=[m['model_specification_id']],scenarios=[{'scenario':'baseline','policy':0},{'scenario':'intervention','policy':1}],comparison_basis='Compare identical horizon and initial conditions.'))['scenario_sets'][0]
    val=s.add_validation_plan(sid,SimulationValidationPlanAddRequest(actor_ref='lead',label='Historical validation',model_specification_ids=[m['model_specification_id']],validation_type='historical',dataset_refs=['dataset-1'],metrics=['RMSE'],acceptance_criteria=['RMSE documented before interpretation']))['validation_plans'][0]
    return m,v,p,sc,val

def test_create_inherits_causal_and_program_lineage(tmp_path):
    s=make_store(tmp_path); rec=make_study(s)
    assert rec['schema']==SIMULATION_MODEL_STUDY_SCHEMA and rec['causal_design_fingerprint']=='causal-hash'
    assert rec['statistical_analysis_plan_id']=='stat-1' and rec['research_program_id']=='prog-1'
    assert rec['governance']['causal_design_lineage_is_inherited_not_rewritten'] is True and rec['governance']['automatic_simulation_execution'] is False

def test_model_variables_parameters_and_scenarios_are_idempotent(tmp_path):
    s=make_store(tmp_path); sid=make_study(s)['simulation_study_id']; m,v,p,sc,val=populate(s,sid)
    s.add_model_specification(sid,SimulationModelSpecificationAddRequest(actor_ref='lead',label='System dynamics baseline',model_class='system-dynamics',purpose='Explore dynamic response under prespecified scenarios.',equations_or_rules_ref='model/system-v1',preferred_runtime='research-lab',assumptions=['closed population']))
    rec=s.get(sid); assert len(rec['model_specifications'])==1 and len(rec['variables'])==1 and len(rec['parameters'])==1 and len(rec['scenario_sets'])==1
    assert rec['model_specifications'][0]['model_not_selected_automatically'] is True and rec['scenario_sets'][0]['scenario_results_not_computed'] is True

def test_unknown_upstream_model_and_parameter_references_fail_closed(tmp_path):
    s=make_store(tmp_path)
    try: s.create(SimulationModelStudyCreateRequest(actor_ref='x',title='Bad',study_ref='bad',causal_design_id='missing'))
    except ValueError as exc: assert 'causal_design_id' in str(exc)
    else: raise AssertionError('unknown causal design should fail closed')
    sid=make_study(s)['simulation_study_id']
    try: s.add_scenario_set(sid,SimulationScenarioSetAddRequest(actor_ref='x',label='Bad',model_specification_ids=['missing'],scenarios=[{'x':1}],comparison_basis='same'))
    except ValueError as exc: assert 'model_specification_id' in str(exc)
    else: raise AssertionError('unknown model should fail closed')
    try: s.add_sensitivity_plan(sid,SimulationSensitivityPlanAddRequest(actor_ref='x',label='Bad',method='sobol',parameter_ids=['missing'],procedure='run'))
    except ValueError as exc: assert 'simulation_parameter_id' in str(exc)
    else: raise AssertionError('unknown parameter should fail closed')

def test_calibration_validation_uncertainty_and_sensitivity_are_plans_not_results(tmp_path):
    s=make_store(tmp_path); sid=make_study(s)['simulation_study_id']; m,_,p,_,_=populate(s,sid)
    cal=s.add_calibration_plan(sid,SimulationCalibrationPlanAddRequest(actor_ref='lead',label='Bayesian calibration',model_specification_ids=[m['model_specification_id']],method='bayesian',target_refs=['obs-1'],dataset_refs=['dataset-1'],objective_or_likelihood='Prespecified likelihood.'))
    s.add_stochastic_assumption(sid,SimulationStochasticAssumptionAddRequest(actor_ref='lead',label='Parameter uncertainty',target_ref=p['simulation_parameter_id'],distribution_family='beta',distribution_parameters={'alpha':2,'beta':5}))
    s.add_uncertainty_plan(sid,SimulationUncertaintyPlanAddRequest(actor_ref='lead',label='Monte Carlo propagation',uncertainty_type='parameter',target_refs=[p['simulation_parameter_id']],procedure='Sample prespecified distributions.',sample_count=1000))
    rec=s.add_sensitivity_plan(sid,SimulationSensitivityPlanAddRequest(actor_ref='lead',label='Sobol sensitivity',method='sobol',parameter_ids=[p['simulation_parameter_id']],output_refs=['net-outcome'],procedure='Estimate first-order and total-order indices.'))
    assert cal['calibration_plans'][0]['calibration_not_executed'] is True and rec['validation_plans'][0]['validation_not_executed'] is True
    assert rec['uncertainty_plans'][0]['uncertainty_not_computed'] is True and rec['sensitivity_plans'][0]['sensitivity_not_computed'] is True

def test_ensemble_compute_budget_stopping_and_outputs(tmp_path):
    s=make_store(tmp_path); sid=make_study(s)['simulation_study_id']; m1,_,_,_,_=populate(s,sid)
    m2=s.add_model_specification(sid,SimulationModelSpecificationAddRequest(actor_ref='lead',label='Agent-based alternative',model_class='agent-based',purpose='Alternative structural representation.'))['model_specifications'][1]
    ens=s.add_ensemble_plan(sid,SimulationEnsemblePlanAddRequest(actor_ref='lead',label='Structural ensemble',model_specification_ids=[m1['model_specification_id'],m2['model_specification_id']],method='equal-weight'))
    s.set_compute_budget(sid,SimulationComputeBudgetRequest(actor_ref='lead',max_runs=5000,max_wall_time_minutes=120,max_memory_gb=16,parallelism_limit=8))
    s.add_stopping_criterion(sid,SimulationStoppingCriterionAddRequest(actor_ref='lead',label='Monte Carlo precision',criterion='Stop after budget or when prespecified Monte Carlo SE threshold is met.'))
    rec=s.add_output_commitment(sid,SimulationOutputCommitmentAddRequest(actor_ref='lead',label='Primary modeled outcome',output_ref='net-outcome',summary_or_metric='Mean and 95% simulation interval'))
    assert ens['ensemble_plans'][0]['ensemble_not_executed'] is True and rec['compute_budget']['max_runs']==5000
    assert len(rec['stopping_criteria'])==1 and rec['output_commitments'][0]['result_not_computed'] is True

def test_human_model_approval_controls_readiness_and_runtime_handoff(tmp_path):
    s=make_store(tmp_path); sid=make_study(s)['simulation_study_id']; m,_,_,_,_=populate(s,sid)
    s.set_compute_budget(sid,SimulationComputeBudgetRequest(actor_ref='lead',max_runs=1000))
    s.add_output_commitment(sid,SimulationOutputCommitmentAddRequest(actor_ref='lead',label='Outcome',output_ref='y',summary_or_metric='distribution'))
    assert 'model-specifications-await-human-approval' in s.readiness(sid)['blockers']
    s.decide(sid,SimulationStudyDecisionRequest(actor_ref='reviewer',object_type='model-specification',object_id=m['model_specification_id'],decision='approved',rationale='Model purpose and assumptions are explicit.'))
    assert s.readiness(sid)['ready_for_simulation_handoff'] is True
    p=s.runtime_handoffs(sid)['packets'][0]; assert p['target']=='research-lab-simulation' and 'workspace' in p['secondary_targets']
    assert p['execution_performed'] is False and p['validation_performed'] is False and p['model_output_accepted_as_empirical_truth'] is False

def test_study_matrix_execution_graph_core_candidate_and_snapshot(tmp_path):
    s=make_store(tmp_path); sid=make_study(s)['simulation_study_id']; m,_,_,_,_=populate(s,sid)
    s.decide(sid,SimulationStudyDecisionRequest(actor_ref='reviewer',object_type='model-specification',object_id=m['model_specification_id'],decision='approved'))
    matrix=s.study_matrix(sid); graph=s.execution_graph(sid); cand=s.core_candidate(sid); snap=s.freeze_snapshot(SimulationModelStudySnapshotRequest(actor_ref='reviewer',simulation_study_id=sid))
    assert matrix['models'][0]['decision']=='approved' and graph['execution_performed'] is False
    assert cand['object_type']=='simulation-model-study' and cand['execution_performed'] is False and cand['model_validity_certified'] is False
    assert snap['schema']==SIMULATION_MODEL_STUDY_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); sid=make_study(s)['simulation_study_id']; assert 'simulation-model-study-planner-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_simulation_model_study_planner_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1140',job_type='simulation-model-study-planner-snapshot',payload={'snapshot':{'actor_ref':'lead','simulation_study_id':sid}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==SIMULATION_MODEL_STUDY_SNAPSHOT_SCHEMA and events[-1]==('simulation-model-study-planner-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/simulation-model-study-planner/capabilities','/v1/core/simulation-model-study-planner/studies','/v1/core/simulation-model-study-planner/studies/{simulation_study_id}/study-matrix','/v1/core/simulation-model-study-planner/studies/{simulation_study_id}/runtime-handoffs','/v1/core/simulation-model-study-planner/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); status=client.get('/v1/core/simulation-model-study-planner/capabilities').status_code; assert status in {401,503}
    ok=client.get('/v1/core/simulation-model-study-planner/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_simulation_execution'] is False

def test_unified_environment_accepts_simulation_model_study_binding(tmp_path):
    s=make_store(tmp_path); sid=make_study(s)['simulation_study_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',simulation_model_study_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='lead',title='Unified',project_ref='p',simulation_model_study_ids=[sid]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['simulation_model_studies'])==1 and ready['dimensions']['simulation_model_study_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['milestone']=='11.4' and cap['human_model_study_approval_required'] is True
    assert cap['uncertainty_planning'] is True and cap['sensitivity_planning'] is True and cap['ensemble_planning'] is True
    assert cap['specialist_runtimes_own_simulation_execution'] is True and cap['platform_core_remains_governed_model_object_authority'] is True
    assert cap['automatic_model_selection'] is False and cap['automatic_calibration'] is False and cap['automatic_validation'] is False
    assert cap['automatic_simulation_execution'] is False and cap['automatic_forecast_acceptance'] is False and cap['automatic_causal_inference'] is False and cap['automatic_truth_promotion'] is False
