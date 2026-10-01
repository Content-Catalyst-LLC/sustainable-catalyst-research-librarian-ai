from __future__ import annotations
import hashlib,hmac
from typing import Any

from fastapi import APIRouter,Depends,Header,HTTPException,Query,status

from ..config import settings
from ..models import ResearchProjectRequest
from ..contracts.independent_research_librarian_api import (
    IndependentRetrievalRequest,
    IndependentAPIContractSnapshotRequest,
)
from ..services.independent_research_librarian_api import (
    envelope,
    api_manifest,
    status_payload,
    retrieve_payload,
    list_projects,
    create_project,
    get_project,
    project_investigations,
    scientist_environment,
    scientist_dossier,
    runtime_authority_payload,
    capabilities,
    get_independent_api_contract_snapshot_store,
)

router=APIRouter(prefix="/v1/research-librarian",tags=["Independent Research Librarian API v1"])

def require_independent_api_key(x_sc_rl_key:str=Header(default="",alias="X-SC-RL-Key"))->None:
    if not settings.api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,detail="SC_RL_BACKEND_API_KEY is not configured on the backend.")
    supplied=hashlib.sha256((x_sc_rl_key or "").encode()).digest()
    expected=hashlib.sha256(settings.api_key.encode()).digest()
    if not x_sc_rl_key or not hmac.compare_digest(supplied,expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Research Librarian API key.")

auth=[Depends(require_independent_api_key)]

def _not_found(exc:Exception)->HTTPException:
    if isinstance(exc,ValueError):
        return HTTPException(status_code=404,detail=str(exc))
    return HTTPException(status_code=500,detail=str(exc))

@router.get("/manifest",dependencies=auth)
def independent_manifest()->dict[str,Any]:
    return envelope(api_manifest(),resource="api-manifest")

@router.get("/capabilities",dependencies=auth)
def independent_capabilities()->dict[str,Any]:
    return envelope(capabilities(),resource="api-capabilities")

@router.get("/status",dependencies=auth)
def independent_status()->dict[str,Any]:
    return envelope(status_payload(),resource="service-status")

@router.post("/retrieve",dependencies=auth)
async def independent_retrieve(req:IndependentRetrievalRequest)->dict[str,Any]:
    data=await retrieve_payload(req)
    return envelope(data,resource="retrieval",meta={"result_count":len(data.get("matches") or [])})

@router.get("/projects",dependencies=auth)
def independent_projects(
    limit:int=Query(default=100,ge=1,le=500),
    owner_ref:str=Query(default="",max_length=220),
)->dict[str,Any]:
    data=list_projects(limit=limit,owner_ref=owner_ref)
    return envelope(data,resource="project-list",meta={"count":data["count"]})

@router.post("/projects",dependencies=auth)
def independent_project_create(req:ResearchProjectRequest)->dict[str,Any]:
    return envelope(create_project(req.model_dump()),resource="project")

@router.get("/projects/{project_id}",dependencies=auth)
def independent_project_get(project_id:str)->dict[str,Any]:
    try:return envelope(get_project(project_id),resource="project")
    except Exception as exc:raise _not_found(exc) from exc

@router.get("/projects/{project_id}/investigations",dependencies=auth)
def independent_project_investigations(
    project_id:str,
    limit:int=Query(default=100,ge=1,le=500),
)->dict[str,Any]:
    try:
        data=project_investigations(project_id,limit)
        return envelope(data,resource="investigation-list",meta={"count":data["count"]})
    except Exception as exc:raise _not_found(exc) from exc

@router.get("/scientist-environments/{scientist_environment_id}",dependencies=auth)
def independent_scientist_environment(scientist_environment_id:str)->dict[str,Any]:
    try:return envelope(scientist_environment(scientist_environment_id),resource="scientist-environment")
    except Exception as exc:raise _not_found(exc) from exc

@router.get("/scientist-environments/{scientist_environment_id}/dossier",dependencies=auth)
def independent_scientist_dossier(scientist_environment_id:str)->dict[str,Any]:
    try:return envelope(scientist_dossier(scientist_environment_id),resource="scientist-dossier")
    except Exception as exc:raise _not_found(exc) from exc

@router.get("/runtime-authority",dependencies=auth)
def independent_runtime_authority()->dict[str,Any]:
    return envelope(runtime_authority_payload(),resource="runtime-authority")

@router.post("/contract-snapshots/freeze",dependencies=auth)
def independent_contract_snapshot(req:IndependentAPIContractSnapshotRequest)->dict[str,Any]:
    snap=get_independent_api_contract_snapshot_store().freeze(req)
    return envelope(snap,resource="api-contract-snapshot")
