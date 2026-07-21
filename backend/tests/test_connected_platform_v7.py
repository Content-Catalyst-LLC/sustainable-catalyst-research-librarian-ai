from __future__ import annotations
import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app); HEADERS={"X-SC-RL-Key":"test-key"}

def test_stable_api_manifest_and_summary():
    api=client.get('/v1/platform/api',headers=HEADERS)
    assert api.status_code==200
    body=api.json()
    assert body['schema']=='sc-connected-research-api/1.0'
    assert body['stability']=='stable-v7'
    assert body['generation_boundary']['fallback']=='deterministic'
    summary=client.get('/v1/platform/summary',headers=HEADERS).json()
    assert summary['version']=='7.0.3'
    assert summary['workspace_schema']=='sc-research-librarian-public-workspace/2.0'

def test_project_investigation_entities_and_bundle():
    project=client.post('/v1/projects',headers=HEADERS,json={'title':'Connected Climate Research','objective':'Compare evidence and prepare reusable analysis.'})
    assert project.status_code==200, project.text
    project_id=project.json()['project_id']
    assert project.json()['schema']=='sc-research-project/1.0'
    inv=client.post('/v1/investigations',headers=HEADERS,json={'project_id':project_id,'title':'Indicator investigation','question':'Which indicators disagree?'})
    assert inv.status_code==200
    entity=client.post('/v1/projects/entities',headers=HEADERS,json={'project_id':project_id,'entity_type':'evidence','title':'Verified evidence','payload':{'record_id':'post:1','annotation':'Primary source'}})
    assert entity.status_code==200
    bundle=client.get('/v1/projects/'+project_id,headers=HEADERS)
    assert bundle.status_code==200
    assert len(bundle.json()['investigations'])>=1
    assert any(item['entity_type']=='evidence' for item in bundle.json()['entities'])

def test_workflow_contradiction_uncertainty_and_backup_roundtrip():
    project=client.post('/v1/projects',headers=HEADERS,json={'title':'Governed systems project'}).json()
    project_id=project['project_id']
    workflow=client.post('/v1/workflows/template',headers=HEADERS,json={'project_id':project_id,'kind':'decision-packet','persist':True})
    assert workflow.status_code==200
    contradiction=client.post('/v1/research/contradictions',headers=HEADERS,json={'project_id':project_id,'items':[{'claim_key':'c1','claim':'The trend is increasing','position':'supports','evidence_id':'e1'},{'claim_key':'c1','claim':'The trend is increasing','position':'opposes','evidence_id':'e2'}]})
    assert contradiction.status_code==200
    assert contradiction.json()['conflict_count']==1
    uncertainty=client.post('/v1/research/uncertainties',headers=HEADERS,json={'project_id':project_id,'items':[{'statement':'Data freshness may change the conclusion','likelihood':.8,'impact':.9}]})
    assert uncertainty.status_code==200
    assert uncertainty.json()['items'][0]['priority']==.72
    backup=client.post(f'/v1/projects/{project_id}/backup',headers=HEADERS)
    assert backup.status_code==200
    envelope=backup.json()
    dry=client.post('/v1/platform/backups/import',headers=HEADERS,json={'envelope':envelope,'dry_run':True})
    assert dry.status_code==200
    assert dry.json()['verification']['ok'] is True
    tampered={**envelope,'payload':{**envelope['payload'],'project':{**envelope['payload']['project'],'title':'Tampered'}}}
    invalid=client.post('/v1/platform/backups/import',headers=HEADERS,json={'envelope':tampered,'dry_run':True})
    assert invalid.status_code==422
