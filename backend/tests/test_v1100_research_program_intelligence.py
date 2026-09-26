import asyncio
from fastapi.testclient import TestClient
from app.contracts.research_program_intelligence import *
from app.services.research_program_intelligence import ResearchProgramIntelligenceStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeComputational:
    def get(self,pid):
        if pid not in {'comp-1','comp-2'}: raise ValueError('missing')
        return {'computational_plan_id':pid,'record_hash':f'hash-{pid}','core_project_id':'core-1','research_question':'How does X affect Y?','review':{'state':'approved'}}

def make_store(tmp_path): return ResearchProgramIntelligenceStore(tmp_path/'program.sqlite3',computational_store=FakeComputational())
def make_program(s): return s.create(ResearchProgramCreateRequest(actor_ref='lead',title='Climate resilience program',program_ref='program-2026',mission='Coordinate related original research.',research_objectives=['Estimate exposure','Test interventions'],computational_plan_ids=['comp-1']))
def add_workstream(s,pid): return s.add_workstream(pid,ResearchProgramWorkstreamAddRequest(actor_ref='lead',label='Exposure study',objective='Estimate exposure patterns',lead_ref='researcher-1',computational_plan_ids=['comp-1'],expected_outputs=['analysis package']))['workstreams'][0]

def test_create_inherits_computational_lineage_and_guardrails(tmp_path):
    s=make_store(tmp_path); rec=make_program(s)
    assert rec['schema']==RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA and rec['core_project_id']=='core-1'
    assert rec['computational_plan_fingerprints']['comp-1']=='hash-comp-1'
    assert rec['component_bindings'][0]['component_type']=='computational-research-plan' and rec['component_bindings'][0]['resolution_status']=='resolved'
    assert rec['governance']['automatic_research_prioritization'] is False and rec['governance']['automatic_execution'] is False

def test_workstreams_and_component_bindings_are_idempotent_and_validate_lineage(tmp_path):
    s=make_store(tmp_path); pid=make_program(s)['research_program_id']; ws=add_workstream(s,pid); add_workstream(s,pid); assert len(s.get(pid)['workstreams'])==1
    r=ResearchProgramComponentBindingRequest(actor_ref='lead',component_type='dataset-fitness-plan',component_ref='datafit-1',workstream_id=ws['workstream_id'],role='data-lineage',source_authority='research-librarian')
    s.bind_component(pid,r); s.bind_component(pid,r); rec=s.get(pid); assert len(rec['component_bindings'])==2 and rec['component_bindings'][-1]['resolution_status']=='declared-not-resolved-by-program-store'
    try: s.add_workstream(pid,ResearchProgramWorkstreamAddRequest(actor_ref='lead',label='bad',objective='bad',computational_plan_ids=['missing']))
    except ValueError as exc: assert 'computational_plan_id' in str(exc)
    else: raise AssertionError('unknown computational plan should fail')

def test_milestone_dependency_graph_is_declared_not_execution(tmp_path):
    s=make_store(tmp_path); pid=make_program(s)['research_program_id']; ws=add_workstream(s,pid)
    m1=s.add_milestone(pid,ResearchProgramMilestoneAddRequest(actor_ref='lead',label='Protocol approved',objective='Lock protocol',workstream_ids=[ws['workstream_id']],acceptance_criteria=['human approval']))['milestones'][0]
    m2=s.add_milestone(pid,ResearchProgramMilestoneAddRequest(actor_ref='lead',label='Analysis ready',objective='Prepare analysis',workstream_ids=[ws['workstream_id']],dependency_milestone_ids=[m1['milestone_id']]))['milestones'][1]
    g=s.program_graph(pid); assert {'from_node_id':m1['milestone_id'],'to_node_id':m2['milestone_id'],'relation':'milestone-precedes'} in g['edges'] and g['milestone_dependency_cycle'] is False
    assert g['governance']['graph_is_declared_program_structure_not_execution_or_scientific_validity'] is True

def test_human_milestone_decisions_and_program_approval_control_readiness(tmp_path):
    s=make_store(tmp_path); pid=make_program(s)['research_program_id']; ws=add_workstream(s,pid)
    m=s.add_milestone(pid,ResearchProgramMilestoneAddRequest(actor_ref='lead',label='Protocol gate',workstream_ids=[ws['workstream_id']]))['milestones'][0]
    assert s.readiness(pid)['ready_for_program_handoff'] is False
    s.decide_milestone(pid,ResearchProgramMilestoneDecisionRequest(actor_ref='reviewer',milestone_id=m['milestone_id'],decision='approved',rationale='Program gate approved.'))
    s.set_state(pid,ResearchProgramStateRequest(actor_ref='reviewer',state='approved'))
    assert s.readiness(pid)['ready_for_program_handoff'] is True

def test_deliverables_constraints_and_descriptive_portfolio_summary(tmp_path):
    s=make_store(tmp_path); pid=make_program(s)['research_program_id']; ws=add_workstream(s,pid)
    m=s.add_milestone(pid,ResearchProgramMilestoneAddRequest(actor_ref='lead',label='Output gate',workstream_ids=[ws['workstream_id']]))['milestones'][0]
    bid=s.get(pid)['component_bindings'][0]['binding_id']
    s.add_deliverable(pid,ResearchProgramDeliverableAddRequest(actor_ref='lead',label='Reproducible analysis package',milestone_id=m['milestone_id'],workstream_id=ws['workstream_id'],binding_ids=[bid],state='draft'))
    s.add_constraint(pid,ResearchProgramConstraintAddRequest(actor_ref='lead',category='resource',description='Compute allocation pending',blocking=True))
    summary=s.portfolio_summary(pid); assert summary['deliverable_count']==1 and summary['blocking_constraint_count']==1 and summary['governance']['counts_are_descriptive_not_priority_or_quality_scores'] is True
    assert 'blocking-program-constraint' in s.readiness(pid)['blockers']

def test_handoffs_core_candidate_and_snapshot_do_not_execute_or_promote(tmp_path):
    s=make_store(tmp_path); pid=make_program(s)['research_program_id']; ws=add_workstream(s,pid)
    m=s.add_milestone(pid,ResearchProgramMilestoneAddRequest(actor_ref='lead',label='Start gate',workstream_ids=[ws['workstream_id']]))['milestones'][0]
    s.decide_milestone(pid,ResearchProgramMilestoneDecisionRequest(actor_ref='reviewer',milestone_id=m['milestone_id'],decision='approved'))
    s.set_state(pid,ResearchProgramStateRequest(actor_ref='reviewer',state='approved'))
    hand=s.handoffs(pid); assert hand['packets'][0]['execution_performed'] is False and hand['packets'][0]['resource_allocation_performed'] is False and hand['packets'][0]['write_performed'] is False
    cand=s.core_candidate(pid); assert cand['handoff_status']=='human-approved-candidate' and cand['promotion_performed'] is False and cand['execution_performed'] is False
    snap=s.freeze_snapshot(ResearchProgramSnapshotRequest(actor_ref='reviewer',research_program_id=pid)); assert snap['schema']==RESEARCH_PROGRAM_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_invalid_upstream_computational_plan_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try: s.create(ResearchProgramCreateRequest(actor_ref='lead',title='bad',program_ref='bad',computational_plan_ids=['missing']))
    except ValueError as exc: assert 'computational_plan_ids' in str(exc)
    else: raise AssertionError('unknown computational plan should fail')

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); pid=make_program(s)['research_program_id']; assert 'research-program-intelligence-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_research_program_intelligence_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1100',job_type='research-program-intelligence-snapshot',payload={'snapshot':{'actor_ref':'lead','research_program_id':pid}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==RESEARCH_PROGRAM_SNAPSHOT_SCHEMA and events[-1]==('research-program-intelligence-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/research-program-intelligence/capabilities','/v1/core/research-program-intelligence/programs','/v1/core/research-program-intelligence/programs/{research_program_id}/program-graph','/v1/core/research-program-intelligence/programs/{research_program_id}/handoffs','/v1/core/research-program-intelligence/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get('/v1/core/research-program-intelligence/capabilities').status_code==401
    ok=client.get('/v1/core/research-program-intelligence/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_research_prioritization'] is False

def test_unified_environment_accepts_research_program_binding(tmp_path):
    s=make_store(tmp_path); pid=make_program(s)['research_program_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',research_program_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='lead',title='Unified',project_ref='p',research_program_ids=[pid]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['research_programs'])==1 and ready['dimensions']['research_program_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['milestone']=='11.0' and cap['human_program_approval_required'] is True and cap['component_authority_remains_with_source_system'] is True
    assert cap['automatic_research_prioritization'] is False and cap['automatic_resource_allocation'] is False and cap['automatic_milestone_completion'] is False and cap['automatic_scientific_judgment'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
