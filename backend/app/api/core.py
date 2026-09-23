from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ..clients.platform_core import PlatformCoreClient, PlatformCoreError
from ..config import settings
from ..contracts.evidence_bridge import (
    CORE_EVIDENCE_BRIDGE_SCHEMA,
    CorePassageEvidencePromotionRequest,
    CoreSourceSnapshotPromotionRequest,
)
from ..contracts.platform_core import (
    CORE_INTEGRATION_SCHEMA,
    CoreExchangePackageRequest,
    CoreResearchObjectPromotionRequest,
    CoreUnifiedProjectSyncRequest,
)
from ..services.core_evidence_bridge import (
    evidence_bridge_capabilities,
    promote_passage_evidence,
    promote_source_snapshot,
)
from ..services.platform_core_integration import (
    CoreBindingConflict,
    create_exchange_package,
    integration_readiness,
    promote_research_object,
    synchronize_unified_project,
)
from ..store import store

router = APIRouter(prefix="/v1/core", tags=["Platform Core Integration"])


def require_backend_key(x_sc_rl_key: str = Header(default="", alias="X-SC-RL-Key")) -> None:
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SC_RL_BACKEND_API_KEY is not configured on the backend.",
        )
    supplied = hashlib.sha256((x_sc_rl_key or "").encode()).digest()
    expected = hashlib.sha256(settings.api_key.encode()).digest()
    if not x_sc_rl_key or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid backend integration key.")


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, CoreBindingConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, PlatformCoreError):
        code = exc.status_code if exc.status_code and 400 <= exc.status_code < 600 else 502
        return HTTPException(
            status_code=code,
            detail={"message": str(exc), "core_detail": exc.detail},
        )
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/architecture", dependencies=[Depends(require_backend_key)])
def architecture() -> dict[str, Any]:
    return {
        "schema": CORE_INTEGRATION_SCHEMA,
        "release": settings.release_version,
        "python_runtime_owns": [
            "source-ingestion",
            "parsing",
            "chunking",
            "indexing",
            "retrieval",
            "connectors",
            "document-intelligence",
            "core-client-orchestration",
            "canonical-source-identity",
            "evidence-promotion-orchestration",
        ],
        "platform_core_owns": [
            "governed-research-objects",
            "governed-source-snapshots-and-evidence-records",
            "provenance-and-lineage",
            "claims-findings-arguments",
            "cross-study-synthesis",
            "reproducibility-packages",
            "visual-reasoning",
            "statistical-reasoning-objects",
            "cross-product-exchange",
        ],
        "automatic_truth_promotion": False,
        "core_executes_arbitrary_research_code": False,
        "write_boundary": "All Core writes require the private Core write key and a Librarian binding record.",
    }


@router.get("/readiness", dependencies=[Depends(require_backend_key)])
async def readiness() -> dict[str, Any]:
    return await integration_readiness()


@router.get("/bindings", dependencies=[Depends(require_backend_key)])
def bindings(
    limit: int = Query(default=100, ge=1, le=1000),
    sync_state: str = Query(default=""),
) -> dict[str, Any]:
    items = store.platform_core_bindings(limit=limit, sync_state=sync_state)
    return {
        "schema": CORE_INTEGRATION_SCHEMA,
        "items": items,
        "count": len(items),
        "summary": store.platform_core_integration_summary(),
    }


@router.get("/bindings/{local_kind}/{local_id:path}", dependencies=[Depends(require_backend_key)])
def binding(local_kind: str, local_id: str) -> dict[str, Any]:
    item = store.platform_core_binding(local_kind, local_id)
    if not item:
        raise HTTPException(status_code=404, detail="Platform Core binding not found.")
    return {"schema": CORE_INTEGRATION_SCHEMA, "binding": item}


@router.post("/research-objects/promote", dependencies=[Depends(require_backend_key)])
async def research_object_promote(payload: CoreResearchObjectPromotionRequest) -> dict[str, Any]:
    try:
        return await promote_research_object(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/research-projects/synchronize", dependencies=[Depends(require_backend_key)])
async def research_project_synchronize(payload: CoreUnifiedProjectSyncRequest) -> dict[str, Any]:
    try:
        return await synchronize_unified_project(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/research-projects/{core_project_id:path}/bundle", dependencies=[Depends(require_backend_key)])
async def research_project_bundle(core_project_id: str) -> dict[str, Any]:
    try:
        result = await PlatformCoreClient().research_project_bundle(core_project_id)
        return {"schema": CORE_INTEGRATION_SCHEMA, "core": result}
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/exchange/packages", dependencies=[Depends(require_backend_key)])
async def exchange_package(payload: CoreExchangePackageRequest) -> dict[str, Any]:
    try:
        return await create_exchange_package(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/evidence/capabilities", dependencies=[Depends(require_backend_key)])
def evidence_capabilities() -> dict[str, Any]:
    return evidence_bridge_capabilities()


@router.post("/evidence/source-snapshots/promote", dependencies=[Depends(require_backend_key)])
async def evidence_source_snapshot_promote(payload: CoreSourceSnapshotPromotionRequest) -> dict[str, Any]:
    try:
        return await promote_source_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/evidence/passages/promote", dependencies=[Depends(require_backend_key)])
async def evidence_passage_promote(payload: CorePassageEvidencePromotionRequest) -> dict[str, Any]:
    try:
        return await promote_passage_evidence(payload)
    except Exception as exc:
        raise _translate(exc) from exc
