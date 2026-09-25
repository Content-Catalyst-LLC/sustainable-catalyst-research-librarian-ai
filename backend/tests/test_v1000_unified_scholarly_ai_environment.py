from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient

from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.unified_scholarly_ai_environment import (
    UnifiedResearchEnvironmentCreateRequest, UnifiedResearchEnvironmentBindingRequest,
    UnifiedResearchEnvironmentSnapshotRequest,
)
from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore, capabilities
from app.services.document_jobs import execute_job

class WorkflowStore:
    def get(self,ref): return {"workflow_id":ref,"state":"running"}
class ScholarlyStore:
    def get(self,ref): return {"study_id":ref,"protocol":{"frozen":True},"results":[{"result_id":"r1"}]}
    def readiness(self,ref): return {"study_id":ref,"ready":True,"blockers":[]}
class PeerStore:
    def get(self,ref,create_if_missing=False): return {"study_id":ref,"reviews":[{"review_id":"rev1"}]}
    def readiness(self,ref): return {"study_id":ref,"ready":True,"blockers":[]}
class PublicationStore:
    def get(self,ref): return {"publication_id":ref,"state":"published","title":"Unified paper"}
class ContextStore:
    def lineage(self,ref): return {"context_id":ref,"model_version_ref":"core:model-version:1","retrieval_runs":[{"run_id":"run1"}]}
class EvalStore:
    def summary(self,ref): return {"evaluation_id":ref,"metrics":{"precision_at_k":0.8},"governance":{"no_winner_selection":True}}
class ExperimentStore:
    def summary(self,ref): return {"experiment_id":ref,"state":"completed","trial_count":2}
class ModelAwareStore:
    def lineage(self,ref): return {"record_id":ref,"ai":{"model_ref":"core:model:1"},"research_objects":{"finding_refs":["core:finding:1"]}}
    def get_exchange(self,ref): return {"exchange_id":ref,"destination":"workspace","receipts":[{"status":"imported"}]}
class GraphStore:
    def neighborhood(self,ref,limit=100): return {"root_node_ref":ref,"nodes":[{"node_ref":ref}],"edges":[]}

def make_store(tmp_path):
    return UnifiedScholarlyAIEnvironmentStore(
        tmp_path/"u.sqlite3", workflow_store=WorkflowStore(), scholarly_store=ScholarlyStore(), peer_store=PeerStore(),
        publication_store=PublicationStore(), context_store=ContextStore(), evaluation_store=EvalStore(),
        experiment_store=ExperimentStore(), model_aware_store=ModelAwareStore(), graph_store=GraphStore(),
    )

def req():
    return UnifiedResearchEnvironmentCreateRequest(
        actor_ref="researcher", title="Unified research environment", research_question="Can the scholarly and AI lineages be reproduced together?",
        project_ref="core:project:1", workflow_id="wf-1", study_id="study-1", publication_id="pub-1",
        context_ids=["ctx-1"], evaluation_ids=["eval-1"], experiment_ids=["exp-1"], model_aware_record_ids=["mair-1"],
        exchange_ids=["xprod-1"], knowledge_graph_node_refs=["publication:pub-1"], core_object_refs=["core:evidence:1"],
    )

def test_environment_create_is_idempotent_and_preserves_authority(tmp_path):
    store=make_store(tmp_path); a=store.create(req()); b=store.create(req())
    assert a["environment_id"]==b["environment_id"] and len(a["record_hash"])==64
    assert a["governance"]["environment_is_orchestration_and_lineage_not_new_authority"] is True
    assert a["governance"]["automatic_truth_promotion"] is False

def test_binding_is_unique_and_extensible(tmp_path):
    store=make_store(tmp_path); env=store.create(req())
    r=UnifiedResearchEnvironmentBindingRequest(actor_ref="researcher",component_type="core-object",ref="core:claim:2",role="supporting")
    a=store.bind(env["environment_id"],r); b=store.bind(env["environment_id"],r)
    refs=[x for x in b["bindings"] if x["ref"]=="core:claim:2"]
    assert len(refs)==1 and len(b["bindings"])==len(a["bindings"])

def test_lineage_unifies_scholarly_ai_graph_and_exchange(tmp_path):
    store=make_store(tmp_path); env=store.create(req()); line=store.lineage(env["environment_id"])
    assert line["scholarly"]["study"]["study_id"]=="study-1"
    assert line["ai"]["contexts"][0]["context_id"]=="ctx-1"
    assert line["ai"]["model_aware_records"][0]["record_id"]=="mair-1"
    assert line["knowledge"]["graph_nodes"][0]["root_node_ref"]=="publication:pub-1"
    assert line["exchange"]["packets"][0]["exchange_id"]=="xprod-1"
    assert line["governance"]["quality_or_truth_not_inferred"] is True

def test_readiness_is_structural_not_scientific_validity(tmp_path):
    store=make_store(tmp_path); env=store.create(req()); ready=store.readiness(env["environment_id"])
    assert ready["ready"] is True
    assert ready["dimensions"]["publication_bound"] is True
    assert ready["governance"]["readiness_is_structural_completeness_not_scientific_validity"] is True

def test_readiness_reports_missing_scholarly_and_ai_lineage(tmp_path):
    store=make_store(tmp_path)
    env=store.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="r",title="Bare",project_ref="core:project:2"))
    ready=store.readiness(env["environment_id"])
    assert ready["ready"] is False
    assert "scholarly-lineage-bound" in ready["blockers"] and "ai-lineage-bound" in ready["blockers"]

def test_dossier_has_unified_lifecycle_without_new_truth_authority(tmp_path):
    store=make_store(tmp_path); env=store.create(req()); d=store.dossier(env["environment_id"])
    assert d["schema"]=="sc-research-librarian-unified-scholarly-ai-research-dossier/1.0"
    assert "peer-review-and-replication" in d["lifecycle"] and "model-aware-lineage" in d["lifecycle"]
    assert d["governance"]["dossier_is_assembled_view_not_new_source_of_truth"] is True

def test_snapshot_and_durable_job(tmp_path,monkeypatch):
    store=make_store(tmp_path); env=store.create(req())
    snap=store.freeze_snapshot(UnifiedResearchEnvironmentSnapshotRequest(actor_ref="r",environment_id=env["environment_id"]))
    assert len(snap["snapshot_hash"])==64 and snap["dossier"]["environment"]["environment_id"]==env["environment_id"]
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_unified_scholarly_ai_environment_store",lambda:store)
    claim=JobClaim(job_id="job-1000",job_type="unified-research-environment-snapshot",payload={"snapshot":{"actor_ref":"r","environment_id":env["environment_id"]}},attempts=1,max_attempts=3,worker_id="w")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["schema"]=="sc-research-librarian-unified-scholarly-ai-research-snapshot/1.0"
    assert events[-1]==("unified-research-environment-snapshot-ready",95)
    assert "unified-research-environment-snapshot" in JOB_TYPES

def test_capabilities_and_authenticated_v1000_api_surface():
    cap=capabilities(); assert cap["milestone"]=="10.0" and cap["automatic_execution"] is False and cap["automatic_model_selection"] is False
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/unified-research-environment/capabilities","/v1/core/unified-research-environment/environments",
        "/v1/core/unified-research-environment/environments/{environment_id}","/v1/core/unified-research-environment/environments/{environment_id}/bindings",
        "/v1/core/unified-research-environment/environments/{environment_id}/lineage","/v1/core/unified-research-environment/environments/{environment_id}/readiness",
        "/v1/core/unified-research-environment/environments/{environment_id}/dossier","/v1/core/unified-research-environment/snapshots/freeze",
    }
    assert not(required-paths),required-paths
    client=TestClient(app); resp=client.get("/v1/core/unified-research-environment/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert resp.status_code==200 and resp.json()["component_authority_remains_with_source_system"] is True
