import asyncio
from fastapi.testclient import TestClient
from app.contracts.dataset_discovery_data_fitness import *
from app.services.dataset_discovery_data_fitness import DatasetDiscoveryDataFitnessStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeGap:
    def get(self,gid):
        if gid!='gap-1': raise ValueError('missing')
        return {'gap_novelty_id':'gap-1','record_hash':'gap-hash','research_question':'How does X affect Y?','core_project_id':'core-1','research_opportunities':[{'opportunity_id':'opp-1','research_question':'Does X affect Y in setting B?'}]}

def make_store(tmp_path): return DatasetDiscoveryDataFitnessStore(tmp_path/'fit.sqlite3',gap_store=FakeGap())
def make_project(s): return s.create(DatasetFitnessCreateRequest(actor_ref='r',title='Data fitness',project_ref='p',gap_novelty_id='gap-1',research_opportunity_ids=['opp-1']))

def test_create_inherits_gap_lineage_and_guardrails(tmp_path):
    s=make_store(tmp_path); rec=make_project(s)
    assert rec['schema']==DATASET_DISCOVERY_FITNESS_SCHEMA and rec['research_question']=='How does X affect Y?'
    assert rec['gap_novelty_fingerprint']=='gap-hash' and rec['core_project_id']=='core-1'
    assert rec['governance']['automatic_dataset_suitability'] is False and rec['governance']['human_fitness_decision_required'] is True

def test_requirements_datasets_variables_are_idempotent_and_validated(tmp_path):
    s=make_store(tmp_path); did=make_project(s)['data_fitness_id']
    req=DataRequirementAddRequest(actor_ref='r',label='Panel inputs',description='Need X and Y',required_variables=['x','y'],opportunity_ids=['opp-1'])
    a=s.add_requirement(did,req); b=s.add_requirement(did,req); assert len(b['data_requirements'])==1
    ds=DatasetCandidateAddRequest(actor_ref='r',source_ref='dataset:1',title='Dataset One',provider='Agency',geography=['US'],license='CC-BY')
    rec=s.add_dataset(did,ds); rec=s.add_dataset(did,ds); assert len(rec['dataset_candidates'])==1
    dsid=rec['dataset_candidates'][0]['dataset_id']
    rec=s.add_variable(did,DatasetVariableAddRequest(actor_ref='r',dataset_id=dsid,name='x',role='exposure')); rec=s.add_variable(did,DatasetVariableAddRequest(actor_ref='r',dataset_id=dsid,name='x',role='exposure'))
    assert len(rec['variables'])==1 and rec['variables'][0]['semantics_certified'] is False
    try: s.add_variable(did,DatasetVariableAddRequest(actor_ref='r',dataset_id='missing',name='z'))
    except ValueError as exc: assert 'unknown dataset_id' in str(exc)
    else: raise AssertionError('unknown dataset should fail')

def test_coverage_matrix_is_structural_not_fitness_claim(tmp_path):
    s=make_store(tmp_path); did=make_project(s)['data_fitness_id']
    r=s.add_requirement(did,DataRequirementAddRequest(actor_ref='r',label='Inputs',description='Need x and y',required_variables=['x','y']))['data_requirements'][0]
    d=s.add_dataset(did,DatasetCandidateAddRequest(actor_ref='r',source_ref='dataset:1',title='D'))['dataset_candidates'][0]
    s.add_variable(did,DatasetVariableAddRequest(actor_ref='r',dataset_id=d['dataset_id'],name='x'))
    m=s.coverage_matrix(did); row=m['rows'][0]
    assert row['recorded_variables_present']==['x'] and row['recorded_variables_missing']==['y']
    assert m['governance']['coverage_is_metadata_comparison_not_scientific_fitness'] is True

def test_human_fitness_assessment_controls_readiness(tmp_path):
    s=make_store(tmp_path); did=make_project(s)['data_fitness_id']
    r=s.add_requirement(did,DataRequirementAddRequest(actor_ref='r',label='Inputs',description='Need x'))['data_requirements'][0]
    d=s.add_dataset(did,DatasetCandidateAddRequest(actor_ref='r',source_ref='dataset:1',title='D'))['dataset_candidates'][0]
    assert s.readiness(did)['ready_for_governed_handoff'] is False
    rec=s.assess(did,DatasetFitnessAssessmentRequest(actor_ref='reviewer',dataset_id=d['dataset_id'],requirement_ids=[r['requirement_id']],decision='fit-with-limitations',limitations=['Temporal coverage ends in 2024.'],rationale='Usable for scoped analysis.'))
    assert rec['fitness_assessments'][0]['human_recorded'] is True and rec['fitness_assessments'][0]['scientific_validity_certified'] is False
    s.set_state(did,DatasetFitnessStateRequest(actor_ref='reviewer',state='approved'))
    assert s.readiness(did)['ready_for_governed_handoff'] is True

def test_handoff_core_candidate_and_snapshot_do_not_execute_or_promote(tmp_path):
    s=make_store(tmp_path); did=make_project(s)['data_fitness_id']
    r=s.add_requirement(did,DataRequirementAddRequest(actor_ref='r',label='Inputs',description='Need x'))['data_requirements'][0]
    d=s.add_dataset(did,DatasetCandidateAddRequest(actor_ref='r',source_ref='dataset:1',title='D'))['dataset_candidates'][0]
    s.assess(did,DatasetFitnessAssessmentRequest(actor_ref='reviewer',dataset_id=d['dataset_id'],requirement_ids=[r['requirement_id']],decision='fit'))
    s.set_state(did,DatasetFitnessStateRequest(actor_ref='reviewer',state='approved'))
    hand=s.computational_planning_handoff(did); assert hand['write_performed'] is False and hand['governance']['automatic_ingestion'] is False
    cand=s.core_candidate(did); assert cand['handoff_status']=='human-approved-candidate' and cand['promotion_performed'] is False
    snap=s.freeze_snapshot(DatasetFitnessSnapshotRequest(actor_ref='reviewer',data_fitness_id=did)); assert snap['schema']==DATASET_DISCOVERY_FITNESS_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_invalid_opportunity_lineage_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try: s.create(DatasetFitnessCreateRequest(actor_ref='r',title='bad',project_ref='p',gap_novelty_id='gap-1',research_opportunity_ids=['missing']))
    except ValueError as exc: assert 'research_opportunity_ids' in str(exc)
    else: raise AssertionError('unknown opportunity should fail')

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); did=make_project(s)['data_fitness_id']; assert 'dataset-discovery-data-fitness-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_dataset_discovery_data_fitness_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1080',job_type='dataset-discovery-data-fitness-snapshot',payload={'snapshot':{'actor_ref':'r','data_fitness_id':did}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==DATASET_DISCOVERY_FITNESS_SNAPSHOT_SCHEMA and events[-1]==('dataset-discovery-data-fitness-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/dataset-discovery-data-fitness/capabilities','/v1/core/dataset-discovery-data-fitness/projects','/v1/core/dataset-discovery-data-fitness/projects/{data_fitness_id}/coverage-matrix','/v1/core/dataset-discovery-data-fitness/projects/{data_fitness_id}/computational-planning-handoff','/v1/core/dataset-discovery-data-fitness/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get('/v1/core/dataset-discovery-data-fitness/capabilities').status_code==401
    ok=client.get('/v1/core/dataset-discovery-data-fitness/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_dataset_suitability'] is False

def test_unified_environment_accepts_dataset_fitness_binding(tmp_path):
    s=make_store(tmp_path); did=make_project(s)['data_fitness_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',dataset_fitness_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='r',title='Unified',project_ref='p',dataset_fitness_ids=[did]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['dataset_fitness_intelligence'])==1 and ready['dimensions']['dataset_fitness_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['human_fitness_decision_required'] is True and cap['fitness_is_question_specific_not_global_quality'] is True
    assert cap['automatic_dataset_suitability'] is False and cap['automatic_quality_certification'] is False and cap['automatic_ingestion'] is False and cap['automatic_truth_promotion'] is False
