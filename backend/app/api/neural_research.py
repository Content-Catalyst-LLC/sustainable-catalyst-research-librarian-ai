from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import require_independent_access
from ..services.identity_session_access import IdentityAccessContext
from ..contracts.neural_research_intelligence import *
from ..services.neural_research_intelligence import (
    capabilities,
    get_neural_research_intelligence_store,
    neural_manifest,
)

router=APIRouter(
    prefix="/v1/research-librarian/neural-research",
    tags=["Research Librarian Neural Research Intelligence"],
)

def _store():
    return get_neural_research_intelligence_store()

def _call(fn,*args,**kwargs):
    try:
        return fn(*args,**kwargs)
    except ValueError as exc:
        message=str(exc)
        code=status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code,detail=message) from exc

@router.get("/manifest")
def manifest()->dict[str,Any]:
    return {"ok":True,"data":neural_manifest(),"resource":"neural-research-manifest"}

@router.get("/capabilities")
def neural_capabilities(
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":capabilities(),"resource":"neural-research-capabilities"}

@router.get("/projects")
def list_projects(
    limit:int=Query(default=100,ge=1,le=500),
    owner_ref:str=Query(default="",max_length=255),
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_store().list(limit,owner_ref),"resource":"neural-research-project-list"}

@router.post("/projects")
def create_project(
    payload:NeuralResearchCreateRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_store().create(payload),"resource":"neural-research-project"}

@router.get("/projects/{neural_research_id}")
def get_project(
    neural_research_id:str,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().get,neural_research_id),"resource":"neural-research-project"}

@router.post("/projects/{neural_research_id}/models")
def add_model_reference(
    neural_research_id:str,
    payload:NeuralModelReferenceAddRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().add_model_reference,neural_research_id,payload),"resource":"neural-model-reference"}

@router.post("/projects/{neural_research_id}/datasets")
def add_dataset_reference(
    neural_research_id:str,
    payload:NeuralDatasetReferenceAddRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().add_dataset_reference,neural_research_id,payload),"resource":"neural-dataset-reference"}

@router.post("/projects/{neural_research_id}/representations")
def add_representation_reference(
    neural_research_id:str,
    payload:NeuralRepresentationReferenceAddRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().add_representation_reference,neural_research_id,payload),"resource":"neural-representation-reference"}

@router.post("/projects/{neural_research_id}/inference-receipts")
def add_inference_receipt(
    neural_research_id:str,
    payload:NeuralInferenceReceiptAddRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().add_inference_receipt,neural_research_id,payload),"resource":"neural-inference-receipt"}

@router.post("/projects/{neural_research_id}/handoffs")
def prepare_handoff(
    neural_research_id:str,
    payload:NeuralRuntimeHandoffPrepareRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().prepare_handoff,neural_research_id,payload),"resource":"neural-runtime-handoff"}

@router.get("/projects/{neural_research_id}/lineage")
def lineage(
    neural_research_id:str,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().lineage,neural_research_id),"resource":"neural-research-lineage"}

@router.get("/projects/{neural_research_id}/readiness")
def readiness(
    neural_research_id:str,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().readiness,neural_research_id),"resource":"neural-research-readiness"}

@router.get("/projects/{neural_research_id}/core-candidate")
def core_candidate(
    neural_research_id:str,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().core_candidate,neural_research_id),"resource":"neural-core-candidate"}

@router.post("/projects/{neural_research_id}/state")
def set_state(
    neural_research_id:str,
    payload:NeuralResearchStateRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().set_state,neural_research_id,payload),"resource":"neural-research-project"}

@router.post("/snapshots/freeze")
def freeze_snapshot(
    payload:NeuralResearchSnapshotRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {"ok":True,"data":_call(_store().freeze_snapshot,payload),"resource":"neural-research-snapshot"}
