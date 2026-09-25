from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient
from app.async_jobs import AsyncJobStore, JobClaim
from app.contracts.research_workflow import ResearchWorkflowCreateRequest, ResearchWorkflowControlRequest, ResearchWorkflowApprovalRequest, ResearchWorkflowAdvanceRequest
from app.contracts.unified_research_runtime import UnifiedResearchRuntimePlan, UnifiedResearchRuntimePlanRequest
from app.services.unified_research_runtime import build_runtime_plan
from app.services.research_workflow import ResearchWorkflowStore, capabilities
from app.services.document_jobs import execute_job

def make_plan(stages=None):
    req=UnifiedResearchRuntimePlanRequest(core_project_id="core-910",local_project_id="local-910",title="Workflow study",research_question="What does the evidence show?",source_refs=["source:a"],core_evidence_refs=["evidence:a"],requested_stages=stages or ["retrieval","evidence-governance","research-intelligence"])
    return UnifiedResearchRuntimePlan.model_validate(build_runtime_plan(req)["plan"])

def make_store(tmp_path,monkeypatch):
    import app.async_jobs as aj
    jobs=AsyncJobStore(tmp_path/"jobs.sqlite3");monkeypatch.setattr(aj,"_job_store",jobs)
    import app.services.research_workflow as rw
    monkeypatch.setattr(rw,"get_job_store",lambda:jobs)
    return ResearchWorkflowStore(tmp_path/"workflows.sqlite3"),jobs

def test_create_idempotent_checkpointed(tmp_path,monkeypatch):
    s,_=make_store(tmp_path,monkeypatch);p=make_plan(["retrieval"])
    a,r1=s.create(ResearchWorkflowCreateRequest(plan=p));b,r2=s.create(ResearchWorkflowCreateRequest(plan=p))
    assert r1 is False and r2 is True and a["workflow_id"]==b["workflow_id"]
    assert s.checkpoints(a["workflow_id"]) and s.events(a["workflow_id"])
    assert capabilities()["automatic_core_writes"] is False

def test_pause_resume_cancel(tmp_path,monkeypatch):
    s,_=make_store(tmp_path,monkeypatch);w,_=s.create(ResearchWorkflowCreateRequest(plan=make_plan(["retrieval"])));wid=w["workflow_id"]
    assert s.control(wid,ResearchWorkflowControlRequest(action="start",actor_ref="researcher"))["state"]=="running"
    assert s.control(wid,ResearchWorkflowControlRequest(action="pause",actor_ref="researcher"))["state"]=="paused"
    assert s.control(wid,ResearchWorkflowControlRequest(action="resume",actor_ref="researcher"))["state"]=="running"
    assert s.control(wid,ResearchWorkflowControlRequest(action="cancel",actor_ref="researcher"))["state"]=="cancelled"

def test_human_gate_blocks_until_explicit_approval(tmp_path,monkeypatch):
    s,_=make_store(tmp_path,monkeypatch);w,_=s.create(ResearchWorkflowCreateRequest(plan=make_plan(["evidence-governance"])));wid=w["workflow_id"]
    s.control(wid,ResearchWorkflowControlRequest(action="start",actor_ref="r"))
    out=s.advance(wid,ResearchWorkflowAdvanceRequest(actor_ref="r"));assert out["workflow"]["stages"][0]["status"]=="awaiting-approval" and not out["scheduled_jobs"]
    s.approve(wid,ResearchWorkflowApprovalRequest(stage="evidence-governance",decision="approved",reviewer_ref="reviewer"))
    out=s.advance(wid,ResearchWorkflowAdvanceRequest(actor_ref="r"));assert out["workflow"]["stages"][0]["status"]=="awaiting-external"

def test_safe_stage_enqueued_idempotently(tmp_path,monkeypatch):
    s,jobs=make_store(tmp_path,monkeypatch);w,_=s.create(ResearchWorkflowCreateRequest(plan=make_plan(["retrieval"])));wid=w["workflow_id"]
    s.control(wid,ResearchWorkflowControlRequest(action="start",actor_ref="r"))
    out=s.advance(wid,ResearchWorkflowAdvanceRequest(actor_ref="r"));assert len(out["scheduled_jobs"])==1
    jid=out["scheduled_jobs"][0];assert jobs.get(jid)["job_type"]=="unified-research-runtime"
    assert s.advance(wid,ResearchWorkflowAdvanceRequest(actor_ref="r"))["scheduled_jobs"]==[]

def test_async_workflow_advance_job(tmp_path,monkeypatch):
    s,_=make_store(tmp_path,monkeypatch)
    import app.services.research_workflow as rw
    monkeypatch.setattr(rw,"_store",s)
    import app.services.document_jobs as dj
    monkeypatch.setattr(dj,"get_research_workflow_store",lambda:s)
    w,_=s.create(ResearchWorkflowCreateRequest(plan=make_plan(["retrieval"])));wid=w["workflow_id"];s.control(wid,ResearchWorkflowControlRequest(action="start",actor_ref="r"))
    claim=JobClaim(job_id="job-910",job_type="research-workflow-advance",payload={"workflow_id":wid,"advance":{"actor_ref":"automation","schedule_jobs":True,"max_new_jobs":1}},attempts=1,max_attempts=3,worker_id="worker")
    events=[];out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["workflow"]["workflow_id"]==wid and events[-1]==("workflow-checkpoint-ready",95)

def test_authenticated_api_surface():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={"/v1/core/research-workflows/capabilities","/v1/core/research-workflows","/v1/core/research-workflows/{workflow_id}","/v1/core/research-workflows/{workflow_id}/control","/v1/core/research-workflows/{workflow_id}/approvals","/v1/core/research-workflows/{workflow_id}/advance","/v1/core/research-workflows/{workflow_id}/events","/v1/core/research-workflows/{workflow_id}/checkpoints"}
    assert not(required-paths)
    body=TestClient(app).get("/v1/core/research-workflows/capabilities",headers={"X-SC-RL-Key":"test-key"}).json()
    assert body["release"]=="10.0.0" and body["durable"] is True and body["automatic_core_writes"] is False
