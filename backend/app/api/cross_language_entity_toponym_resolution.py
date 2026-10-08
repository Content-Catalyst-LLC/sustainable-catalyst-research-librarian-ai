from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import require_independent_access
from ..services.identity_session_access import IdentityAccessContext
from ..contracts.cross_language_entity_toponym_resolution import *
from ..services.cross_language_entity_toponym_resolution import (
    capabilities,
    resolution_manifest,
    get_cross_language_entity_toponym_resolution_store,
)

router = APIRouter(
    prefix="/v1/research-librarian/cross-language-entity-toponym-resolution",
    tags=["Research Librarian Cross-Language Entity & Toponym Resolution"],
)


def _store():
    return get_cross_language_entity_toponym_resolution_store()


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        message = str(exc)
        code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=message) from exc


@router.get("/manifest")
def manifest() -> dict[str, Any]:
    return {"ok": True, "data": resolution_manifest(), "resource": "cross-language-resolution-manifest"}


@router.get("/capabilities")
def resolution_capabilities(
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": capabilities(), "resource": "cross-language-resolution-capabilities"}


@router.get("/projects")
def list_projects(
    limit: int = Query(default=100, ge=1, le=500),
    owner_ref: str = Query(default="", max_length=255),
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _store().list(limit, owner_ref), "resource": "cross-language-resolution-project-list"}


@router.post("/projects")
def create_project(
    payload: CrossLanguageResolutionCreateRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _store().create(payload), "resource": "cross-language-resolution-project"}


@router.get("/projects/{resolution_id}")
def get_project(
    resolution_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().get, resolution_id), "resource": "cross-language-resolution-project"}


@router.post("/projects/{resolution_id}/entity-mentions")
def add_entity_mention(
    resolution_id: str,
    payload: EntityMentionAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_entity_mention, resolution_id, payload), "resource": "cross-language-entity-mention"}


@router.post("/projects/{resolution_id}/entity-candidates")
def add_entity_candidate(
    resolution_id: str,
    payload: EntityCandidateAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_entity_candidate, resolution_id, payload), "resource": "cross-language-entity-candidate"}


@router.post("/projects/{resolution_id}/entity-resolutions")
def resolve_entity(
    resolution_id: str,
    payload: EntityResolutionDecisionRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().resolve_entity, resolution_id, payload), "resource": "cross-language-entity-resolution"}


@router.post("/projects/{resolution_id}/toponym-mentions")
def add_toponym_mention(
    resolution_id: str,
    payload: ToponymMentionAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_toponym_mention, resolution_id, payload), "resource": "cross-language-toponym-mention"}


@router.post("/projects/{resolution_id}/toponym-candidates")
def add_toponym_candidate(
    resolution_id: str,
    payload: ToponymCandidateAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_toponym_candidate, resolution_id, payload), "resource": "cross-language-toponym-candidate"}


@router.post("/projects/{resolution_id}/toponym-resolutions")
def resolve_toponym(
    resolution_id: str,
    payload: ToponymResolutionDecisionRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().resolve_toponym, resolution_id, payload), "resource": "cross-language-toponym-resolution"}


@router.post("/projects/{resolution_id}/alias-alignments")
def add_alias_alignment(
    resolution_id: str,
    payload: AliasAlignmentAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_alias_alignment, resolution_id, payload), "resource": "cross-language-alias-alignment"}


@router.get("/projects/{resolution_id}/lineage")
def lineage(
    resolution_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().lineage, resolution_id), "resource": "cross-language-resolution-lineage"}


@router.get("/projects/{resolution_id}/readiness")
def readiness(
    resolution_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().readiness, resolution_id), "resource": "cross-language-resolution-readiness"}


@router.get("/projects/{resolution_id}/core-candidate")
def core_candidate(
    resolution_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().core_candidate, resolution_id), "resource": "cross-language-resolution-core-candidate"}


@router.post("/projects/{resolution_id}/state")
def set_state(
    resolution_id: str,
    payload: CrossLanguageResolutionStateRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().set_state, resolution_id, payload), "resource": "cross-language-resolution-project"}


@router.post("/snapshots/freeze")
def freeze_snapshot(
    payload: CrossLanguageResolutionSnapshotRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().freeze_snapshot, payload), "resource": "cross-language-resolution-snapshot"}
