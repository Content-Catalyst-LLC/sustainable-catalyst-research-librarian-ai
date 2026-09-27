import asyncio
from fastapi.testclient import TestClient
from app.contracts.causal_research_design_intelligence import *
from app.services.causal_research_design_intelligence import CausalResearchDesignIntelligenceStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeStatistics:
    def get(self,pid):
        if pid!='statplan-1': raise ValueError('missing')
        return {
            'statistical_analysis_plan_id':'statplan-1','record_hash':'statplan-hash','study_protocol_id':'protocol-1','research_program_id':'prog-1','core_project_id':'core-1',
            'preregistration_baseline_snapshot_hash':'baseline-hash',
            'estimands':[{'estimand_id':'e1','label':'ATE','outcome':'score'}],
            'model_specifications':[{'model_specification_id':'m1','label':'Adjusted outcome model','method':'OLS'}],
        }

def make_store(tmp_path): return CausalResearchDesignIntelligenceStore(tmp_path/'causal.sqlite3',statistical_analysis_store=FakeStatistics())
def make_design(s): return s.create(CausalResearchDesignCreateRequest(actor_ref='lead',title='Primary causal design',design_ref='causal-2026',statistical_analysis_plan_id='statplan-1'))
def populate(s,cid):
    tx=s.add_variable_role(cid,CausalVariableRoleAddRequest(actor_ref='lead',variable_ref='v-treatment',label='Treatment',role='treatment',temporal_position='baseline assignment'))['variable_roles'][0]
    y=s.add_variable_role(cid,CausalVariableRoleAddRequest(actor_ref='lead',variable_ref='v-outcome',label='Outcome',role='outcome',temporal_position='12 weeks'))['variable_roles'][1]
    c=s.add_variable_role(cid,CausalVariableRoleAddRequest(actor_ref='lead',variable_ref='v-age',label='Age',role='confounder',temporal_position='baseline'))['variable_roles'][2]
    s.add_edge(cid,CausalEdgeAddRequest(actor_ref='lead',source_role_id=c['causal_role_id'],target_role_id=tx['causal_role_id'],rationale='Age may influence treatment uptake'))
    s.add_edge(cid,CausalEdgeAddRequest(actor_ref='lead',source_role_id=c['causal_role_id'],target_role_id=y['causal_role_id'],rationale='Age may influence outcome'))
    s.add_edge(cid,CausalEdgeAddRequest(actor_ref='lead',source_role_id=tx['causal_role_id'],target_role_id=y['causal_role_id'],rationale='Target causal pathway'))
    a=s.add_assumption(cid,CausalAssumptionAddRequest(actor_ref='lead',label='Conditional exchangeability',assumption_type='exchangeability',statement='No unmeasured common causes after adjustment for age.',linked_role_ids=[tx['causal_role_id'],y['causal_role_id'],c['causal_role_id']],testability='untestable',threat_if_violated='Residual confounding'))['causal_assumptions'][0]
    st=s.add_identification_strategy(cid,CausalIdentificationStrategyAddRequest(actor_ref='lead',label='Backdoor adjustment',strategy='backdoor-adjustment',estimand_ids=['e1'],treatment_or_exposure_role_ids=[tx['causal_role_id']],outcome_role_ids=[y['causal_role_id']],adjustment_role_ids=[c['causal_role_id']],assumption_ids=[a['causal_assumption_id']],statistical_model_specification_ids=['m1'],identification_rationale='Adjust for the prespecified common cause.'))['identification_strategies'][0]
    d=s.add_diagnostic_plan(cid,CausalDiagnosticPlanAddRequest(actor_ref='lead',label='Overlap check',diagnostic_type='overlap',identification_strategy_ids=[st['identification_strategy_id']],procedure='Inspect propensity-score overlap before estimation.',interpretation_boundary='Poor overlap challenges positivity; it does not prove bias direction.'))['diagnostic_plans'][0]
    return tx,y,c,a,st,d

def test_create_inherits_statistical_plan_and_preregistration_lineage(tmp_path):
    s=make_store(tmp_path); rec=make_design(s)
    assert rec['schema']==CAUSAL_RESEARCH_DESIGN_SCHEMA and rec['statistical_analysis_plan_fingerprint']=='statplan-hash'
    assert rec['preregistration_baseline_snapshot_hash']=='baseline-hash' and rec['statistical_estimands'][0]['estimand_id']=='e1'
    assert rec['governance']['statistical_plan_lineage_is_inherited_not_rewritten'] is True and rec['governance']['automatic_causality_inference'] is False

def test_variable_roles_edges_assumptions_and_strategies_are_idempotent(tmp_path):
    s=make_store(tmp_path); cid=make_design(s)['causal_design_id']; tx,y,c,a,st,d=populate(s,cid)
    s.add_variable_role(cid,CausalVariableRoleAddRequest(actor_ref='lead',variable_ref='v-treatment',label='Treatment',role='treatment',temporal_position='baseline assignment'))
    rec=s.get(cid); assert len(rec['variable_roles'])==3 and len(rec['causal_edges'])==3 and len(rec['causal_assumptions'])==1 and len(rec['identification_strategies'])==1
    assert rec['identification_strategies'][0]['identification_not_established'] is True and rec['causal_assumptions'][0]['assumption_not_proven'] is True

def test_dag_rejects_unknown_roles_self_loops_and_cycles(tmp_path):
    s=make_store(tmp_path); cid=make_design(s)['causal_design_id']; tx,y,c,_,_,_=populate(s,cid)
    for req,needle in [
        (CausalEdgeAddRequest(actor_ref='x',source_role_id='missing',target_role_id=y['causal_role_id']), 'unknown causal_role_id'),
        (CausalEdgeAddRequest(actor_ref='x',source_role_id=tx['causal_role_id'],target_role_id=tx['causal_role_id']), 'self-loop'),
        (CausalEdgeAddRequest(actor_ref='x',source_role_id=y['causal_role_id'],target_role_id=c['causal_role_id']), 'directed cycle'),
    ]:
        try: s.add_edge(cid,req)
        except ValueError as exc: assert needle in str(exc)
        else: raise AssertionError('invalid DAG edge should fail closed')
    assert s.causal_graph(cid)['acyclic'] is True

def test_unknown_upstream_and_strategy_references_fail_closed(tmp_path):
    s=make_store(tmp_path)
    try: s.create(CausalResearchDesignCreateRequest(actor_ref='x',title='Bad',design_ref='bad',statistical_analysis_plan_id='missing'))
    except ValueError as exc: assert 'statistical_analysis_plan_id' in str(exc)
    else: raise AssertionError('missing statistical plan should fail closed')
    cid=make_design(s)['causal_design_id']; tx=s.add_variable_role(cid,CausalVariableRoleAddRequest(actor_ref='x',variable_ref='x',label='X',role='treatment'))['variable_roles'][0]
    y=s.add_variable_role(cid,CausalVariableRoleAddRequest(actor_ref='x',variable_ref='y',label='Y',role='outcome'))['variable_roles'][1]
    try: s.add_identification_strategy(cid,CausalIdentificationStrategyAddRequest(actor_ref='x',label='Bad',strategy='backdoor-adjustment',estimand_ids=['missing'],treatment_or_exposure_role_ids=[tx['causal_role_id']],outcome_role_ids=[y['causal_role_id']],identification_rationale='Bad reference'))
    except ValueError as exc: assert 'unknown estimand_id' in str(exc)
    else: raise AssertionError('unknown estimand should fail closed')

def test_negative_controls_sensitivity_and_diagnostics_are_plans_not_execution(tmp_path):
    s=make_store(tmp_path); cid=make_design(s)['causal_design_id']; _,_,_,a,st,d=populate(s,cid)
    n=s.add_negative_control_plan(cid,CausalNegativeControlPlanAddRequest(actor_ref='lead',label='Negative control outcome',control_type='outcome',identification_strategy_ids=[st['identification_strategy_id']],variable_or_period_ref='v-neg-outcome',rationale='Probe residual confounding.'))
    rec=s.add_sensitivity_plan(cid,CausalSensitivityPlanAddRequest(actor_ref='lead',label='Unmeasured confounding sensitivity',sensitivity_type='unmeasured-confounding',identification_strategy_ids=[st['identification_strategy_id']],procedure='Quantify effect strength needed to explain estimate.',target_assumption_ids=[a['causal_assumption_id']],interpretation_boundary='Sensitivity analysis does not identify hidden confounders.'))
    assert n['negative_control_plans'][0]['control_not_executed'] is True and rec['sensitivity_plans'][0]['sensitivity_not_executed'] is True
    assert rec['diagnostic_plans'][0]['diagnostic_not_executed'] is True

def test_human_strategy_approval_controls_readiness_and_handoff(tmp_path):
    s=make_store(tmp_path); cid=make_design(s)['causal_design_id']; _,_,_,_,st,_=populate(s,cid)
    assert 'identification-strategies-await-human-approval' in s.readiness(cid)['blockers']
    s.decide(cid,CausalDesignDecisionRequest(actor_ref='reviewer',object_type='identification-strategy',object_id=st['identification_strategy_id'],decision='approved',rationale='Design assumptions are explicit.'))
    assert s.readiness(cid)['ready_for_causal_handoff'] is True
    p=s.runtime_handoffs(cid)['packets'][0]; assert p['target']=='research-lab-causal-inference' and p['secondary_target']=='statistical-analysis-plan'
    assert p['execution_performed'] is False and p['identification_established'] is False and p['causality_inferred'] is False

def test_core_candidate_and_snapshot_never_promote_causal_results(tmp_path):
    s=make_store(tmp_path); cid=make_design(s)['causal_design_id']; _,_,_,_,st,_=populate(s,cid)
    s.decide(cid,CausalDesignDecisionRequest(actor_ref='reviewer',object_type='identification-strategy',object_id=st['identification_strategy_id'],decision='approved'))
    cand=s.core_candidate(cid); assert cand['object_type']=='causal-research-design' and cand['promotion_performed'] is False and cand['causality_inferred'] is False
    snap=s.freeze_snapshot(CausalResearchDesignSnapshotRequest(actor_ref='reviewer',causal_design_id=cid)); assert snap['schema']==CAUSAL_RESEARCH_DESIGN_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); cid=make_design(s)['causal_design_id']; assert 'causal-research-design-intelligence-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_causal_research_design_intelligence_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1130',job_type='causal-research-design-intelligence-snapshot',payload={'snapshot':{'actor_ref':'lead','causal_design_id':cid}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==CAUSAL_RESEARCH_DESIGN_SNAPSHOT_SCHEMA and events[-1]==('causal-research-design-intelligence-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/causal-research-design-intelligence/capabilities','/v1/core/causal-research-design-intelligence/designs','/v1/core/causal-research-design-intelligence/designs/{causal_design_id}/causal-graph','/v1/core/causal-research-design-intelligence/designs/{causal_design_id}/runtime-handoffs','/v1/core/causal-research-design-intelligence/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); status=client.get('/v1/core/causal-research-design-intelligence/capabilities').status_code; assert status in {401,503}
    ok=client.get('/v1/core/causal-research-design-intelligence/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_causality_inference'] is False

def test_unified_environment_accepts_causal_research_design_binding(tmp_path):
    s=make_store(tmp_path); cid=make_design(s)['causal_design_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',causal_research_design_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='lead',title='Unified',project_ref='p',causal_research_design_ids=[cid]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['causal_research_designs'])==1 and ready['dimensions']['causal_research_design_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['milestone']=='11.3' and cap['human_causal_design_approval_required'] is True
    assert cap['research_lab_and_specialist_runtimes_own_causal_execution'] is True and cap['platform_core_remains_governed_causal_object_authority'] is True
    assert cap['automatic_causal_identification'] is False and cap['automatic_adjustment_set_selection'] is False and cap['automatic_instrument_validation'] is False
    assert cap['automatic_causal_estimation'] is False and cap['automatic_causality_inference'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
