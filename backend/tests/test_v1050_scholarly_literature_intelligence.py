import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from pathlib import Path
import asyncio
from fastapi.testclient import TestClient

from app.async_jobs import JOB_TYPES, JobClaim
from app.contracts.scholarly_literature_intelligence import (
    LiteratureIntelligenceCreateRequest, LiteratureWorkAddRequest, CitationContextAddRequest,
    LiteratureStrandAddRequest, LiteratureGapAddRequest, SeminalCandidateAddRequest,
    RelatedWorkCandidateAddRequest, RelatedWorkDecisionRequest, LiteratureIntelligenceStateRequest,
    LiteratureIntelligenceSnapshotRequest,
)
from app.services.scholarly_literature_intelligence import ScholarlyLiteratureIntelligenceStore, capabilities
from app.services.document_jobs import execute_job
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest

class FakeReviewStore:
    def get(self, rid):
        return {"review_id":rid,"question_plan_id":"q-1","research_design_plan_id":"d-1","evidence_search_strategy_id":"s-1","review_question":"How does storage shape renewable-market price volatility?","record_hash":"a"*64,"candidates":[{"candidate_id":"c1","source_ref":"library:doc:1"},{"candidate_id":"c2","source_ref":"library:doc:2"}],"screening_decisions":[{"candidate_id":"c1","stage":"full-text","decision":"include"},{"candidate_id":"c2","stage":"full-text","decision":"exclude"}]}

def make(tmp_path):
    store=ScholarlyLiteratureIntelligenceStore(tmp_path/'lit.sqlite3',systematic_review_store=FakeReviewStore())
    rec=store.create(LiteratureIntelligenceCreateRequest(actor_ref='r',project_ref='core:project:grad-5',systematic_review_id='review-1',title='Grid literature intelligence'))
    return store,rec

def add_two(store,iid):
    a=store.add_work(iid,LiteratureWorkAddRequest(actor_ref='r',source_ref='doi:10.1/a',title='Foundational storage study',publication_year=2012,authors=['A Author']))
    b=store.add_work(iid,LiteratureWorkAddRequest(actor_ref='r',source_ref='doi:10.1/b',title='Recent market study',publication_year=2025,authors=['B Author']))
    works={w['source_ref']:w for w in b['works']}
    return works['doi:10.1/a']['work_id'],works['doi:10.1/b']['work_id']

def test_create_inherits_systematic_review_and_included_corpus(tmp_path):
    store,rec=make(tmp_path)
    assert rec['research_question'].startswith('How does storage') and rec['question_plan_id']=='q-1'
    assert [w['source_ref'] for w in rec['works']]==['library:doc:1']
    assert rec['systematic_review_fingerprint']=='a'*64
    assert rec['governance']['automatic_seminal_work_classification'] is False

def test_citation_context_and_descriptive_matrix_do_not_rank_quality(tmp_path):
    store,rec=make(tmp_path); a,b=add_two(store,rec['intelligence_id'])
    store.add_citation_context(rec['intelligence_id'],CitationContextAddRequest(actor_ref='reviewer',citing_work_id=b,cited_work_id=a,function='background',context_excerpt='Prior storage work established the baseline.',source_locator_ref='doi:10.1/b#p4'))
    matrix=store.citation_matrix(rec['intelligence_id'])
    assert matrix['citation_function_counts']['background']==1
    row=next(x for x in matrix['descriptive_visibility_indicators'] if x['work_id']==a)
    assert row['inbound_registered_citations']==1
    assert matrix['governance']['counts_are_corpus_descriptors_not_quality_or_authority_scores'] is True

def test_strands_gaps_and_seminal_candidates_are_human_declared(tmp_path):
    store,rec=make(tmp_path); a,b=add_two(store,rec['intelligence_id']); iid=rec['intelligence_id']
    store.add_strand(iid,LiteratureStrandAddRequest(actor_ref='reviewer',label='Storage buffering',work_ids=[a,b],rationale='Human thematic grouping.'))
    store.add_gap(iid,LiteratureGapAddRequest(actor_ref='reviewer',gap_type='geographic',label='Regional evidence gap',description='Few studies cover smaller balancing areas.',work_ids=[b]))
    store.add_seminal_candidate(iid,SeminalCandidateAddRequest(actor_ref='reviewer',work_id=a,rationale='Frequently used as historical baseline in this corpus.'))
    land=store.landscape(iid)
    assert land['literature_strands'][0]['human_labeled'] is True and land['gaps'][0]['human_declared'] is True
    assert land['seminal_candidates'][0]['classification_performed'] is False

def test_related_work_requires_human_acceptance_before_graph_handoff(tmp_path):
    store,rec=make(tmp_path); a,b=add_two(store,rec['intelligence_id']); iid=rec['intelligence_id']
    x=store.add_related_work_candidate(iid,RelatedWorkCandidateAddRequest(actor_ref='r',source_work_id=a,target_work_id=b,relation='extends',basis='Shared design lineage.'))
    cand=x['related_work_candidates'][0]; assert cand['decision']=='pending' and store.graph_handoffs(iid)['edge_candidates']==[]
    store.decide_related_work(iid,RelatedWorkDecisionRequest(actor_ref='reviewer',candidate_id=cand['candidate_id'],decision='accepted',rationale='Reviewed relationship.'))
    out=store.graph_handoffs(iid); assert out['edge_candidates'][0]['relation']=='extends' and out['write_performed'] is False

def test_core_candidate_requires_human_approved_state_for_approved_status(tmp_path):
    store,rec=make(tmp_path); iid=rec['intelligence_id']; assert store.core_candidate(iid)['handoff_status']=='draft-candidate'
    store.set_state(iid,LiteratureIntelligenceStateRequest(actor_ref='pi',state='approved',note='Literature annotations reviewed.'))
    out=store.core_candidate(iid); assert out['handoff_status']=='human-approved-candidate' and out['promotion_performed'] is False
    assert out['governance']['platform_core_remains_authority'] is True

def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    store,rec=make(tmp_path); iid=rec['intelligence_id']; snap=store.freeze_snapshot(LiteratureIntelligenceSnapshotRequest(actor_ref='r',intelligence_id=iid)); assert len(snap['snapshot_hash'])==64
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,'get_scholarly_literature_intelligence_store',lambda:store)
    claim=JobClaim(job_id='job-1050',job_type='scholarly-literature-intelligence-snapshot',payload={'snapshot':{'actor_ref':'r','intelligence_id':iid}},attempts=1,max_attempts=3,worker_id='w')
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out['schema']=='sc-research-librarian-scholarly-literature-intelligence-snapshot/1.0' and events[-1]==('scholarly-literature-intelligence-snapshot-ready',95)
    assert 'scholarly-literature-intelligence-snapshot' in JOB_TYPES

def test_capabilities_and_authenticated_api_surface():
    cap=capabilities(); assert cap['milestone']=='10.5' and cap['automatic_authority_ranking'] is False and cap['automatic_impact_scoring'] is False
    from app.main import app
    paths={getattr(r,'path','') for r in app.routes}; required={'/v1/core/scholarly-literature-intelligence/capabilities','/v1/core/scholarly-literature-intelligence/projects','/v1/core/scholarly-literature-intelligence/projects/{intelligence_id}/citation-contexts','/v1/core/scholarly-literature-intelligence/projects/{intelligence_id}/landscape','/v1/core/scholarly-literature-intelligence/projects/{intelligence_id}/citation-matrix','/v1/core/scholarly-literature-intelligence/projects/{intelligence_id}/graph-handoffs','/v1/core/scholarly-literature-intelligence/projects/{intelligence_id}/core-candidate','/v1/core/scholarly-literature-intelligence/snapshots/freeze'}
    assert not(required-paths),required-paths
    client=TestClient(app); assert client.get('/v1/core/scholarly-literature-intelligence/capabilities').status_code==401
    ok=client.get('/v1/core/scholarly-literature-intelligence/capabilities',headers={'X-SC-RL-Key':'test-key'}); assert ok.status_code==200 and ok.json()['human_gap_declaration_required'] is True

def test_guardrails_preserve_graph_library_and_core_authority():
    cap=capabilities()
    for key in ['automatic_authority_ranking','automatic_impact_scoring','automatic_seminal_work_classification','automatic_literature_gap_claims','automatic_graph_write','automatic_truth_promotion']: assert cap[key] is False
    assert cap['research_knowledge_graph_remains_citation_graph_authority'] is True and cap['knowledge_library_remains_source_authority'] is True and cap['platform_core_remains_authority'] is True

def test_unified_environment_can_bind_literature_intelligence(tmp_path):
    store,rec=make(tmp_path); iid=rec['intelligence_id']
    envs=UnifiedScholarlyAIEnvironmentStore(tmp_path/'e.sqlite3',literature_intelligence_store=store)
    env=envs.create(UnifiedResearchEnvironmentCreateRequest(actor_ref='r',title='Program',project_ref='core:project:grad-5',literature_intelligence_ids=[iid]))
    line=envs.lineage(env['environment_id']); assert line['research_design']['literature_intelligence'][0]['project']['intelligence_id']==iid
    assert envs.readiness(env['environment_id'])['dimensions']['literature_intelligence_bound'] is True
