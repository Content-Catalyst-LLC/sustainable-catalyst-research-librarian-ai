import asyncio
from fastapi.testclient import TestClient
from app.contracts.computational_research_planning import *
from app.services.computational_research_planning import ComputationalResearchPlanningStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeFitness:
    def get(self,did):
        if did!='datafit-1': raise ValueError('missing')
        return {'data_fitness_id':'datafit-1','record_hash':'fit-hash','research_question':'How does X affect Y?','core_project_id':'core-1','dataset_candidates':[{'dataset_id':'ds-1','title':'D'}],'variables':[{'variable_id':'var-x','dataset_id':'ds-1','name':'x'}],'fitness_assessments':[{'assessment_id':'fa-1','dataset_id':'ds-1','decision':'fit-with-limitations'}]}

def make_store(tmp_path): return ComputationalResearchPlanningStore(tmp_path/'plan.sqlite3',dataset_fitness_store=FakeFitness())
def make_project(s): return s.create(ComputationalResearchPlanCreateRequest(actor_ref='r',title='Compute plan',project_ref='p',data_fitness_id='datafit-1',dataset_ids=['ds-1']))
def add_runtime(s,pid): return s.add_runtime_target(pid,ComputationalRuntimeTargetAddRequest(actor_ref='r',runtime_kind='python',name='Python runtime',version_constraint='>=3.12'))['runtime_targets'][0]
def add_step(s,pid,rid): return s.add_step(pid,ComputationalAnalysisStepAddRequest(actor_ref='r',label='Estimate model',objective='Estimate association',method_family='regression',runtime_target_id=rid,dataset_ids=['ds-1'],variable_ids=['var-x'],expected_outputs=['coefficient table'],validation_checks=['residual diagnostics']))['analysis_steps'][0]

def test_create_inherits_dataset_fitness_lineage_and_guardrails(tmp_path):
    s=make_store(tmp_path); rec=make_project(s)
    assert rec['schema']==COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA and rec['research_question']=='How does X affect Y?'
    assert rec['data_fitness_fingerprint']=='fit-hash' and rec['human_accepted_dataset_ids']==['ds-1'] and rec['core_project_id']=='core-1'
    assert rec['governance']['automatic_execution'] is False and rec['governance']['human_method_and_runtime_approval_required'] is True

def test_runtime_targets_and_steps_are_idempotent_and_validate_lineage(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)['computational_plan_id']; rt=add_runtime(s,pid); add_runtime(s,pid); assert len(s.get(pid)['runtime_targets'])==1
    step=add_step(s,pid,rt['runtime_target_id']); add_step(s,pid,rt['runtime_target_id']); assert len(s.get(pid)['analysis_steps'])==1 and step['execution_status']=='not-executed'
    try: s.add_step(pid,ComputationalAnalysisStepAddRequest(actor_ref='r',label='bad',objective='bad',runtime_target_id='missing'))
    except ValueError as exc: assert 'runtime_target_id' in str(exc)
    else: raise AssertionError('unknown runtime should fail')

def test_dependency_graph_and_cycle_semantics_are_declared_not_execution(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)['computational_plan_id']; rt=add_runtime(s,pid); a=add_step(s,pid,rt['runtime_target_id'])
    b=s.add_step(pid,ComputationalAnalysisStepAddRequest(actor_ref='r',label='Validate',objective='Validate output',method_family='diagnostics',runtime_target_id=rt['runtime_target_id'],dependency_step_ids=[a['step_id']]))['analysis_steps'][1]
    g=s.execution_graph(pid); assert len(g['nodes'])==2 and {'from_step_id':a['step_id'],'to_step_id':b['step_id'],'relation':'precedes'} in g['edges'] and g['has_cycle'] is False
    assert g['governance']['graph_is_declared_dependency_structure_not_execution_trace'] is True

def test_human_step_decisions_and_reproducibility_control_readiness(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)['computational_plan_id']; rt=add_runtime(s,pid); step=add_step(s,pid,rt['runtime_target_id'])
    assert s.readiness(pid)['ready_for_execution_handoff'] is False
    s.decide_step(pid,ComputationalStepDecisionRequest(actor_ref='reviewer',step_id=step['step_id'],decision='approved-for-execution',rationale='Method is appropriate for the scoped question.'))
    s.add_reproducibility_requirement(pid,ReproducibilityRequirementAddRequest(actor_ref='reviewer',label='Environment lock',description='Capture dependencies',artifact_type='environment-lock'))
    s.set_state(pid,ComputationalResearchPlanStateRequest(actor_ref='reviewer',state='approved'))
    assert s.readiness(pid)['ready_for_execution_handoff'] is True

def test_constraints_can_block_handoff(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)['computational_plan_id']; rt=add_runtime(s,pid); step=add_step(s,pid,rt['runtime_target_id'])
    s.decide_step(pid,ComputationalStepDecisionRequest(actor_ref='r',step_id=step['step_id'],decision='approved-for-execution'))
    s.add_reproducibility_requirement(pid,ReproducibilityRequirementAddRequest(actor_ref='r',label='Seed',description='Record random seed'))
    s.set_state(pid,ComputationalResearchPlanStateRequest(actor_ref='r',state='approved'))
    s.add_constraint(pid,ComputationalConstraintAddRequest(actor_ref='r',category='privacy',description='Restricted microdata approval pending',blocking=True))
    assert 'blocking-computational-constraint' in s.readiness(pid)['blockers']

def test_execution_handoff_core_candidate_and_snapshot_do_not_execute_or_promote(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)['computational_plan_id']; rt=add_runtime(s,pid); step=add_step(s,pid,rt['runtime_target_id'])
    s.decide_step(pid,ComputationalStepDecisionRequest(actor_ref='reviewer',step_id=step['step_id'],decision='approved-for-execution'))
    s.add_reproducibility_requirement(pid,ReproducibilityRequirementAddRequest(actor_ref='reviewer',label='Environment',description='Lock environment'))
    s.set_state(pid,ComputationalResearchPlanStateRequest(actor_ref='reviewer',state='approved'))
    hand=s.execution_handoffs(pid); assert hand['packets'][0]['execution_performed'] is False and hand['packets'][0]['write_performed'] is False
    cand=s.core_candidate(pid); assert cand['handoff_status']=='human-approved-candidate' and cand['promotion_performed'] is False and cand['execution_performed'] is False
    snap=s.freeze_snapshot(ComputationalResearchPlanSnapshotRequest(actor_ref='reviewer',computational_plan_id=pid)); assert snap['schema']==COMPUTATIONAL_RESEARCH_PLANNING_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_invalid_dataset_lineage_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try: s.create(ComputationalResearchPlanCreateRequest(actor_ref='r',title='bad',project_ref='p',data_fitness_id='datafit-1',dataset_ids=['missing']))
    except ValueError as exc: assert 'dataset_ids' in str(exc)
    else: raise AssertionError('unknown dataset should fail')

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); pid=make_project(s)['computational_plan_id']; assert 'computational-research-planning-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_computational_research_planning_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1090',job_type='computational-research-planning-snapshot',payload={'snapshot':{'actor_ref':'r','computational_plan_id':pid}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==COMPUTATIONAL_RESEARCH_PLANNING_SNAPSHOT_SCHEMA and events[-1]==('computational-research-planning-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/computational-research-planning/capabilities','/v1/core/computational-research-planning/plans','/v1/core/computational-research-planning/plans/{computational_plan_id}/execution-graph','/v1/core/computational-research-planning/plans/{computational_plan_id}/execution-handoffs','/v1/core/computational-research-planning/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get('/v1/core/computational-research-planning/capabilities').status_code==401
    ok=client.get('/v1/core/computational-research-planning/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_execution'] is False

def test_unified_environment_accepts_computational_plan_binding(tmp_path):
    s=make_store(tmp_path); pid=make_project(s)['computational_plan_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',computational_research_planning_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='r',title='Unified',project_ref='p',computational_research_plan_ids=[pid]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['computational_research_plans'])==1 and ready['dimensions']['computational_research_plan_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['human_method_and_runtime_approval_required'] is True and cap['specialist_runtimes_own_execution'] is True
    assert cap['automatic_method_selection'] is False and cap['automatic_runtime_selection'] is False and cap['automatic_execution'] is False and cap['automatic_result_interpretation'] is False and cap['automatic_truth_promotion'] is False
