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
from .auth import require_independent_access
from ..services.identity_session_access import IdentityAccessContext, assert_session_access

router=APIRouter(prefix="/v1/research-librarian",tags=["Independent Research Librarian API v1"])

auth=[Depends(require_independent_access)]

def _not_found(exc:Exception)->HTTPException:
    if isinstance(exc,ValueError):
        return HTTPException(status_code=404,detail=str(exc))
    return HTTPException(status_code=500,detail=str(exc))


def _session_for_access(session_id:str,access:IdentityAccessContext)->dict[str,Any]:
    session=get_persistent_research_session_store().get(session_id)
    try:
        assert_session_access(session,access)
    except PermissionError as exc:
        raise HTTPException(status_code=403,detail=str(exc)) from exc
    return session

def _project_for_access(project_id:str,access:IdentityAccessContext)->dict[str,Any]:
    project=get_project(project_id)
    if not access.is_integration_key and str(project.get("owner_ref") or "")!=access.identity_ref:
        raise HTTPException(status_code=403,detail="Research project is not owned by the authenticated identity.")
    return project

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

@router.get("/projects")
def independent_projects(
    limit:int=Query(default=100,ge=1,le=500),
    owner_ref:str=Query(default="",max_length=220),
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    effective_owner=owner_ref if access.is_integration_key else access.identity_ref
    data=list_projects(limit=limit,owner_ref=effective_owner)
    return envelope(data,resource="project-list",meta={"count":data["count"],"identity_scoped":not access.is_integration_key})

@router.post("/projects")
def independent_project_create(
    req:ResearchProjectRequest,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    if not access.is_integration_key:
        req=req.model_copy(update={"owner_ref":access.identity_ref})
    return envelope(create_project(req.model_dump()),resource="project")

@router.get("/projects/{project_id}")
def independent_project_get(
    project_id:str,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:return envelope(_project_for_access(project_id,access),resource="project")
    except HTTPException:raise
    except Exception as exc:raise _not_found(exc) from exc

@router.get("/projects/{project_id}/investigations")
def independent_project_investigations(
    project_id:str,
    limit:int=Query(default=100,ge=1,le=500),
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:
        _project_for_access(project_id,access)
        data=project_investigations(project_id,limit)
        return envelope(data,resource="investigation-list",meta={"count":data["count"]})
    except HTTPException:raise
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

@router.get("/sessions")
def independent_sessions(
    limit:int=Query(default=100,ge=1,le=500),
    client_ref:str=Query(default="",max_length=255),
    project_id:str=Query(default="",max_length=255),
    state:str=Query(default="",max_length=40),
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    effective_client_ref=client_ref if access.is_integration_key else access.identity_ref
    items=get_persistent_research_session_store().list_sessions(
        limit=limit,client_ref=effective_client_ref,project_id=project_id,state=state
    )
    return envelope(
        {"items":items,"count":len(items),"limit":limit},
        resource="research-session-list",
        meta={"client_ref_is_identity":not access.is_integration_key},
    )

@router.post("/sessions")
def independent_session_create(
    req:ResearchSessionCreateRequest,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    if not access.is_integration_key:
        req=req.model_copy(update={"client_ref":access.identity_ref})
    session=get_persistent_research_session_store().create(req)
    return envelope(session,resource="research-session")

@router.get("/sessions/{session_id}")
def independent_session_get(
    session_id:str,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:
        return envelope(_session_for_access(session_id,access),resource="research-session")
    except HTTPException:raise
    except Exception as exc:
        raise _not_found(exc) from exc

@router.get("/sessions/{session_id}/turns")
def independent_session_turns(
    session_id:str,
    limit:int=Query(default=500,ge=1,le=5000),
    after_sequence:int=Query(default=0,ge=0),
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:
        _session_for_access(session_id,access)
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

@router.post("/sessions/{session_id}/turns")
def independent_session_turn_add(
    session_id:str,req:ResearchSessionTurnAddRequest,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:
        _session_for_access(session_id,access)
        turn=get_persistent_research_session_store().add_turn(session_id,req)
        return envelope(turn,resource="research-session-turn")
    except ValueError as exc:
        code=404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=code,detail=str(exc)) from exc

@router.post("/sessions/{session_id}/context")
def independent_session_context(
    session_id:str,req:ResearchSessionContextBindRequest,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:
        _session_for_access(session_id,access)
        session=get_persistent_research_session_store().bind_context(session_id,req)
        return envelope(session,resource="research-session-context")
    except ValueError as exc:
        code=404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=code,detail=str(exc)) from exc

@router.post("/sessions/{session_id}/state")
def independent_session_state(
    session_id:str,req:ResearchSessionStateRequest,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:
        _session_for_access(session_id,access)
        session=get_persistent_research_session_store().set_state(session_id,req)
        return envelope(session,resource="research-session-state")
    except Exception as exc:
        raise _not_found(exc) from exc

@router.post("/sessions/{session_id}/reset")
def independent_session_reset(
    session_id:str,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    _session_for_access(session_id,access)
    removed=get_persistent_research_session_store().clear_turns(session_id)
    return envelope(
        {"session_id":session_id,"removed_turns":removed},
        resource="research-session-reset",
    )

@router.get("/sessions/{session_id}/summary")
def independent_session_summary(
    session_id:str,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:
        _session_for_access(session_id,access)
        return envelope(
            get_persistent_research_session_store().summary(session_id),
            resource="research-session-summary",
        )
    except Exception as exc:
        raise _not_found(exc) from exc

@router.post("/sessions/{session_id}/snapshots/freeze")
def independent_session_snapshot(
    session_id:str,req:ResearchSessionSnapshotRequest,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    try:
        _session_for_access(session_id,access)
        snap=get_persistent_research_session_store().freeze_snapshot(session_id,req)
        return envelope(snap,resource="research-session-snapshot")
    except Exception as exc:
        raise _not_found(exc) from exc
