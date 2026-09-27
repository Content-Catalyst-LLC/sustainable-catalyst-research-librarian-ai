import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
import asyncio
from fastapi.testclient import TestClient
from app.contracts.reproduction_replication_intelligence import *
from app.services.reproduction_replication_intelligence import ReproductionReplicationIntelligenceStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakeProtocol:
    def get(self,pid):
        if pid!='protocol-1': raise ValueError('missing')
        return {'study_protocol_id':'protocol-1','record_hash':'protocol-hash','research_program_id':'prog-1','core_project_id':'core-1','registration':{'status':'preregistered','baseline_snapshot_hash':'baseline-hash'}}
class FakeStat:
    def get(self,pid):
        if pid!='stat-1': raise ValueError('missing')
        return {'statistical_analysis_plan_id':'stat-1','record_hash':'stat-hash','study_protocol_id':'protocol-1'}
class FakeCausal:
    def get(self,cid):
        if cid!='causal-1': raise ValueError('missing')
        return {'causal_design_id':'causal-1','record_hash':'causal-hash','statistical_analysis_plan_id':'stat-1'}
class FakeSimulation:
    def get(self,sid):
        if sid!='sim-1': raise ValueError('missing')
        return {'simulation_study_id':'sim-1','record_hash':'sim-hash','causal_design_id':'causal-1'}

def make_store(tmp_path):
    return ReproductionReplicationIntelligenceStore(tmp_path/'rr.sqlite3',study_protocol_store=FakeProtocol(),statistical_store=FakeStat(),causal_store=FakeCausal(),simulation_store=FakeSimulation())
def make_project(s):
    return s.create(ReproductionReplicationCreateRequest(actor_ref='lead',title='Replication program',source_study_ref='doi:10/example',study_protocol_id='protocol-1',statistical_analysis_plan_id='stat-1',causal_design_id='causal-1',simulation_study_id='sim-1'))
def add_attempt(s,rid):
    return s.add_reproduction_attempt(rid,ReproductionAttemptAddRequest(actor_ref='lead',label='Computational reproduction',kind='computational',target_refs=['table-2'],data_refs=['dataset:v1'],code_refs=['repo:commit'],environment_refs=['container:digest'],runtime_target='workspace',fidelity_basis='Same data, code revision, and declared environment.',expected_outputs=['table-2']))['reproduction_attempts'][0]
def add_replication(s,rid):
    return s.add_replication_study(rid,ReplicationStudyAddRequest(actor_ref='lead',label='Independent-data replication',kind='independent-data',target_claim_refs=['claim-1'],research_question='Does the registered association persist in an independent dataset?',population_or_context='Independent comparable population',dataset_refs=['dataset:v2'],method_refs=['stat-plan:registered'],independence_note='Independent data collection.'))['replication_studies'][0]

def test_create_inherits_protocol_stat_causal_simulation_lineage(tmp_path):
    s=make_store(tmp_path); rec=make_project(s)
    assert rec['schema']==REPRODUCTION_REPLICATION_SCHEMA and rec['research_program_id']=='prog-1'
    assert rec['protocol_fingerprint']=='protocol-hash' and rec['statistical_plan_fingerprint']=='stat-hash' and rec['causal_design_fingerprint']=='causal-hash' and rec['simulation_study_fingerprint']=='sim-hash'
    assert rec['governance']['reproduction_and_replication_are_distinct'] is True and rec['governance']['automatic_replication_verdict'] is False

def test_upstream_lineage_mismatch_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try: s.create(ReproductionReplicationCreateRequest(actor_ref='x',title='Bad',source_study_ref='s',study_protocol_id='missing'))
    except ValueError as exc: assert 'study_protocol_id' in str(exc)
    else: raise AssertionError('missing protocol should fail closed')
    class WrongStat:
        def get(self,pid): return {'statistical_analysis_plan_id':pid,'study_protocol_id':'other','record_hash':'x'}
    s2=ReproductionReplicationIntelligenceStore(tmp_path/'rr2.sqlite3',study_protocol_store=FakeProtocol(),statistical_store=WrongStat(),causal_store=FakeCausal(),simulation_store=FakeSimulation())
    try: s2.create(ReproductionReplicationCreateRequest(actor_ref='x',title='Bad',source_study_ref='s',study_protocol_id='protocol-1',statistical_analysis_plan_id='stat-1'))
    except ValueError as exc: assert 'does not belong' in str(exc)
    else: raise AssertionError('mismatched statistical plan should fail closed')

def test_attempt_replication_comparability_and_environment_are_idempotent(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)['reproduction_replication_id']; a=add_attempt(s,rid); r=add_replication(s,rid)
    s.add_reproduction_attempt(rid,ReproductionAttemptAddRequest(actor_ref='lead',label='Computational reproduction',kind='computational',target_refs=['table-2'],data_refs=['dataset:v1'],code_refs=['repo:commit'],environment_refs=['container:digest'],runtime_target='workspace',fidelity_basis='Same data, code revision, and declared environment.',expected_outputs=['table-2']))
    s.add_comparability_criterion(rid,ComparabilityCriterionAddRequest(actor_ref='lead',label='Outcome definition',dimension='outcome',source_basis='Registered primary outcome.',replication_basis='Same operational definition.',acceptable_difference='None planned.'))
    rec=s.set_environment_manifest(rid,ReproductionEnvironmentManifestRequest(actor_ref='lead',runtime='python',runtime_version='3.12',package_lock_refs=['requirements.lock'],container_or_environment_refs=['sha256:abc'],seed_policy='reuse registered seeds where applicable'))
    assert len(rec['reproduction_attempts'])==1 and len(rec['replication_studies'])==1 and len(rec['comparability_criteria'])==1
    assert rec['environment_manifest']['environment_reconstructed'] is False and a['execution_performed'] is False and r['replication_outcome_not_assessed'] is True

def test_deviations_and_execution_receipts_are_recorded_not_auto_judged(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)['reproduction_replication_id']; a=add_attempt(s,rid)
    s.add_deviation(rid,ReproductionReplicationDeviationAddRequest(actor_ref='lead',target_type='reproduction-attempt',target_id=a['reproduction_attempt_id'],category='runtime',description='Patch-level runtime differs.',rationale='Original patch unavailable.'))
    rec=s.add_execution_receipt(rid,ReproductionReplicationReceiptAddRequest(actor_ref='runner',target_type='reproduction-attempt',target_id=a['reproduction_attempt_id'],execution_ref='workspace-run-42',status='completed',observed_summary='Generated target table.',artifact_refs=['artifact:table2'],metrics={'rows':120}))
    assert rec['deviations'][0]['materiality_not_auto_judged'] is True
    assert rec['execution_receipts'][0]['receipt_is_observation_not_verdict'] is True and rec['execution_receipts'][0]['truth_not_promoted'] is True

def test_human_assessment_is_explicit_and_scope_bounded(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)['reproduction_replication_id']; r=add_replication(s,rid)
    rec=s.add_human_assessment(rid,ReproductionReplicationAssessmentRequest(actor_ref='reviewer',target_type='replication-study',target_id=r['replication_study_id'],assessment='inconclusive',rationale='Estimate is imprecise and context differs.',limitations=['limited sample']))
    a=rec['human_assessments'][0]; assert a['human_authored'] is True and a['assessment']=='inconclusive' and a['assessment_is_scope_bounded_not_global_truth'] is True

def test_human_approval_controls_readiness_and_runtime_handoffs(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)['reproduction_replication_id']; a=add_attempt(s,rid); r=add_replication(s,rid)
    s.add_comparability_criterion(rid,ComparabilityCriterionAddRequest(actor_ref='lead',label='Population',dimension='population',source_basis='Original population',replication_basis='Independent comparable population'))
    s.set_environment_manifest(rid,ReproductionEnvironmentManifestRequest(actor_ref='lead',runtime='python',runtime_version='3.12'))
    assert 'reproduction-attempts-await-human-approval' in s.readiness(rid)['blockers']
    s.decide(rid,ReproductionReplicationDecisionRequest(actor_ref='reviewer',object_type='reproduction-attempt',object_id=a['reproduction_attempt_id'],decision='approved'))
    s.decide(rid,ReproductionReplicationDecisionRequest(actor_ref='reviewer',object_type='replication-study',object_id=r['replication_study_id'],decision='approved'))
    ready=s.readiness(rid); packets=s.runtime_handoffs(rid)['packets']
    assert ready['ready_for_execution_handoff'] is True and len(packets)==2
    assert all(p['execution_performed'] is False for p in packets) and any(p['target']=='workspace' for p in packets) and any(p['target']=='research-lab' for p in packets)

def test_matrix_lineage_core_candidate_and_snapshot(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)['reproduction_replication_id']; a=add_attempt(s,rid); r=add_replication(s,rid)
    s.add_comparability_criterion(rid,ComparabilityCriterionAddRequest(actor_ref='lead',label='Analysis',dimension='analysis',source_basis='Registered model',replication_basis='Same estimand with prespecified alternative robustness model'))
    s.decide(rid,ReproductionReplicationDecisionRequest(actor_ref='reviewer',object_type='reproduction-attempt',object_id=a['reproduction_attempt_id'],decision='approved'))
    matrix=s.comparison_matrix(rid); line=s.lineage_map(rid); cand=s.core_candidate(rid); snap=s.freeze_snapshot(ReproductionReplicationSnapshotRequest(actor_ref='reviewer',reproduction_replication_id=rid))
    assert matrix['governance']['matrix_is_descriptive_comparison_not_automatic_replication_verdict'] is True and line['outcome_inferred'] is False
    assert cand['object_type']=='reproduction-replication-plan' and cand['replication_verdict_generated'] is False and cand['truth_promoted'] is False
    assert snap['schema']==REPRODUCTION_REPLICATION_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); rid=make_project(s)['reproduction_replication_id']; assert 'reproduction-replication-intelligence-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_reproduction_replication_intelligence_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1150',job_type='reproduction-replication-intelligence-snapshot',payload={'snapshot':{'actor_ref':'lead','reproduction_replication_id':rid}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==REPRODUCTION_REPLICATION_SNAPSHOT_SCHEMA and events[-1]==('reproduction-replication-intelligence-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/reproduction-replication-intelligence/capabilities','/v1/core/reproduction-replication-intelligence/projects','/v1/core/reproduction-replication-intelligence/projects/{reproduction_replication_id}/comparison-matrix','/v1/core/reproduction-replication-intelligence/projects/{reproduction_replication_id}/runtime-handoffs','/v1/core/reproduction-replication-intelligence/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); status=client.get('/v1/core/reproduction-replication-intelligence/capabilities').status_code; assert status in {401,503}
    ok=client.get('/v1/core/reproduction-replication-intelligence/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_replication_verdict'] is False

def test_unified_environment_accepts_reproduction_replication_binding(tmp_path):
    s=make_store(tmp_path); rid=make_project(s)['reproduction_replication_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',reproduction_replication_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='lead',title='Unified',project_ref='p',reproduction_replication_ids=[rid]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['reproduction_replication_projects'])==1 and ready['dimensions']['reproduction_replication_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['milestone']=='11.5' and cap['reproduction_replication_distinction'] is True
    assert cap['human_outcome_assessment'] is True and cap['comparability_criteria'] is True and cap['execution_receipts'] is True
    assert cap['specialist_runtimes_own_execution'] is True and cap['platform_core_remains_governed_research_object_authority'] is True
    assert cap['automatic_reproduction_verdict'] is False and cap['automatic_replication_verdict'] is False
    assert cap['automatic_claim_acceptance'] is False and cap['automatic_causal_inference'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
