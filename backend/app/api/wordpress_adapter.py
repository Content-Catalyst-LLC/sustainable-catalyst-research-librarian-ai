from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends

from .auth import require_independent_access
from ..services.identity_session_access import IdentityAccessContext
from ..services.thin_wordpress_adapter import (
    thin_wordpress_adapter_manifest,
    thin_wordpress_adapter_capabilities,
)

router=APIRouter(
    prefix="/v1/research-librarian/wordpress-adapter",
    tags=["Research Librarian Thin WordPress Adapter"],
)

@router.get("/manifest")
def wordpress_adapter_manifest() -> dict[str, Any]:
    return {
        "ok": True,
        "data": thin_wordpress_adapter_manifest(),
        "resource": "thin-wordpress-adapter-manifest",
    }

@router.get("/capabilities")
def wordpress_adapter_capabilities(
    _access: IdentityAccessContext=Depends(require_independent_access),
) -> dict[str, Any]:
    return {
        "ok": True,
        "data": thin_wordpress_adapter_capabilities(),
        "resource": "thin-wordpress-adapter-capabilities",
    }
