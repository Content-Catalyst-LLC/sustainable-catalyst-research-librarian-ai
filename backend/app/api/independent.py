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
from ..contracts.persistent_research_session_conversation import (
    ResearchSessionCreateRequest,
    ResearchSessionTurnAddRequest,
    ResearchSessionContextBindRequest,
    ResearchSessionStateRequest,
    ResearchSessionSnapshotRequest,
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
from ..services.persistent_research_session_conversation import (
    get_persistent_research_session_store,
    capabilities as persistent_research_session_capabilities,
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

@router.get("/sessions",dependencies=auth)
def independent_sessions(
    limit:int=Query(default=100,ge=1,le=500),
    client_ref:str=Query(default="",max_length=255),
    project_id:str=Query(default="",max_length=255),
    state:str=Query(default="",max_length=40),
)->dict[str,Any]:
    items=get_persistent_research_session_store().list_sessions(
        limit=limit,client_ref=client_ref,project_id=project_id,state=state
    )
    return envelope(
        {"items":items,"count":len(items),"limit":limit},
        resource="research-session-list",
        meta={"client_ref_is_identity":False},
    )

@router.post("/sessions",dependencies=auth)
def independent_session_create(req:ResearchSessionCreateRequest)->dict[str,Any]:
    session=get_persistent_research_session_store().create(req)
    return envelope(session,resource="research-session")

@router.get("/sessions/{session_id}",dependencies=auth)
def independent_session_get(session_id:str)->dict[str,Any]:
    try:
        return envelope(get_persistent_research_session_store().get(session_id),resource="research-session")
    except Exception as exc:
        raise _not_found(exc) from exc

@router.get("/sessions/{session_id}/turns",dependencies=auth)
def independent_session_turns(
    session_id:str,
    limit:int=Query(default=500,ge=1,le=5000),
    after_sequence:int=Query(default=0,ge=0),
)->dict[str,Any]:
    try:
        items=get_persistent_research_session_store().turns(
            session_id,limit=limit,after_sequence=after_sequence
        )
        return envelope(
            {"session_id":session_id,"items":items,"count":len(items)},
            resource="research-session-turn-list",
            meta={"count":len(items)},
        )
    except Exception as exc:
        raise _not_found(exc) from exc

@router.post("/sessions/{session_id}/turns",dependencies=auth)
def independent_session_turn_add(session_id:str,req:ResearchSessionTurnAddRequest)->dict[str,Any]:
    try:
        turn=get_persistent_research_session_store().add_turn(session_id,req)
        return envelope(turn,resource="research-session-turn")
    except ValueError as exc:
        code=404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=code,detail=str(exc)) from exc

@router.post("/sessions/{session_id}/context",dependencies=auth)
def independent_session_context(session_id:str,req:ResearchSessionContextBindRequest)->dict[str,Any]:
    try:
        session=get_persistent_research_session_store().bind_context(session_id,req)
        return envelope(session,resource="research-session-context")
    except ValueError as exc:
        code=404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=code,detail=str(exc)) from exc

@router.post("/sessions/{session_id}/state",dependencies=auth)
def independent_session_state(session_id:str,req:ResearchSessionStateRequest)->dict[str,Any]:
    try:
        session=get_persistent_research_session_store().set_state(session_id,req)
        return envelope(session,resource="research-session-state")
    except Exception as exc:
        raise _not_found(exc) from exc

@router.post("/sessions/{session_id}/reset",dependencies=auth)
def independent_session_reset(session_id:str)->dict[str,Any]:
    removed=get_persistent_research_session_store().clear_turns(session_id)
    return envelope(
        {"session_id":session_id,"removed_turns":removed},
        resource="research-session-reset",
    )

@router.get("/sessions/{session_id}/summary",dependencies=auth)
def independent_session_summary(session_id:str)->dict[str,Any]:
    try:
        return envelope(
            get_persistent_research_session_store().summary(session_id),
            resource="research-session-summary",
        )
    except Exception as exc:
        raise _not_found(exc) from exc

@router.post("/sessions/{session_id}/snapshots/freeze",dependencies=auth)
def independent_session_snapshot(session_id:str,req:ResearchSessionSnapshotRequest)->dict[str,Any]:
    try:
        snap=get_persistent_research_session_store().freeze_snapshot(session_id,req)
        return envelope(snap,resource="research-session-snapshot")
    except Exception as exc:
        raise _not_found(exc) from exc
