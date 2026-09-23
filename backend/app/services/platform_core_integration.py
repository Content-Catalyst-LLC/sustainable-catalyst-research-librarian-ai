from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from ..clients.platform_core import PlatformCoreClient, PlatformCoreError, compatibility
from ..config import settings
from ..contracts.platform_core import (
    CORE_BINDING_SCHEMA,
    CORE_INTEGRATION_SCHEMA,
    CoreExchangePackageRequest,
    CoreResearchObjectPromotionRequest,
    CoreUnifiedProjectSyncRequest,
)
from ..models import utc_now
from ..store import store


class CoreBindingConflict(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _safe_token(value: str, length: int = 40) -> str:
    clean = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value or "")).strip("-._")
    return (clean[:length] or hashlib.sha256(str(value).encode()).hexdigest()[:length]).lower()


def _core_entity_id(object_type: str, local_id: str) -> str:
    digest = hashlib.sha256(local_id.encode("utf-8")).hexdigest()[:20]
    return f"sc:{object_type}:research-librarian:{_safe_token(local_id, 48)}:{digest}"


def _idempotency(local_kind: str, local_id: str, supplied: str | None) -> str:
    if supplied and supplied.strip():
        return supplied.strip()
    return f"rl-8.2:{local_kind}:{hashlib.sha256(local_id.encode()).hexdigest()[:32]}"


def _base_binding(local_kind: str, local_id: str, core_kind: str, payload_hash: str, idempotency_key: str) -> dict[str, Any]:
    now = utc_now()
    return {
        "schema": CORE_BINDING_SCHEMA,
        "binding_key": f"{local_kind}:{local_id}",
        "local_kind": local_kind,
        "local_id": local_id,
        "core_kind": core_kind,
        "core_id": "",
        "sync_state": "pending",
        "contract_version": CORE_INTEGRATION_SCHEMA,
        "payload_hash": payload_hash,
        "idempotency_key": idempotency_key,
        "created_utc": now,
        "updated_utc": now,
        "last_error": "",
        "research_librarian_release": settings.release_version,
        "core_minimum_version": settings.core_minimum_version,
    }


def _existing_or_conflict(local_kind: str, local_id: str, payload_hash: str) -> dict[str, Any] | None:
    existing = store.platform_core_binding(local_kind, local_id)
    if not existing:
        return None
    if existing.get("payload_hash") == payload_hash and existing.get("sync_state") == "synced" and existing.get("core_id"):
        return existing
    if existing.get("payload_hash") != payload_hash:
        raise CoreBindingConflict(
            "This Librarian object is already bound to Platform Core with different content. "
            "v8.2 bindings are immutable; create an explicit revised Librarian object instead of overwriting governed Core state."
        )
    return None


def _failure(binding: dict[str, Any], exc: Exception) -> None:
    failed = {
        **binding,
        "sync_state": "failed",
        "updated_utc": utc_now(),
        "last_error": str(exc)[:2000],
    }
    store.save_platform_core_binding(failed)


async def integration_readiness(client: PlatformCoreClient | None = None) -> dict[str, Any]:
    summary = store.platform_core_integration_summary()
    base = {
        "schema": CORE_INTEGRATION_SCHEMA,
        "research_librarian_release": settings.release_version,
        "enabled": settings.core_enabled,
        "base_url": settings.core_base_url,
        "minimum_core_version": settings.core_minimum_version,
        "supported_core_major": settings.core_supported_major,
        "write_key_configured": bool(settings.core_write_api_key),
        "fail_closed_writes": settings.core_fail_closed_writes,
        "bindings": summary,
    }
    if not settings.core_enabled:
        return {**base, "ok": False, "state": "disabled", "compatible": False, "write_ready": False}
    core = client or PlatformCoreClient()
    try:
        health = await core.health()
        check = compatibility(str(health.get("version") or ""))
        capabilities = await core.capability_readiness()
        failed = sorted(name for name, item in capabilities.items() if not item.get("ok"))
        return {
            **base,
            "ok": check.compatible and not failed,
            "state": "ready" if check.compatible and not failed else "degraded",
            "compatible": check.compatible,
            "write_ready": bool(check.compatible and settings.core_write_api_key),
            "core_health": health,
            "compatibility": check.as_dict(),
            "capabilities": capabilities,
            "failed_capabilities": failed,
        }
    except PlatformCoreError as exc:
        return {
            **base,
            "ok": False,
            "state": "unreachable",
            "compatible": False,
            "write_ready": False,
            "error": str(exc),
            "status_code": exc.status_code,
            "detail": exc.detail,
        }


async def promote_research_object(
    request: CoreResearchObjectPromotionRequest,
    client: PlatformCoreClient | None = None,
) -> dict[str, Any]:
    local_kind = "research-object"
    idempotency_key = _idempotency(local_kind, request.local_object_id, request.idempotency_key)
    entity_id = _core_entity_id(request.object_type, request.local_object_id)
    metadata = {
        **request.metadata,
        "source_product": "research-librarian",
        "source_release": settings.release_version,
        "source_local_object_id": request.local_object_id,
        "source_project_id": request.project_id or "",
        "integration_schema": CORE_INTEGRATION_SCHEMA,
        "idempotency_key": idempotency_key,
    }
    core_payload = {
        "object_type": request.object_type,
        "name": request.name,
        "slug": request.slug,
        "description": request.description,
        "entity_id": entity_id,
        "visibility": request.visibility,
        "status": request.status,
        "attributes": request.attributes,
        "metadata": metadata,
    }
    payload_hash = _sha(core_payload)
    existing = _existing_or_conflict(local_kind, request.local_object_id, payload_hash)
    if existing:
        return {"schema": CORE_INTEGRATION_SCHEMA, "idempotent_replay": True, "binding": existing}

    binding = _base_binding(local_kind, request.local_object_id, request.object_type, payload_hash, idempotency_key)
    binding.update({"core_id": entity_id, "request": core_payload})
    store.save_platform_core_binding(binding)
    core = client or PlatformCoreClient()
    try:
        result = await core.create_research_object(core_payload)
    except PlatformCoreError as exc:
        if exc.status_code == 409:
            try:
                result = await core.research_object(entity_id)
                recovered_local_id = str((result.get("metadata") or {}).get("source_local_object_id") or "")
                if recovered_local_id and recovered_local_id != request.local_object_id:
                    raise PlatformCoreError("Recovered Core object identity does not match the Librarian source object.", status_code=409, detail=result)
            except PlatformCoreError:
                _failure(binding, exc)
                raise
        else:
            _failure(binding, exc)
            raise
    synced = {
        **binding,
        "core_id": str(result.get("id") or entity_id),
        "sync_state": "synced",
        "updated_utc": utc_now(),
        "last_error": "",
        "core_response": result,
    }
    saved = store.save_platform_core_binding(synced)
    return {"schema": CORE_INTEGRATION_SCHEMA, "idempotent_replay": False, "binding": saved, "core": result}


async def synchronize_unified_project(
    request: CoreUnifiedProjectSyncRequest,
    client: PlatformCoreClient | None = None,
) -> dict[str, Any]:
    local_kind = "research-project"
    idempotency_key = _idempotency(local_kind, request.local_project_id, request.idempotency_key)
    project_entity_id = _core_entity_id("research-project", request.local_project_id)
    metadata = {
        **request.metadata,
        "source_product": "research-librarian",
        "source_release": settings.release_version,
        "source_local_project_id": request.local_project_id,
        "integration_schema": CORE_INTEGRATION_SCHEMA,
        "idempotency_key": idempotency_key,
    }
    core_payload = {
        "project_entity_id": project_entity_id,
        "project_key": request.project_key or _safe_token(request.local_project_id, 80),
        "title": request.title,
        "abstract": request.abstract,
        "research_question": request.research_question,
        "objective": request.objective,
        "methodology": request.methodology,
        "research_type": request.research_type,
        "lifecycle_state": request.lifecycle_state,
        "visibility": request.visibility,
        "owner_product": "research-librarian",
        "reproducibility_target": request.reproducibility_target,
        "metadata": metadata,
        "scope": request.scope,
        "ethics": request.ethics,
        "governance": request.governance,
    }
    payload_hash = _sha(core_payload)
    existing = _existing_or_conflict(local_kind, request.local_project_id, payload_hash)
    if existing:
        return {"schema": CORE_INTEGRATION_SCHEMA, "idempotent_replay": True, "binding": existing}

    binding = _base_binding(local_kind, request.local_project_id, "unified-research-project", payload_hash, idempotency_key)
    binding.update({"core_id": project_entity_id, "request": core_payload})
    store.save_platform_core_binding(binding)
    core = client or PlatformCoreClient()
    try:
        result = await core.create_unified_research_project(core_payload)
    except PlatformCoreError as exc:
        if exc.status_code == 409:
            try:
                result = await core.research_project_bundle(project_entity_id)
            except PlatformCoreError:
                _failure(binding, exc)
                raise
        else:
            _failure(binding, exc)
            raise
    synced = {
        **binding,
        "core_id": project_entity_id,
        "sync_state": "synced",
        "updated_utc": utc_now(),
        "last_error": "",
        "core_response": result,
    }
    saved = store.save_platform_core_binding(synced)
    return {"schema": CORE_INTEGRATION_SCHEMA, "idempotent_replay": False, "binding": saved, "core": result}


async def create_exchange_package(
    request: CoreExchangePackageRequest,
    client: PlatformCoreClient | None = None,
) -> dict[str, Any]:
    local_kind = "exchange-package"
    idempotency_key = _idempotency(local_kind, request.local_exchange_id, request.idempotency_key)
    payload = {
        "origin_product": "research-librarian",
        "target_product": request.target_product,
        "title": request.title,
        "purpose": request.purpose,
        "visibility": request.visibility,
        "idempotency_key": idempotency_key,
        "items": [item.model_dump() for item in request.items],
        "provenance": {
            **request.provenance,
            "source_product": "research-librarian",
            "source_release": settings.release_version,
            "source_local_exchange_id": request.local_exchange_id,
            "integration_schema": CORE_INTEGRATION_SCHEMA,
        },
    }
    payload_hash = _sha(payload)
    existing = _existing_or_conflict(local_kind, request.local_exchange_id, payload_hash)
    if existing:
        return {"schema": CORE_INTEGRATION_SCHEMA, "idempotent_replay": True, "binding": existing}

    binding = _base_binding(local_kind, request.local_exchange_id, "exchange-package", payload_hash, idempotency_key)
    binding.update({"request": payload})
    store.save_platform_core_binding(binding)
    core = client or PlatformCoreClient()
    try:
        result = await core.create_exchange_package(payload)
    except PlatformCoreError as exc:
        _failure(binding, exc)
        raise
    core_id = str(result.get("id") or result.get("package_id") or "")
    synced = {
        **binding,
        "core_id": core_id,
        "sync_state": "synced",
        "updated_utc": utc_now(),
        "last_error": "",
        "core_response": result,
    }
    saved = store.save_platform_core_binding(synced)
    return {"schema": CORE_INTEGRATION_SCHEMA, "idempotent_replay": False, "binding": saved, "core": result}
