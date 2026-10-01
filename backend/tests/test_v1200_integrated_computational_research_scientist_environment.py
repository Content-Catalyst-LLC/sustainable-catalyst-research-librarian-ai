import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
import asyncio
from fastapi.testclient import TestClient

from app.contracts.integrated_computational_research_scientist_environment import *
from app.services.integrated_computational_research_scientist_environment import IntegratedComputationalResearchScientistEnvironmentStore,capabilities
from app.async_jobs import JOB_TYPES,JobClaim
from app.services.document_jobs import execute_job

def unified(ref):
    if ref=="missing": raise ValueError("missing")
    return {"environment":{"environment_id":ref,"record_hash":"unified-hash","title":"Unified"},"readiness":{"ready":True}}

def make_store(tmp_path):
    return IntegratedComputationalResearchScientistEnvironmentStore(tmp_path/"scientist.sqlite3",unified_environment_resolver=unified)

def make_env(s):
    return s.create(ScientistEnvironmentCreateRequest(actor_ref="lead",title="Integrated scientist environment",project_ref="project-1",unified_environment_ref="unified-1",research_question="What does the evidence support?",objective="Run a reproducible research program."))

def seed(s,eid):
    r=s.add_stage(eid,ScientistStageAddRequest(actor_ref="lead",stage_type="statistical-analysis",label="Primary analysis",source_refs=["sap-1"],entry_criteria=["data ready"],exit_criteria=["analysis reviewed"]))
    sid=r["stages"][0]["stage_id"]
    r=s.add_work_package(eid,ScientistWorkPackageAddRequest(actor_ref="lead",stage_id=sid,work_package_type="statistics",label="Primary model",research_task="Run preregistered primary model.",input_refs=["dataset-1","sap-1"],expected_outputs=["model-output"]))
    wid=r["work_packages"][0]["work_package_id"]
    return sid,wid

def test_create_preserves_authority_and_guardrails(tmp_path):
    s=make_store(tmp_path); r=make_env(s)
    assert r["schema"]==SCIENTIST_ENVIRONMENT_SCHEMA
    assert r["unified_environment_hash"]=="unified-hash"
    assert r["governance"]["source_component_authority_preserved"] is True
    assert r["governance"]["automatic_execution"] is False
    assert r["governance"]["automatic_truth_promotion"] is False

def test_missing_unified_environment_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try:s.create(ScientistEnvironmentCreateRequest(actor_ref="x",title="x",project_ref="p",unified_environment_ref="missing"))
    except ValueError as e: assert "unified research environment" in str(e)
    else: raise AssertionError("expected fail closed")

def test_runtime_handoff_requires_human_approval(tmp_path):
    s=make_store(tmp_path); eid=make_env(s)["scientist_environment_id"]; sid,wid=seed(s,eid)
    r=s.add_runtime_handoff(eid,ScientistRuntimeHandoffAddRequest(actor_ref="lead",work_package_id=wid,runtime_target="workspace",execution_spec={"runtime":"python","entrypoint":"analysis.py"},expected_artifacts=["model-output"]))
    hid=r["runtime_handoffs"][0]["runtime_handoff_id"]
    assert s.runtime_handoffs(eid)["packets"]==[]
    s.decide(eid,ScientistObjectDecisionRequest(actor_ref="lead",object_type="runtime-handoff",object_id=hid,decision="approved",rationale="Approved execution."))
    assert len(s.runtime_handoffs(eid)["packets"])==1
    r=s.add_execution_receipt(eid,ScientistExecutionReceiptAddRequest(actor_ref="workspace",runtime_handoff_id=hid,execution_ref="run-1",status="completed",runtime_version="python-3.12",artifact_refs=["model-output"]))
    assert r["execution_receipts"][0]["receipt_is_observation_not_scientific_verdict"] is True

def test_interpretation_and_checkpoint_are_human_records(tmp_path):
    s=make_store(tmp_path); eid=make_env(s)["scientist_environment_id"]; sid,wid=seed(s,eid)
    r=s.add_runtime_handoff(eid,ScientistRuntimeHandoffAddRequest(actor_ref="lead",work_package_id=wid,runtime_target="workspace",execution_spec={}))
    hid=r["runtime_handoffs"][0]["runtime_handoff_id"]
    s.decide(eid,ScientistObjectDecisionRequest(actor_ref="lead",object_type="runtime-handoff",object_id=hid,decision="approved"))
    r=s.add_execution_receipt(eid,ScientistExecutionReceiptAddRequest(actor_ref="workspace",runtime_handoff_id=hid,execution_ref="run-1",status="completed"))
    receipt=r["execution_receipts"][0]["execution_receipt_id"]
    r=s.add_interpretation(eid,ScientistInterpretationAddRequest(actor_ref="researcher",work_package_id=wid,execution_receipt_ids=[receipt],interpretation="The model output is consistent with the prespecified analysis, subject to uncertainty.",uncertainties=["sampling error"]))
    assert r["interpretations"][0]["human_authored"] is True
    r=s.add_checkpoint(eid,ScientistCheckpointAddRequest(actor_ref="researcher",stage_id=sid,label="Primary analysis review",review_question="Is this stage ready to proceed?"))
    cid=r["checkpoints"][0]["checkpoint_id"]
    s.decide_checkpoint(eid,ScientistCheckpointDecisionRequest(actor_ref="reviewer",checkpoint_id=cid,status="approved",rationale="Reviewed."))
    assert s.get(eid)["checkpoints"][0]["status"]=="approved"

def test_readiness_dossier_core_snapshot(tmp_path):
    s=make_store(tmp_path); eid=make_env(s)["scientist_environment_id"]; sid,wid=seed(s,eid)
    r=s.add_runtime_handoff(eid,ScientistRuntimeHandoffAddRequest(actor_ref="lead",work_package_id=wid,runtime_target="workspace",execution_spec={}))
    hid=r["runtime_handoffs"][0]["runtime_handoff_id"]
    s.decide(eid,ScientistObjectDecisionRequest(actor_ref="lead",object_type="runtime-handoff",object_id=hid,decision="approved"))
    r=s.add_execution_receipt(eid,ScientistExecutionReceiptAddRequest(actor_ref="workspace",runtime_handoff_id=hid,execution_ref="run-1",status="completed"))
    receipt=r["execution_receipts"][0]["execution_receipt_id"]
    s.add_interpretation(eid,ScientistInterpretationAddRequest(actor_ref="researcher",work_package_id=wid,execution_receipt_ids=[receipt],interpretation="Human interpretation."))
    ready=s.readiness(eid); dossier=s.dossier(eid); cand=s.core_candidate(eid)
    snap=s.freeze_snapshot(ScientistEnvironmentSnapshotRequest(actor_ref="lead",scientist_environment_id=eid))
    assert ready["ready_for_reproducible_dossier"] is True
    assert dossier["governance"]["human_scholarly_judgment_required"] is True
    assert cand["scientific_validity_not_certified"] is True and cand["truth_promoted"] is False
    assert len(snap["snapshot_hash"])==64

def test_durable_job_and_authenticated_api(tmp_path,monkeypatch):
    s=make_store(tmp_path); eid=make_env(s)["scientist_environment_id"]; seed(s,eid)
    assert "integrated-computational-research-scientist-environment-snapshot" in JOB_TYPES
    import app.services.document_jobs as dj
    monkeypatch.setattr(dj,"get_integrated_computational_research_scientist_environment_store",lambda:s)
    events=[]
    claim=JobClaim(job_id="job-1200",job_type="integrated-computational-research-scientist-environment-snapshot",payload={"snapshot":{"actor_ref":"lead","scientist_environment_id":eid}},attempts=1,max_attempts=3,worker_id="w")
    out=asyncio.run(execute_job(claim,lambda st,p:events.append((st,p))))
    assert out["schema"]==SCIENTIST_ENVIRONMENT_SNAPSHOT_SCHEMA
    assert events[-1]==("integrated-computational-research-scientist-environment-snapshot-ready",95)
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
      "/v1/core/integrated-computational-research-scientist-environment/capabilities",
      "/v1/core/integrated-computational-research-scientist-environment/environments",
      "/v1/core/integrated-computational-research-scientist-environment/environments/{scientist_environment_id}/dossier",
      "/v1/core/integrated-computational-research-scientist-environment/snapshots/freeze",
    }
    assert not(required-paths)
    client=TestClient(app)
    assert client.get("/v1/core/integrated-computational-research-scientist-environment/capabilities").status_code in {401,503}
    ok=client.get("/v1/core/integrated-computational-research-scientist-environment/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert ok.status_code==200 and ok.json()["automatic_execution"] is False

def test_capabilities_guardrails():
    c=capabilities()
    assert c["milestone"]=="12.0" and c["reproducible_scientist_dossier"] is True
    assert c["source_component_authority_preserved"] is True and c["specialist_runtimes_own_execution"] is True
    assert c["automatic_execution"] is False and c["automatic_model_selection"] is False
    assert c["automatic_causal_inference"] is False and c["automatic_scientific_validity_verdict"] is False
    assert c["automatic_scholarly_judgment"] is False and c["automatic_truth_promotion"] is False
