import asyncio
from fastapi.testclient import TestClient
from app.contracts.study_protocol_preregistration import *
from app.services.study_protocol_preregistration import StudyProtocolPreregistrationStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore

class FakePrograms:
    def get(self,pid):
        if pid!='prog-1': raise ValueError('missing')
        return {'research_program_id':'prog-1','record_hash':'program-hash','core_project_id':'core-1','workstreams':[{'workstream_id':'ws-1','objective':'Estimate intervention effect'}]}

def make_store(tmp_path): return StudyProtocolPreregistrationStore(tmp_path/'protocol.sqlite3',research_program_store=FakePrograms())
def make_protocol(s): return s.create(StudyProtocolCreateRequest(actor_ref='lead',title='Intervention protocol',protocol_ref='protocol-2026',research_program_id='prog-1',workstream_id='ws-1',study_type='randomized-trial',registration_target='OSF'))
def populate(s,pid):
    h=s.add_hypothesis(pid,ProtocolHypothesisAddRequest(actor_ref='lead',label='H1',statement='The intervention changes the primary outcome.',role='confirmatory'))['hypotheses'][0]
    o=s.add_outcome(pid,ProtocolOutcomeAddRequest(actor_ref='lead',label='Primary outcome',role='primary',measure='Validated scale score',timepoint='12 weeks'))['outcomes'][0]
    v=s.add_variable(pid,ProtocolVariableAddRequest(actor_ref='lead',name='treatment',role='exposure',operational_definition='Randomized treatment assignment'))['variables'][0]
    s.set_sampling_plan(pid,ProtocolSamplingPlanRequest(actor_ref='lead',population='Eligible adults',inclusion_criteria=['age >= 18'],exclusion_criteria=['missing consent'],target_sample_size=200,stopping_rule='Stop when target sample is reached.'))
    c=s.add_analysis_commitment(pid,ProtocolAnalysisCommitmentAddRequest(actor_ref='lead',label='Primary model',method='Linear model',hypothesis_ids=[h['hypothesis_id']],outcome_ids=[o['outcome_id']],variable_ids=[v['variable_id']],alpha_or_threshold='0.05',missing_data_strategy='Multiple imputation'))['analysis_commitments'][0]
    return h,o,v,c

def test_create_inherits_program_lineage_and_guardrails(tmp_path):
    s=make_store(tmp_path); rec=make_protocol(s)
    assert rec['schema']==STUDY_PROTOCOL_PREREGISTRATION_SCHEMA and rec['research_program_fingerprint']=='program-hash' and rec['core_project_id']=='core-1'
    assert rec['governance']['preregistration_baseline_is_immutable_once_frozen'] is True and rec['governance']['automatic_preregistration'] is False

def test_protocol_components_are_idempotent_and_structured(tmp_path):
    s=make_store(tmp_path); pid=make_protocol(s)['study_protocol_id']; h,o,v,c=populate(s,pid)
    s.add_hypothesis(pid,ProtocolHypothesisAddRequest(actor_ref='lead',label='H1',statement='The intervention changes the primary outcome.',role='confirmatory'))
    rec=s.get(pid); assert len(rec['hypotheses'])==1 and len(rec['outcomes'])==1 and len(rec['variables'])==1 and len(rec['analysis_commitments'])==1
    row=s.protocol_matrix(pid)['rows'][0]; assert row['commitment_id']==c['commitment_id'] and row['decision']=='pending'

def test_human_commitment_approval_controls_preregistration_readiness(tmp_path):
    s=make_store(tmp_path); pid=make_protocol(s)['study_protocol_id']; *_,c=populate(s,pid)
    assert 'analysis-commitments-await-human-approval' in s.readiness(pid)['blockers']
    s.decide_commitment(pid,ProtocolCommitmentDecisionRequest(actor_ref='reviewer',commitment_id=c['commitment_id'],decision='approved',rationale='Specified prospectively.'))
    assert s.readiness(pid)['ready_for_preregistration'] is True

def test_preregistration_freezes_immutable_baseline(tmp_path):
    s=make_store(tmp_path); pid=make_protocol(s)['study_protocol_id']; *_,c=populate(s,pid); s.decide_commitment(pid,ProtocolCommitmentDecisionRequest(actor_ref='reviewer',commitment_id=c['commitment_id'],decision='approved'))
    rec=s.preregister(pid,ProtocolPreregisterRequest(actor_ref='reviewer',registration_target='OSF',registration_identifier='osf-abc',registration_url='https://example.org/osf-abc'))
    baseline=rec['registration']['baseline_snapshot_hash']; assert rec['review']['state']=='preregistered' and len(baseline)==64
    try: s.add_outcome(pid,ProtocolOutcomeAddRequest(actor_ref='lead',label='Late outcome',measure='Not allowed'))
    except ValueError as exc: assert 'immutable' in str(exc)
    else: raise AssertionError('preregistered baseline must not be silently rewritten')

def test_amendments_are_append_only_and_preserve_baseline_hash(tmp_path):
    s=make_store(tmp_path); pid=make_protocol(s)['study_protocol_id']; *_,c=populate(s,pid); s.decide_commitment(pid,ProtocolCommitmentDecisionRequest(actor_ref='reviewer',commitment_id=c['commitment_id'],decision='approved')); before=s.preregister(pid,ProtocolPreregisterRequest(actor_ref='reviewer',registration_identifier='reg-1')); base=before['registration']['baseline_snapshot_hash']
    rec=s.add_amendment(pid,ProtocolAmendmentAddRequest(actor_ref='lead',description='Extend recruitment window.',rationale='Enrollment slower than planned.',impact='minor',affected_sections=['sampling'],prospective=True))
    assert rec['protocol_version']==2 and rec['registration']['baseline_snapshot_hash']==base and rec['amendments'][0]['baseline_snapshot_hash']==base

def test_deviations_are_disclosed_not_auto_judged(tmp_path):
    s=make_store(tmp_path); pid=make_protocol(s)['study_protocol_id']; *_,c=populate(s,pid)
    rec=s.add_deviation(pid,ProtocolDeviationAddRequest(actor_ref='lead',category='analysis',description='One planned robustness check could not run.',affected_commitment_ids=[c['commitment_id']],consequence_note='Report transparently.'))
    assert rec['deviations'][0]['invalidity_not_inferred'] is True and rec['governance']['automatic_deviation_judgment'] is False

def test_handoffs_core_candidate_and_snapshot_never_execute_or_promote(tmp_path):
    s=make_store(tmp_path); pid=make_protocol(s)['study_protocol_id']; *_,c=populate(s,pid); s.decide_commitment(pid,ProtocolCommitmentDecisionRequest(actor_ref='reviewer',commitment_id=c['commitment_id'],decision='approved')); s.preregister(pid,ProtocolPreregisterRequest(actor_ref='reviewer'))
    hand=s.handoffs(pid); assert hand['packets'][0]['execution_performed'] is False and hand['packets'][0]['method_selection_performed'] is False
    cand=s.core_candidate(pid); assert cand['handoff_status']=='preregistered-candidate' and cand['promotion_performed'] is False
    snap=s.freeze_snapshot(StudyProtocolSnapshotRequest(actor_ref='reviewer',study_protocol_id=pid)); assert snap['schema']==STUDY_PROTOCOL_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); pid=make_protocol(s)['study_protocol_id']; assert 'study-protocol-preregistration-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_study_protocol_preregistration_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1110',job_type='study-protocol-preregistration-snapshot',payload={'snapshot':{'actor_ref':'lead','study_protocol_id':pid}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==STUDY_PROTOCOL_SNAPSHOT_SCHEMA and events[-1]==('study-protocol-preregistration-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/study-protocol-preregistration/capabilities','/v1/core/study-protocol-preregistration/protocols','/v1/core/study-protocol-preregistration/protocols/{study_protocol_id}/preregister','/v1/core/study-protocol-preregistration/protocols/{study_protocol_id}/amendments','/v1/core/study-protocol-preregistration/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); status=client.get('/v1/core/study-protocol-preregistration/capabilities').status_code; assert status in {401,503}
    ok=client.get('/v1/core/study-protocol-preregistration/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_preregistration'] is False

def test_unified_environment_accepts_study_protocol_binding(tmp_path):
    s=make_store(tmp_path); pid=make_protocol(s)['study_protocol_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',study_protocol_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='lead',title='Unified',project_ref='p',study_protocol_ids=[pid]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['study_protocols'])==1 and ready['dimensions']['study_protocol_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['milestone']=='11.1' and cap['human_preregistration_approval_required'] is True and cap['preregistration_baseline_is_immutable_once_frozen'] is True
    assert cap['automatic_hypothesis_acceptance'] is False and cap['automatic_method_selection'] is False and cap['automatic_preregistration'] is False and cap['automatic_amendment_acceptance'] is False and cap['automatic_deviation_judgment'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
