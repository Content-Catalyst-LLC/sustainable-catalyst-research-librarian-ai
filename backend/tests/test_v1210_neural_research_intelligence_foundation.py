import os
from pathlib import Path
import tempfile

os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
os.environ.setdefault("SC_RL_IDENTITY_COOKIE_SECURE","false")

from fastapi.testclient import TestClient

from app.contracts.neural_research_intelligence import (
    NeuralResearchCreateRequest,
    NeuralModelReferenceAddRequest,
    NeuralDatasetReferenceAddRequest,
    NeuralRepresentationReferenceAddRequest,
    NeuralInferenceReceiptAddRequest,
    NeuralRuntimeHandoffPrepareRequest,
    NeuralResearchSnapshotRequest,
)
from app.services.neural_research_intelligence import (
    NeuralResearchIntelligenceStore,
    neural_manifest,
    capabilities,
)

def _store(tmp_path):
    return NeuralResearchIntelligenceStore(sqlite_path=tmp_path/"neural.sqlite3")

def _project(store):
    return store.create(NeuralResearchCreateRequest(
        actor_ref="identity:test-owner",
        title="Neural retrieval robustness study",
        project_ref="project:test",
        research_question_ref="rq:test",
        objective="Trace model, dataset, representation, inference, and execution provenance.",
    ))

def test_manifest_and_capabilities_define_foundation_boundary():
    m=neural_manifest()
    c=capabilities()
    assert m["milestone"]=="12.1.0"
    assert m["wordpress_required"] is False
    assert m["runtime_authority"]=="python-fastapi-backend"
    assert m["database_migration"]=="041_neural_research_intelligence_foundation.sql"
    assert m["execution"]["librarian_executes_training"] is False
    assert m["execution"]["librarian_executes_inference"] is False
    assert m["authority"]["platform_core_model_contract_authority"] is True
    assert m["authority"]["specialist_runtime_execution_authority"] is True
    assert m["governance"]["model_weights_stored"] is False
    assert m["governance"]["secrets_stored"] is False
    assert m["governance"]["automatic_model_ranking"] is False
    assert m["next_boundary"]=="multilingual-cross-language-research-intelligence"
    assert c["model_provenance"] is True
    assert c["dataset_transformation_lineage"] is True
    assert c["representation_lineage"] is True
    assert c["runtime_handoffs"] is True

def test_neural_project_lineage_handoff_and_snapshot(tmp_path):
    store=_store(tmp_path)
    project=_project(store)
    rid=project["neural_research_id"]

    project=store.add_model_reference(rid,NeuralModelReferenceAddRequest(
        actor_ref="identity:test-owner",
        label="Encoder A",
        framework="pytorch",
        model_ref="workspace:model:encoder-a",
        model_hash="sha256:model-a",
        model_family="transformer",
        architecture="encoder",
        task_types=["retrieval","embedding"],
        checkpoint_ref="workspace:checkpoint:42",
        core_model_ref="core:neural-model:encoder-a",
    ))
    mid=project["model_references"][0]["model_reference_id"]

    project=store.add_dataset_reference(rid,NeuralDatasetReferenceAddRequest(
        actor_ref="identity:test-owner",
        label="Research corpus",
        dataset_ref="library:dataset:research-corpus",
        dataset_hash="sha256:dataset-a",
        split="validation",
        feature_schema_ref="core:feature-schema:1",
        transformation_refs=["workspace:transform:normalize","workspace:transform:tokenize"],
        core_dataset_ref="core:dataset:research-corpus",
    ))
    did=project["dataset_references"][0]["dataset_reference_id"]

    project=store.add_representation_reference(rid,NeuralRepresentationReferenceAddRequest(
        actor_ref="identity:test-owner",
        label="Validation embeddings",
        source_refs=["library:source:1","library:source:2"],
        model_reference_id=mid,
        dimensions=768,
        metric="cosine",
        vector_store_ref="workspace:artifact:embedding-set",
        transformation_refs=["workspace:transform:tokenize"],
        core_embedding_ref="core:embedding:validation",
    ))
    repid=project["representation_references"][0]["representation_reference_id"]

    project=store.add_inference_receipt(rid,NeuralInferenceReceiptAddRequest(
        actor_ref="identity:test-owner",
        model_reference_id=mid,
        input_refs=["library:source:1"],
        output_refs=["workspace:artifact:inference-1"],
        runtime_target="workspace",
        execution_ref="workspace:job:99",
        checkpoint_ref="workspace:checkpoint:42",
        parameters={"temperature":0},
        metrics={"latency_ms":23.0},
        provenance_note="Observed inference receipt; not a validity judgment.",
    ))
    assert project["inference_receipts"][0]["execution_performed_by_librarian"] is False

    handoff=store.prepare_handoff(rid,NeuralRuntimeHandoffPrepareRequest(
        actor_ref="identity:test-owner",
        target="research-lab",
        operation="evaluation",
        objective="Evaluate robustness under controlled perturbations.",
        model_reference_ids=[mid],
        dataset_reference_ids=[did],
        representation_reference_ids=[repid],
        expected_artifacts=["metrics","evaluation-report"],
    ))
    packet=handoff["handoff"]
    assert packet["execution_performed"] is False
    assert packet["librarian_executes"] is False
    assert packet["human_confirmation_required_at_target"] is True

    lineage=store.lineage(rid)
    assert lineage["models"][0]["core_model_ref"]=="core:neural-model:encoder-a"
    assert lineage["datasets"][0]["core_dataset_ref"]=="core:dataset:research-corpus"
    assert lineage["representations"][0]["core_embedding_ref"]=="core:embedding:validation"
    assert lineage["inference_receipts"][0]["execution_ref"]=="workspace:job:99"

    readiness=store.readiness(rid)
    assert readiness["ready_for_runtime_handoff"] is True
    assert readiness["governance"]["readiness_is_structural_not_model_recommendation"] is True

    core=store.core_candidate(rid)
    assert core["platform_core_authority_required"] is True
    assert core["automatic_core_write"] is False
    assert core["automatic_truth_promotion"] is False

    snap=store.freeze_snapshot(NeuralResearchSnapshotRequest(
        actor_ref="identity:test-owner",
        neural_research_id=rid,
        note="v12.1.0 foundation snapshot",
    ))
    assert len(snap["snapshot_hash"])==64
    assert snap["governance"]["snapshot_is_provenance_not_model_validity_certification"] is True

def test_invalid_cross_reference_fails_closed(tmp_path):
    store=_store(tmp_path)
    rid=_project(store)["neural_research_id"]

    try:
        store.add_representation_reference(rid,NeuralRepresentationReferenceAddRequest(
            actor_ref="identity:test-owner",
            label="Bad representation",
            source_refs=["library:source:1"],
            model_reference_id="modelref:missing",
            dimensions=128,
        ))
        assert False,"unknown model reference should fail"
    except ValueError as exc:
        assert "not registered" in str(exc)

def test_routes_auth_and_current_boundary(tmp_path):
    from app.services import neural_research_intelligence as neural_service
    neural_service._store=NeuralResearchIntelligenceStore(sqlite_path=tmp_path/"api-neural.sqlite3")

    from app.main import app
    client=TestClient(app)
    paths={getattr(r,"path","") for r in app.routes}

    assert "/v1/research-librarian/neural-research/manifest" in paths
    assert "/v1/research-librarian/neural-research/capabilities" in paths
    assert "/v1/research-librarian/neural-research/projects" in paths

    public=client.get("/v1/research-librarian/neural-research/manifest")
    assert public.status_code==200
    assert public.json()["data"]["milestone"]=="12.1.0"

    assert client.get("/v1/research-librarian/neural-research/capabilities").status_code==401
    cap=client.get(
        "/v1/research-librarian/neural-research/capabilities",
        headers={"X-SC-RL-Key":"test-key"},
    )
    assert cap.status_code==200
    assert cap.json()["data"]["runtime_handoffs"] is True

    created=client.post(
        "/v1/research-librarian/neural-research/projects",
        headers={"X-SC-RL-Key":"test-key"},
        json={
            "actor_ref":"identity:test-owner",
            "title":"API neural study",
            "objective":"Trace neural research provenance."
        },
    )
    assert created.status_code==200

    health=client.get("/health")
    assert health.status_code==200
    h=health.json()
    assert h["version"]=="12.1.0"
    assert h["neural_research_intelligence"] is True
    assert h["neural_research_runtime"]=="12.1.0"
    assert h["wordpress_required"] is False

    from app.services.independent_research_librarian_api import api_manifest,capabilities as independent_capabilities
    m=api_manifest()
    c=independent_capabilities()
    assert m["scope"]["neural_research_intelligence"] is True
    assert m["next_boundary"]=="multilingual-cross-language-research-intelligence"
    assert c["milestone"]=="12.1.0"
    assert c["neural_research_intelligence"] is True
    assert c["neural_runtime_execution"] is False

def test_v1208_independence_certification_remains_historical_boundary():
    from app.services.independent_deployment_certification import certification_manifest
    m=certification_manifest()
    assert m["milestone"]=="12.0.8"
    assert m["certification_target"]=="wordpress-unreachable-or-absent"
    assert m["wordpress_required"] is False
