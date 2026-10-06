from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from .auth import require_independent_access
from ..services.identity_session_access import IdentityAccessContext
from ..contracts.global_source_federation_original_language import *
from ..services.global_source_federation_original_language import (
    capabilities,
    federation_manifest,
    get_global_source_federation_original_language_store,
)

router = APIRouter(
    prefix="/v1/research-librarian/global-source-federation",
    tags=["Research Librarian Global Source Federation & Original-Language Research"],
)


def _store():
    return get_global_source_federation_original_language_store()


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        message = str(exc)
        code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=message) from exc


@router.get("/manifest")
def manifest() -> dict[str, Any]:
    return {"ok": True, "data": federation_manifest(), "resource": "global-source-federation-manifest"}


@router.get("/capabilities")
def federation_capabilities(
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": capabilities(), "resource": "global-source-federation-capabilities"}


@router.get("/projects")
def list_projects(
    limit: int = Query(default=100, ge=1, le=500),
    owner_ref: str = Query(default="", max_length=255),
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _store().list(limit, owner_ref), "resource": "global-source-federation-project-list"}


@router.post("/projects")
def create_project(
    payload: GlobalSourceFederationCreateRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _store().create(payload), "resource": "global-source-federation-project"}


@router.get("/projects/{federation_id}")
def get_project(
    federation_id: str,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().get, federation_id), "resource": "global-source-federation-project"}


@router.post("/projects/{federation_id}/sources")
def add_source(
    federation_id: str,
    payload: FederatedSourceAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_source, federation_id, payload), "resource": "federated-source"}


@router.post("/projects/{federation_id}/original-language-acquisitions")
def add_original_language_acquisition(
    federation_id: str,
    payload: OriginalLanguageAcquisitionAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_original_language_acquisition, federation_id, payload), "resource": "original-language-acquisition"}


@router.post("/projects/{federation_id}/ingestion-receipts")
def add_ingestion_receipt(
    federation_id: str,
    payload: SourceIngestionReceiptAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_ingestion_receipt, federation_id, payload), "resource": "source-ingestion-receipt"}


@router.post("/projects/{federation_id}/trust-preferences")
def set_source_trust_preference(
    federation_id: str,
    payload: SourceTrustPreferenceAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().set_source_trust_preference, federation_id, payload), "resource": "source-trust-preference"}


@router.post("/projects/{federation_id}/query-plans")
def add_query_plan(
    federation_id: str,
    payload: FederationQueryPlanAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_query_plan, federation_id, payload), "resource": "federation-query-plan"}


@router.post("/projects/{federation_id}/retrieval-receipts")
def add_retrieval_receipt(
    federation_id: str,
    payload: FederationRetrievalReceiptAddRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().add_retrieval_receipt, federation_id, payload), "resource": "federation-retrieval-receipt"}


@router.get("/projects/{federation_id}/lineage")
def lineage(federation_id: str, _access: IdentityAccessContext = Depends(require_independent_access)) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().lineage, federation_id), "resource": "global-source-federation-lineage"}


@router.get("/projects/{federation_id}/readiness")
def readiness(federation_id: str, _access: IdentityAccessContext = Depends(require_independent_access)) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().readiness, federation_id), "resource": "global-source-federation-readiness"}


@router.get("/projects/{federation_id}/multilingual-candidate")
def multilingual_candidate(federation_id: str, _access: IdentityAccessContext = Depends(require_independent_access)) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().multilingual_candidate, federation_id), "resource": "multilingual-federation-candidate"}


@router.get("/projects/{federation_id}/core-candidate")
def core_candidate(federation_id: str, _access: IdentityAccessContext = Depends(require_independent_access)) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().core_candidate, federation_id), "resource": "global-source-federation-core-candidate"}


@router.post("/projects/{federation_id}/state")
def set_state(
    federation_id: str,
    payload: GlobalSourceFederationStateRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().set_state, federation_id, payload), "resource": "global-source-federation-project"}


@router.post("/snapshots/freeze")
def freeze_snapshot(
    payload: GlobalSourceFederationSnapshotRequest,
    _access: IdentityAccessContext = Depends(require_independent_access),
) -> dict[str, Any]:
    return {"ok": True, "data": _call(_store().freeze_snapshot, payload), "resource": "global-source-federation-snapshot"}
