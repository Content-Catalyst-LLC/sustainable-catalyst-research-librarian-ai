from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_independent_access, require_admin_access
from ..services.identity_session_access import IdentityAccessContext
from ..contracts.wordpress_state_migration import (
    WordPressMigrationPrepareRequest,
    WordPressMigrationApplyRequest,
    WordPressCompatibilityResolveRequest,
)
from ..services.wordpress_state_migration import (
    migration_manifest,
    get_wordpress_state_migration_store,
)

router=APIRouter(
    prefix="/v1/research-librarian/wordpress-migration",
    tags=["Research Librarian WordPress State Migration"],
)

@router.get("/manifest")
def wordpress_migration_manifest()->dict[str,Any]:
    return {
        "ok":True,
        "data":migration_manifest(),
        "resource":"wordpress-state-migration-manifest",
    }

@router.get("/capabilities")
def wordpress_migration_capabilities(
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    return {
        "ok":True,
        "data":get_wordpress_state_migration_store().capabilities(),
        "resource":"wordpress-state-migration-capabilities",
    }

@router.post("/prepare")
def wordpress_migration_prepare(
    req:WordPressMigrationPrepareRequest,
    _admin:IdentityAccessContext=Depends(require_admin_access),
)->dict[str,Any]:
    try:
        data=get_wordpress_state_migration_store().prepare(req)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc
    return {"ok":True,"data":data,"resource":"wordpress-state-migration-prepare"}

@router.get("/runs")
def wordpress_migration_runs(
    source_site:str=Query(default="",max_length=1000),
    limit:int=Query(default=50,ge=1,le=200),
    _admin:IdentityAccessContext=Depends(require_admin_access),
)->dict[str,Any]:
    items=get_wordpress_state_migration_store().recent_runs(source_site,limit)
    return {
        "ok":True,
        "data":{"items":items,"count":len(items)},
        "resource":"wordpress-state-migration-run-list",
    }

@router.get("/runs/{run_id}")
def wordpress_migration_run(
    run_id:str,
    _admin:IdentityAccessContext=Depends(require_admin_access),
)->dict[str,Any]:
    try:
        data=get_wordpress_state_migration_store().get_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc
    return {"ok":True,"data":data,"resource":"wordpress-state-migration-run"}

@router.post("/runs/{run_id}/apply")
def wordpress_migration_apply(
    run_id:str,
    req:WordPressMigrationApplyRequest,
    _admin:IdentityAccessContext=Depends(require_admin_access),
)->dict[str,Any]:
    try:
        data=get_wordpress_state_migration_store().apply(run_id,req)
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc
    return {"ok":True,"data":data,"resource":"wordpress-state-migration-apply"}

@router.post("/resolve")
def wordpress_compatibility_resolve(
    req:WordPressCompatibilityResolveRequest,
    _access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    alias=get_wordpress_state_migration_store().resolve(
        req.source_site,req.source_type,req.legacy_id
    )
    if not alias:
        raise HTTPException(status_code=404,detail="Compatibility alias not found.")
    return {
        "ok":True,
        "data":alias,
        "resource":"wordpress-compatibility-alias",
    }
