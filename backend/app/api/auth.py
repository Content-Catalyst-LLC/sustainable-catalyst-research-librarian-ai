from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from ..config import settings
from ..contracts.identity_session_access import (
    IdentityLoginRequest,
    IdentityPasswordUpdateRequest,
    IdentityProvisionRequest,
    IdentityRoleUpdateRequest,
    IdentitySessionRevokeRequest,
    IdentityStatusUpdateRequest,
)
from ..services.identity_session_access import (
    IdentityAccessContext,
    get_identity_session_store,
    integration_key_context,
)

router=APIRouter(prefix="/v1/research-librarian/auth",tags=["Research Librarian Identity & Access"])

def _api_key_valid(value:str)->bool:
    if not settings.api_key or not value:
        return False
    supplied=hashlib.sha256(value.encode("utf-8")).digest()
    expected=hashlib.sha256(settings.api_key.encode("utf-8")).digest()
    return hmac.compare_digest(supplied,expected)

def _extract_bearer(value:str)->str:
    raw=(value or "").strip()
    if len(raw)>7 and raw[:7].lower()=="bearer ":
        return raw[7:].strip()
    return ""

def require_independent_access(
    request:Request,
    x_sc_rl_key:str=Header(default="",alias="X-SC-RL-Key"),
    authorization:str=Header(default="",alias="Authorization"),
)->IdentityAccessContext:
    if _api_key_valid(x_sc_rl_key):
        return integration_key_context()

    token=_extract_bearer(authorization) or request.cookies.get(settings.identity_cookie_name,"")
    access=get_identity_session_store().resolve_token(token)
    if access is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Authentication required.")

    if request.method.upper() not in {"GET","HEAD","OPTIONS"} and not access.can_write:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="This identity does not have write access.")
    return access

def require_admin_access(access:IdentityAccessContext=Depends(require_independent_access))->IdentityAccessContext:
    if not access.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Owner or integration administration access is required.")
    return access

def require_integration_key(x_sc_rl_key:str=Header(default="",alias="X-SC-RL-Key"))->IdentityAccessContext:
    if not _api_key_valid(x_sc_rl_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Valid Research Librarian integration key required.")
    return integration_key_context()

@router.get("/manifest")
def auth_manifest()->dict[str,Any]:
    return {
        "ok":True,
        "data":get_identity_session_store().capabilities(),
        "resource":"identity-access-manifest",
    }

@router.post("/login")
def login(req:IdentityLoginRequest,response:Response)->dict[str,Any]:
    try:
        identity,token,session=get_identity_session_store().authenticate(
            req.email,req.password,req.client_label
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED,detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail=str(exc)) from exc

    data={"identity":identity,"session":session,"client_mode":req.client_mode}
    if req.client_mode=="bearer":
        data["bearer_token"]=token
    else:
        response.set_cookie(
            key=settings.identity_cookie_name,
            value=token,
            max_age=int(settings.identity_session_ttl_seconds),
            httponly=True,
            secure=bool(settings.identity_cookie_secure),
            samesite="strict",
            path="/",
        )
    return {"ok":True,"data":data,"resource":"identity-login"}

@router.post("/logout")
def logout(
    response:Response,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    if access.auth_session_id:
        get_identity_session_store().revoke(access.auth_session_id,"logout")
    response.delete_cookie(
        key=settings.identity_cookie_name,
        path="/",
        secure=bool(settings.identity_cookie_secure),
        httponly=True,
        samesite="strict",
    )
    return {"ok":True,"data":{"logged_out":True},"resource":"identity-logout"}

@router.get("/me")
def me(access:IdentityAccessContext=Depends(require_independent_access))->dict[str,Any]:
    return {"ok":True,"data":access.public(),"resource":"identity-access-context"}

@router.get("/sessions")
def my_sessions(
    limit:int=Query(default=100,ge=1,le=500),
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    if access.is_integration_key:
        return {"ok":True,"data":{"items":[],"count":0,"integration_key":True},"resource":"identity-session-list"}
    items=get_identity_session_store().sessions_for_identity(access.identity_id,limit)
    return {"ok":True,"data":{"items":items,"count":len(items)},"resource":"identity-session-list"}

@router.post("/sessions/{auth_session_id}/revoke")
def revoke_session(
    auth_session_id:str,
    req:IdentitySessionRevokeRequest,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    if access.is_integration_key:
        raise HTTPException(status_code=400,detail="Integration-key access does not own an identity session.")
    owned={x["auth_session_id"] for x in get_identity_session_store().sessions_for_identity(access.identity_id,500)}
    if auth_session_id not in owned:
        raise HTTPException(status_code=404,detail="Identity session not found.")
    revoked=get_identity_session_store().revoke(auth_session_id,req.reason)
    return {"ok":True,"data":{"auth_session_id":auth_session_id,"revoked":revoked},"resource":"identity-session-revoke"}

@router.post("/password")
def change_password(
    req:IdentityPasswordUpdateRequest,
    response:Response,
    access:IdentityAccessContext=Depends(require_independent_access),
)->dict[str,Any]:
    if access.is_integration_key:
        raise HTTPException(status_code=400,detail="Integration-key access has no identity password.")
    try:
        get_identity_session_store().change_password(access.identity_id,req.current_password,req.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc
    response.delete_cookie(
        key=settings.identity_cookie_name,path="/",secure=bool(settings.identity_cookie_secure),httponly=True,samesite="strict"
    )
    return {"ok":True,"data":{"password_changed":True,"reauthentication_required":True},"resource":"identity-password-change"}

@router.post("/provision")
def provision_identity(
    req:IdentityProvisionRequest,
    _admin:IdentityAccessContext=Depends(require_integration_key),
)->dict[str,Any]:
    try:
        identity=get_identity_session_store().provision(req)
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc
    return {"ok":True,"data":identity,"resource":"identity"}

@router.get("/identities")
def list_identities(
    limit:int=Query(default=100,ge=1,le=500),
    _admin:IdentityAccessContext=Depends(require_admin_access),
)->dict[str,Any]:
    items=get_identity_session_store().list_identities(limit)
    return {"ok":True,"data":{"items":items,"count":len(items)},"resource":"identity-list"}

@router.post("/identities/{identity_id}/role")
def update_identity_role(
    identity_id:str,
    req:IdentityRoleUpdateRequest,
    _admin:IdentityAccessContext=Depends(require_admin_access),
)->dict[str,Any]:
    try:
        identity=get_identity_session_store().update_role(identity_id,req.role)
    except ValueError as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc
    return {"ok":True,"data":identity,"resource":"identity"}

@router.post("/identities/{identity_id}/status")
def update_identity_status(
    identity_id:str,
    req:IdentityStatusUpdateRequest,
    _admin:IdentityAccessContext=Depends(require_admin_access),
)->dict[str,Any]:
    try:
        identity=get_identity_session_store().update_status(identity_id,req.status)
    except ValueError as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc
    return {"ok":True,"data":identity,"resource":"identity"}
