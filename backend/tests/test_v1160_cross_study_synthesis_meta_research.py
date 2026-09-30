import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
import asyncio
from fastapi.testclient import TestClient
from app.contracts.cross_study_synthesis_meta_research import *
from app.services.cross_study_synthesis_meta_research import CrossStudySynthesisMetaResearchStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job

class FakeReview:
    def get(self,rid):
        if rid!='review-1': raise ValueError('missing')
        return {'review_id':'review-1','record_hash':'review-hash'}
class FakeRR:
    def get(self,rid):
        if rid not in {'rr-1','rr-2'}: raise ValueError('missing')
        return {'reproduction_replication_id':rid,'record_hash':rid+'-hash'}

def make_store(tmp_path): return CrossStudySynthesisMetaResearchStore(tmp_path/'xstudy.sqlite3',systematic_review_store=FakeReview(),reproduction_replication_store=FakeRR())
def make_project(s): return s.create(CrossStudySynthesisCreateRequest(actor_ref='lead',title='Cross-study synthesis',research_question='How consistent is the evidence?',synthesis_kind='meta-analysis-plan',systematic_review_id='review-1',reproduction_replication_ids=['rr-1','rr-2']))
def add_study(s,sid,ref,label,direction,estimate,rr):
    rec=s.add_study(sid,CrossStudyEvidenceAddRequest(actor_ref='reviewer',study_ref=ref,label=label,design='cohort',population_context='adult population',sample_size=100,outcome='primary outcome',effect_measure='risk-ratio',estimate=estimate,direction=direction,reproduction_replication_id=rr))
    return rec['studies'][-1]

def test_create_preserves_upstream_lineage_and_governance(tmp_path):
    s=make_store(tmp_path); rec=make_project(s)
    assert rec['schema']==CROSS_STUDY_SYNTHESIS_SCHEMA and rec['upstream_lineage']['systematic_review_fingerprint']=='review-hash'
    assert len(rec['upstream_lineage']['reproduction_replication_fingerprints'])==2
    assert rec['governance']['automatic_meta_analysis'] is False and rec['governance']['automatic_truth_promotion'] is False

def test_missing_upstream_reference_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try: s.create(CrossStudySynthesisCreateRequest(actor_ref='x',title='Bad',research_question='q',systematic_review_id='missing'))
    except ValueError as exc: assert 'systematic_review_id' in str(exc)
    else: raise AssertionError('missing systematic review should fail closed')

def test_study_disposition_matrix_and_landscape_are_descriptive(tmp_path):
    s=make_store(tmp_path); sid=make_project(s)['cross_study_synthesis_id']; a=add_study(s,sid,'doi:a','Study A','positive',1.2,'rr-1'); b=add_study(s,sid,'doi:b','Study B','null',1.0,'rr-2')
    s.set_study_disposition(sid,CrossStudyDispositionRequest(actor_ref='reviewer',study_id=a['study_id'],disposition='included',rationale='Eligible'))
    s.set_study_disposition(sid,CrossStudyDispositionRequest(actor_ref='reviewer',study_id=b['study_id'],disposition='included',rationale='Eligible'))
    matrix=s.study_matrix(sid); landscape=s.evidence_landscape(sid); contradictions=s.contradiction_map(sid)
    assert len(matrix['rows'])==2 and landscape['included_study_count']==2
    assert landscape['governance']['strength_of_evidence_not_inferred'] is True
    assert contradictions['governance']['directional_variation_is_signal_for_review_not_contradiction_verdict'] is True

def test_bias_and_meta_research_are_human_authored_scope_bounded(tmp_path):
    s=make_store(tmp_path); sid=make_project(s)['cross_study_synthesis_id']; a=add_study(s,sid,'doi:a','Study A','positive',1.2,'rr-1')
    rec=s.add_bias_assessment(sid,CrossStudyBiasAssessmentAddRequest(actor_ref='reviewer',study_id=a['study_id'],domain='missing outcome data',judgment='some-concerns',rationale='Attrition is incompletely reported.'))
    rec=s.add_meta_research_observation(sid,MetaResearchObservationAddRequest(actor_ref='reviewer',category='code-availability',scope='included literature',observation='One study supplied executable code.',supporting_refs=['doi:a']))
    assert rec['bias_assessments'][0]['human_authored'] is True and rec['bias_assessments'][0]['judgment_not_global_truth'] is True
    assert rec['meta_research_observations'][0]['causal_or_motive_inference_not_generated'] is True

def test_human_approval_controls_runtime_handoff_and_receipts(tmp_path):
    s=make_store(tmp_path); sid=make_project(s)['cross_study_synthesis_id']; a=add_study(s,sid,'doi:a','Study A','positive',1.2,'rr-1'); b=add_study(s,sid,'doi:b','Study B','positive',1.1,'rr-2')
    for x in [a,b]: s.set_study_disposition(sid,CrossStudyDispositionRequest(actor_ref='reviewer',study_id=x['study_id'],disposition='included',rationale='Eligible'))
    s.add_dimension(sid,CrossStudySynthesisDimensionAddRequest(actor_ref='reviewer',label='Population',dimension='population',comparison_basis='Comparable target populations',known_differences=['country']))
    rec=s.add_synthesis_plan(sid,CrossStudySynthesisPlanAddRequest(actor_ref='analyst',label='Random effects plan',method_kind='random-effects',estimand_or_target='pooled risk ratio',heterogeneity_metrics=['tau2','I2'],bias_diagnostics=['funnel-plot'],sensitivity_analyses=['leave-one-out'],runtime_target='workspace'))
    pid=rec['synthesis_plans'][0]['synthesis_plan_id']; assert s.readiness(sid)['ready_for_execution_handoff'] is False
    s.decide(sid,CrossStudyDecisionRequest(actor_ref='reviewer',object_type='synthesis-plan',object_id=pid,decision='approved',rationale='Plan is prespecified.'))
    assert s.readiness(sid)['ready_for_execution_handoff'] is True and len(s.runtime_handoffs(sid)['packets'])==1
    rec=s.add_execution_receipt(sid,CrossStudySynthesisReceiptAddRequest(actor_ref='runner',synthesis_plan_id=pid,execution_ref='workspace-run-1',status='completed',observed_summary='Runtime produced pooled estimate.',pooled_estimates=[{'measure':'risk-ratio','estimate':1.15}]))
    assert rec['execution_receipts'][0]['receipt_is_observation_not_scholarly_verdict'] is True and rec['execution_receipts'][0]['pooled_estimates_not_truth_promoted'] is True

def test_human_interpretation_core_candidate_and_snapshot(tmp_path):
    s=make_store(tmp_path); sid=make_project(s)['cross_study_synthesis_id']
    rec=s.add_human_interpretation(sid,CrossStudyHumanInterpretationAddRequest(actor_ref='lead',interpretation='Evidence direction is broadly similar, with important contextual limitations.',limitations=['small study set']))
    cand=s.core_candidate(sid); snap=s.freeze_snapshot(CrossStudySnapshotRequest(actor_ref='lead',cross_study_synthesis_id=sid))
    assert rec['human_interpretations'][0]['human_authored'] is True and cand['truth_promoted'] is False
    assert snap['schema']==CROSS_STUDY_SYNTHESIS_SNAPSHOT_SCHEMA and len(snap['snapshot_hash'])==64

def test_durable_job_and_authenticated_api_surface(tmp_path,monkeypatch):
    s=make_store(tmp_path); sid=make_project(s)['cross_study_synthesis_id']; assert 'cross-study-synthesis-meta-research-snapshot' in JOB_TYPES
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_cross_study_synthesis_meta_research_store',lambda:s)
    events=[]; claim=JobClaim(job_id='job-1160',job_type='cross-study-synthesis-meta-research-snapshot',payload={'snapshot':{'actor_ref':'lead','cross_study_synthesis_id':sid}},attempts=1,max_attempts=3,worker_id='w')
    out=asyncio.run(execute_job(claim,lambda stage,percent:events.append((stage,percent))))
    assert out['schema']==CROSS_STUDY_SYNTHESIS_SNAPSHOT_SCHEMA and events[-1]==('cross-study-synthesis-meta-research-snapshot-ready',95)
    from app.main import app; paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/cross-study-synthesis-meta-research/capabilities','/v1/core/cross-study-synthesis-meta-research/projects','/v1/core/cross-study-synthesis-meta-research/projects/{cross_study_synthesis_id}/study-matrix','/v1/core/cross-study-synthesis-meta-research/projects/{cross_study_synthesis_id}/runtime-handoffs','/v1/core/cross-study-synthesis-meta-research/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get('/v1/core/cross-study-synthesis-meta-research/capabilities').status_code in {401,503}
    ok=client.get('/v1/core/cross-study-synthesis-meta-research/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['automatic_meta_analysis'] is False

def test_unified_environment_accepts_cross_study_binding(tmp_path):
    from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
    from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
    s=make_store(tmp_path); sid=make_project(s)['cross_study_synthesis_id']
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/'env.sqlite3',cross_study_synthesis_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='lead',title='Unified',project_ref='p',cross_study_synthesis_ids=[sid]))
    line=env.lineage(rec['environment_id']); ready=env.readiness(rec['environment_id'])
    assert len(line['research_design']['cross_study_syntheses'])==1 and ready['dimensions']['cross_study_synthesis_bound'] is True

def test_capabilities_guardrails_are_explicit():
    cap=capabilities(); assert cap['milestone']=='11.6' and cap['study_registry'] is True and cap['meta_research_observations'] is True
    assert cap['specialist_runtimes_own_meta_analysis_execution'] is True and cap['platform_core_remains_governed_research_object_authority'] is True
    assert cap['automatic_study_inclusion'] is False and cap['automatic_risk_of_bias_judgment'] is False and cap['automatic_meta_analysis'] is False
    assert cap['automatic_publication_bias_verdict'] is False and cap['automatic_claim_acceptance'] is False and cap['automatic_causal_inference'] is False and cap['automatic_execution'] is False and cap['automatic_truth_promotion'] is False
