from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from ..clients.platform_core import PlatformCoreClient, PlatformCoreError
from ..config import settings
from ..contracts.platform_core import CoreUnifiedProjectSyncRequest
from ..contracts.research_sync import (
    CORE_PROJECT_STATE_CONTRACT,
    CORE_RESEARCH_SYNC_SCHEMA,
    CoreProjectSynchronizationPlanRequest,
    CoreProjectSynchronizationRequest,
)
from ..models import utc_now
from ..services.platform_core_integration import synchronize_unified_project
from ..store import store


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _token(value: str, limit: int = 120) -> str:
    clean = re.sub(r"[^a-zA-Z0-9._:-]+", "-", str(value or "")).strip("-._:").lower()
    return (clean[:limit] or hashlib.sha256(str(value).encode()).hexdigest()[:limit])


def _visibility(value: str) -> str:
    value = str(value or "private").lower()
    return value if value in {"private", "internal", "public"} else "private"


def _content_hash(item: dict[str, Any]) -> str:
    fp = str(item.get("fingerprint") or "").strip()
    return fp if re.fullmatch(r"[0-9a-fA-F]{64}", fp) else _sha(item)


def _binding(key: str, object_type: str, object_ref: str, role: str, item: dict[str, Any], visibility: str = "internal", **metadata: Any) -> dict[str, Any]:
    return {
        "binding_key": _token(key, 180),
        "product_key": "research_librarian",
        "object_type": object_type,
        "object_ref": str(object_ref)[:1000],
        "content_hash": _content_hash(item),
        "role": role[:160],
        "visibility": _visibility(visibility),
        "metadata": {
            "source_release": settings.release_version,
            "source_schema": str(item.get("schema") or ""),
            **metadata,
        },
        "provenance": {
            "source_product": "research-librarian",
            "declared_not_inferred": True,
        },
    }


def capabilities() -> dict[str, Any]:
    return {
        "schema": CORE_RESEARCH_SYNC_SCHEMA,
        "release": settings.release_version,
        "platform_core_contract": CORE_PROJECT_STATE_CONTRACT,
        "unified_project_binding": True,
        "immutable_project_state_versions": True,
        "research_context_bindings": True,
        "research_room_bindings": True,
        "source_bindings": True,
        "project_entity_bindings": True,
        "open_question_bindings": True,
        "lifecycle_bindings": True,
        "declared_dependency_edges": True,
        "automatic_truth_promotion": False,
        "automatic_claim_creation": False,
        "automatic_workflow_advancement": False,
        "core_executes_research_code": False,
    }


def build_project_sync_plan(request: CoreProjectSynchronizationPlanRequest | CoreProjectSynchronizationRequest) -> dict[str, Any]:
    project = store.research_project(request.local_project_id)
    if not project:
        raise ValueError("Unknown Research Librarian project.")
    owner_ref = str(project.get("owner_ref") or "")
    bundle = store.project_bundle(request.local_project_id)
    bindings: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []

    project_key = "project-local"
    bindings.append(_binding(project_key, "project", f"research-librarian:project:{request.local_project_id}", "local_project_identity", project, request.visibility, local_project_id=request.local_project_id))

    if request.include_contexts:
        contexts = [x for x in store.research_contexts(500, owner_ref=owner_ref) if str(x.get("project_id") or "") == request.local_project_id]
        for item in contexts:
            cid = str(item.get("context_id") or "")
            if not cid:
                continue
            key = f"context-{cid}"
            bindings.append(_binding(key, "workflow", f"research-librarian:context:{cid}", "research_context", item, request.visibility, local_context_id=cid))
            dependencies.append({"dependency_key": _token(f"dep-{key}-project", 180), "from_binding_key": _token(key,180), "to_binding_key": project_key, "relation": "scoped_to_project", "details": {}, "provenance": {"declared_not_inferred": True}})

    if request.include_rooms:
        for room_bundle in bundle.get("research_rooms") or []:
            item = room_bundle.get("room") if isinstance(room_bundle, dict) else {}
            rid = str(item.get("room_id") or "")
            if not rid:
                continue
            key = f"room-{rid}"
            bindings.append(_binding(key, "other", f"research-librarian:room:{rid}", "research_room", item, request.visibility, local_room_id=rid, collaborative_state_not_evidence=True))
            dependencies.append({"dependency_key": _token(f"dep-{key}-project",180), "from_binding_key": _token(key,180), "to_binding_key": project_key, "relation": "collaboration_scope_for", "details": {}, "provenance": {"declared_not_inferred": True}})

    if request.include_sources:
        for item in bundle.get("library_objects") or []:
            oid = str(item.get("object_id") or "")
            if not oid:
                continue
            key = f"source-{oid}"
            obj_type = "source" if str(item.get("object_type") or "") in {"source", "publication", "workspace-evidence"} else "other"
            bindings.append(_binding(key, obj_type, f"research-librarian:library-object:{oid}", "research_material", item, _visibility(str(item.get("visibility") or request.visibility)), local_library_object_id=oid, source_scope=str(item.get("source_scope") or "")))
            dependencies.append({"dependency_key": _token(f"dep-{key}-project",180), "from_binding_key": _token(key,180), "to_binding_key": project_key, "relation": "research_material_for", "details": {}, "provenance": {"declared_not_inferred": True}})

    if request.include_entities:
        for item in bundle.get("entities") or []:
            eid = str(item.get("entity_id") or "")
            if not eid:
                continue
            key = f"entity-{eid}"
            type_map = {"question":"question","source":"source","evidence":"evidence","dataset":"dataset","method":"method","finding":"finding","claim":"claim","argument":"argument","conclusion":"conclusion","publication":"publication","visualization":"visualization","notebook":"notebook","workflow":"workflow"}
            core_type = type_map.get(str(item.get("entity_type") or "").lower(), "other")
            bindings.append(_binding(key, core_type, f"research-librarian:project-entity:{eid}", "project_entity", item, request.visibility, local_entity_id=eid, local_entity_type=str(item.get("entity_type") or "")))
            dependencies.append({"dependency_key": _token(f"dep-{key}-project",180), "from_binding_key": _token(key,180), "to_binding_key": project_key, "relation": "belongs_to_project", "details": {}, "provenance": {"declared_not_inferred": True}})

    if request.include_questions:
        for item in bundle.get("open_questions") or []:
            qid = str(item.get("question_id") or "")
            if not qid:
                continue
            key = f"question-{qid}"
            bindings.append(_binding(key, "question", f"research-librarian:question:{qid}", "open_research_question", item, request.visibility, local_question_id=qid, unresolved_question_not_fact=True))
            dependencies.append({"dependency_key": _token(f"dep-{key}-project",180), "from_binding_key": _token(key,180), "to_binding_key": project_key, "relation": "open_question_for", "details": {}, "provenance": {"declared_not_inferred": True}})

    if request.include_lifecycles:
        for lifecycle_bundle in bundle.get("research_lifecycles") or []:
            item = lifecycle_bundle.get("lifecycle") if isinstance(lifecycle_bundle, dict) else {}
            lid = str(item.get("lifecycle_id") or "")
            if not lid:
                continue
            key = f"lifecycle-{lid}"
            bindings.append(_binding(key, "workflow", f"research-librarian:lifecycle:{lid}", "research_lifecycle", item, request.visibility, local_lifecycle_id=lid, workflow_state_not_evidence=True))
            dependencies.append({"dependency_key": _token(f"dep-{key}-project",180), "from_binding_key": _token(key,180), "to_binding_key": project_key, "relation": "workflow_state_for", "details": {}, "provenance": {"declared_not_inferred": True}})

    bindings.sort(key=lambda x: x["binding_key"])
    dependencies.sort(key=lambda x: x["dependency_key"])
    payload = {
        "schema": CORE_RESEARCH_SYNC_SCHEMA,
        "local_project_id": request.local_project_id,
        "project_fingerprint": _content_hash(project),
        "bindings": bindings,
        "dependencies": dependencies,
        "governance": {
            "state_is_declared_not_inferred": True,
            "synchronization_does_not_determine_truth": True,
            "synchronization_does_not_publish": True,
            "synchronization_does_not_advance_workflow": True,
        },
    }
    payload["plan_hash"] = _sha(payload)
    return payload


async def synchronize_project_research_objects(request: CoreProjectSynchronizationRequest, client: PlatformCoreClient | None = None) -> dict[str, Any]:
    plan = build_project_sync_plan(request)
    if request.dry_run:
        return {"schema": CORE_RESEARCH_SYNC_SCHEMA, "dry_run": True, "plan": plan, "capabilities": capabilities()}

    core = client or PlatformCoreClient()
    project = store.research_project(request.local_project_id)
    assert project is not None

    project_binding = store.platform_core_binding("research-project", request.local_project_id)
    if not project_binding or project_binding.get("sync_state") != "synced" or not project_binding.get("core_id"):
        sync = await synchronize_unified_project(CoreUnifiedProjectSyncRequest(
            local_project_id=request.local_project_id,
            title=str(project.get("title") or "Untitled research project"),
            abstract=str(project.get("objective") or ""),
            objective=str(project.get("objective") or ""),
            lifecycle_state=str(project.get("status") or "active"),
            visibility=_visibility(str(project.get("visibility") or "private")),
            metadata={"v8_8_project_state_sync": True, "local_project_fingerprint": str(project.get("fingerprint") or "")},
            governance=dict(project.get("governance") or {}),
        ), client=core)
        project_binding = sync["binding"]
    core_project_id = str(project_binding.get("core_id") or "")
    if not core_project_id:
        raise ValueError("Platform Core unified project binding did not return a Core project identity.")

    tracker = store.platform_core_binding("research-project-state", request.local_project_id)
    if tracker and tracker.get("sync_state") == "synced" and tracker.get("payload_hash") == plan["plan_hash"]:
        return {"schema": CORE_RESEARCH_SYNC_SCHEMA, "idempotent_replay": True, "plan": plan, "binding": tracker}

    state_id = str((tracker or {}).get("core_id") or "")
    if not state_id:
        state_key = f"rl-project-state-{hashlib.sha256(request.local_project_id.encode()).hexdigest()[:24]}"
        created = await core.create_project_state({
            "state_key": state_key,
            "project_ref": core_project_id,
            "title": str(project.get("title") or "Research Librarian project state"),
            "status": "active" if str(project.get("status") or "active") not in {"archived"} else "archived",
            "visibility": request.visibility,
            "metadata": {"source_product":"research-librarian","source_release":settings.release_version,"local_project_id":request.local_project_id},
            "provenance": {"source_product":"research-librarian","local_project_fingerprint":str(project.get("fingerprint") or ""),"declared_not_inferred":True},
            "created_by": request.created_by,
        })
        state_id = str(created.get("id") or "")
        if not state_id:
            raise ValueError("Platform Core project-state creation returned no state id.")

    version_result = await core.create_project_state_version(state_id, {
        "label": f"Research Librarian {settings.release_version}",
        "status": "draft",
        "summary": f"Synchronized declared Research Librarian project state for {request.local_project_id}.",
        "metadata": {"plan_hash":plan["plan_hash"],"binding_count":len(plan["bindings"]),"dependency_count":len(plan["dependencies"])},
        "provenance": {"source_product":"research-librarian","source_release":settings.release_version,"declared_not_inferred":True},
        "created_by": request.created_by,
    })
    version = int(version_result.get("version") or 0)
    if version <= 0:
        raise ValueError("Platform Core project-state version creation returned no version number.")

    for item in plan["bindings"]:
        await core.add_project_state_binding(state_id, version, {**item, "created_by": request.created_by})
    for edge in plan["dependencies"]:
        await core.add_project_state_dependency(state_id, version, {**edge, "created_by": request.created_by})

    frozen: dict[str, Any] | None = None
    if request.freeze_version:
        frozen = await core.freeze_project_state_version(state_id, version, {"created_by": request.created_by})
    snapshot: dict[str, Any] | None = None
    if request.create_snapshot and request.freeze_version:
        snapshot = await core.snapshot_project_state(state_id, {"provenance":{"source_product":"research-librarian","source_release":settings.release_version,"plan_hash":plan["plan_hash"]},"created_by":request.created_by})

    now = utc_now()
    binding = store.save_platform_core_binding({
        "schema": "sc-research-librarian-core-binding/1.0",
        "binding_key": f"research-project-state:{request.local_project_id}",
        "local_kind": "research-project-state",
        "local_id": request.local_project_id,
        "core_kind": "research-project-state",
        "core_id": state_id,
        "sync_state": "synced",
        "contract_version": CORE_RESEARCH_SYNC_SCHEMA,
        "payload_hash": plan["plan_hash"],
        "idempotency_key": f"rl-8.8:project-state:{hashlib.sha256(request.local_project_id.encode()).hexdigest()[:32]}",
        "created_utc": str((tracker or {}).get("created_utc") or now),
        "updated_utc": now,
        "last_error": "",
        "research_librarian_release": settings.release_version,
        "core_project_id": core_project_id,
        "core_version": version,
        "frozen": bool(frozen),
        "snapshot_id": str((snapshot or {}).get("id") or ""),
        "plan": plan,
    })
    return {
        "schema": CORE_RESEARCH_SYNC_SCHEMA,
        "idempotent_replay": False,
        "binding": binding,
        "core_project_id": core_project_id,
        "state_id": state_id,
        "version": version,
        "frozen": frozen,
        "snapshot": snapshot,
        "plan": plan,
    }
