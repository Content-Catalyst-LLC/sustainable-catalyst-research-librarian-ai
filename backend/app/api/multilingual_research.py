from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import require_independent_access
from ..services.identity_session_access import IdentityAccessContext
from ..contracts.multilingual_cross_language_research import *
from ..services.multilingual_cross_language_research import (
    capabilities,
    get_multilingual_cross_language_research_store,
    multilingual_manifest,
)

router = APIRouter(
    prefix="/v1/research-librarian/multilingual-research",
    tags=["Research Librarian Multilingual & Cross-Language Research"],
)


def _store():
    return get_multilingual_cross_language_research_store()


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        message = str(exc)
        code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=message) from exc


@router.get("/manifest")
def manifest() -> dict[str, Any]:
    return {"ok": True, "data": multilingual_manifest(), "resource": "multilingual-research-manifest"}


@router.get("/capabilities")
def multilingual_capabilities(
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": capabilities(), "resource": "multilingual-research-capabilities"}


@router.get("/projects")
def list_projects(
    limit: int = Query(default=100, ge=1, le=500),
    owner_ref: str = Query(default="", max_length=255),
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _store().list(limit, owner_ref), "resource": "multilingual-research-project-list"}


@router.post("/projects")
def create_project(
    payload: MultilingualResearchCreateRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _store().create(payload), "resource": "multilingual-research-project"}


@router.get("/projects/{multilingual_research_id}")
def get_project(
    multilingual_research_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().get, multilingual_research_id), "resource": "multilingual-research-project"}


@router.post("/projects/{multilingual_research_id}/language-profiles")
def add_language_profile(
    multilingual_research_id: str,
    payload: LanguageProfileAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_language_profile, multilingual_research_id, payload), "resource": "language-profile"}


@router.post("/projects/{multilingual_research_id}/source-texts")
def add_source_text(
    multilingual_research_id: str,
    payload: OriginalLanguageSourceTextAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_source_text, multilingual_research_id, payload), "resource": "original-language-source-text"}


@router.post("/projects/{multilingual_research_id}/derived-representations")
def add_derived_representation(
    multilingual_research_id: str,
    payload: DerivedLanguageRepresentationAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_derived_representation, multilingual_research_id, payload), "resource": "derived-language-representation"}


@router.post("/projects/{multilingual_research_id}/alignments")
def add_alignment(
    multilingual_research_id: str,
    payload: TextAlignmentAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_alignment, multilingual_research_id, payload), "resource": "text-alignment"}


@router.post("/projects/{multilingual_research_id}/query-plans")
def add_query_plan(
    multilingual_research_id: str,
    payload: CrossLanguageQueryPlanAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_query_plan, multilingual_research_id, payload), "resource": "cross-language-query-plan"}


@router.post("/projects/{multilingual_research_id}/retrieval-receipts")
def add_retrieval_receipt(
    multilingual_research_id: str,
    payload: CrossLanguageRetrievalReceiptAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_retrieval_receipt, multilingual_research_id, payload), "resource": "cross-language-retrieval-receipt"}


@router.get("/projects/{multilingual_research_id}/lineage")
def lineage(
    multilingual_research_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().lineage, multilingual_research_id), "resource": "multilingual-research-lineage"}


@router.get("/projects/{multilingual_research_id}/readiness")
def readiness(
    multilingual_research_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().readiness, multilingual_research_id), "resource": "multilingual-research-readiness"}


@router.get("/projects/{multilingual_research_id}/core-candidate")
def core_candidate(
    multilingual_research_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().core_candidate, multilingual_research_id), "resource": "multilingual-core-candidate"}


@router.post("/projects/{multilingual_research_id}/state")
def set_state(
    multilingual_research_id: str,
    payload: MultilingualResearchStateRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().set_state, multilingual_research_id, payload), "resource": "multilingual-research-project"}


@router.post("/snapshots/freeze")
def freeze_snapshot(
    payload: MultilingualResearchSnapshotRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().freeze_snapshot, payload), "resource": "multilingual-research-snapshot"}
