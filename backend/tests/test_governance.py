from __future__ import annotations
import os, uuid
os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")
from fastapi.testclient import TestClient
from app.main import app
from app.governance import evaluate_release_gate, sanitize_governance_policy
from app.store import store

client=TestClient(app); HEADERS={"X-SC-RL-Key":"test-key"}

def _sync():
    response=client.post("/v1/knowledge/sync",headers=HEADERS,json={"mode":"upsert","job_id":"gov-"+uuid.uuid4().hex,"records":[{"id":"post:governance","title":"Research Quality and Governance","url":"https://sustainablecatalyst.com/research-quality-governance/","summary":"Governance, citations, source review, and quality gates.","content":"Research quality requires citation verification, human review, release gates, and privacy-minimized answer traces.","modified_utc":"2026-07-14T00:00:00+00:00"}]})
    assert response.status_code==200

def test_policy_is_sanitized_and_requires_reviewer_for_update():
    current=client.get('/v1/governance/policy',headers=HEADERS)
    assert current.status_code==200
    assert current.json()['policy']['schema']=='sc-research-governance-policy/1.0'
    rejected=client.post('/v1/governance/policy',headers=HEADERS,json={'policy':{'profile':'x'}})
    assert rejected.status_code==409
    updated=client.post('/v1/governance/policy',headers=HEADERS,json={'policy':{'profile':'test-governance','retention':{'store_query_text':False}},'reviewer':'Test Reviewer','reason':'test'})
    assert updated.status_code==200
    assert updated.json()['policy']['profile']=='test-governance'

def test_source_exclusion_requires_human_and_filters_retrieval():
    _sync()
    rejected=client.post('/v1/governance/sources',headers=HEADERS,json={'record_id':'post:governance','state':'excluded'})
    assert rejected.status_code==409
    accepted=client.post('/v1/governance/sources',headers=HEADERS,json={'record_id':'post:governance','state':'excluded','reviewer':'Test Reviewer','note':'test exclusion'})
    assert accepted.status_code==200
    result=client.post('/v1/retrieve/explain',headers=HEADERS,json={'query':'Research Quality and Governance','limit':5})
    assert all(item['id']!='post:governance' for item in result.json()['matches'])
    # restore for later tests
    client.post('/v1/governance/sources',headers=HEADERS,json={'record_id':'post:governance','state':'approved','reviewer':'Test Reviewer'})

def test_ask_creates_privacy_minimized_trace():
    _sync()
    response=client.post('/v1/ask',headers=HEADERS,json={'question':'What does Research Quality and Governance require?','session_id':'governance-test'})
    assert response.status_code==200, response.text
    body=response.json()
    trace_id=body['provenance']['answer_trace_id']
    trace=client.get('/v1/governance/traces/'+trace_id,headers=HEADERS).json()['trace']
    assert trace['schema']=='sc-research-answer-trace/1.0'
    assert trace['prompt_version']=='research-librarian-answer-v7.1.2'
    assert 'query' not in trace
    assert 'answer' not in trace
    assert trace['trace_fingerprint']

def test_release_gate_blocks_critical_citation_failure_and_records_history():
    metrics={'exact_title_accuracy':.98,'hit_at_3':.95,'citation_precision':.5,'citation_completeness':.6,'unsupported_claim_rate':.2,'route_accuracy':.9,'pdf_page_accuracy':.9,'fallback_success':1,'mean_answer_quality':.9}
    result=client.post('/v1/governance/release-gate',headers=HEADERS,json={'release_version':'7.1.2-test','metrics':metrics,'persist':True})
    assert result.status_code==200
    assert result.json()['report']['decision']=='block'
    assert result.json()['ok'] is False
    history=client.get('/v1/governance/release-gate/history',headers=HEADERS).json()['runs']
    assert any(item['release_version']=='7.1.2-test' for item in history)

def test_release_override_requires_named_human():
    metrics={'exact_title_accuracy':1,'hit_at_3':1,'citation_precision':1,'citation_completeness':1,'unsupported_claim_rate':0,'route_accuracy':1,'pdf_page_accuracy':1,'fallback_success':1,'mean_answer_quality':1}
    missing=client.post('/v1/governance/release-gate',headers=HEADERS,json={'release_version':'7.1.2','metrics':metrics,'override':True})
    assert missing.status_code==409
    approved=client.post('/v1/governance/release-gate',headers=HEADERS,json={'release_version':'7.1.2','metrics':metrics,'override':True,'reviewer':'Release Reviewer'})
    assert approved.status_code==200
    assert approved.json()['report']['decision']=='human-override'

def test_methodology_public_and_retention_dry_run():
    methodology=client.get('/v1/governance/methodology')
    assert methodology.status_code==200
    assert methodology.json()['methodology']['schema']=='sc-research-methodology/1.0'
    retention=client.post('/v1/governance/retention/run',headers=HEADERS,json={'dry_run':True})
    assert retention.status_code==200
    assert retention.json()['dry_run'] is True
