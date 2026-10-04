from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Request

from .auth import require_independent_access
from ..services.identity_session_access import IdentityAccessContext
from ..services.independent_deployment_certification import (
    certification_manifest,
    certification_report,
)

router=APIRouter(
    prefix="/v1/research-librarian/independence",
    tags=["Research Librarian Independent Deployment Certification"],
)

@router.get("/manifest")
def independence_manifest()->dict[str,Any]:
    return {
        "ok":True,
        "data":certification_manifest(),
        "resource":"independent-deployment-certification-manifest",
    }

@router.get("/report")
def independence_report(
    request:Request,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    paths={getattr(route,"path","") for route in request.app.routes}
    return {
        "ok":True,
        "data":certification_report(paths),
        "resource":"independent-deployment-certification-report",
    }
