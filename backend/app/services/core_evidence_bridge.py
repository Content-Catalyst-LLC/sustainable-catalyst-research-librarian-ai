from __future__ import annotations

import hashlib
from typing import Any

from ..clients.platform_core import PlatformCoreClient, PlatformCoreError
from ..config import settings
from ..contracts.evidence_bridge import (
    CORE_EVIDENCE_BRIDGE_SCHEMA,
    CorePassageEvidencePromotionRequest,
    CoreSourceSnapshotPromotionRequest,
)
from ..contracts.platform_core import CORE_INTEGRATION_SCHEMA
from ..models import utc_now
from ..source_identity import get_source_graph_store
from ..store import store
from .platform_core_integration import CoreBindingConflict, _base_binding, _sha


def _bridge_idempotency(local_kind: str, local_id: str, supplied: str | None) -> str:
    if supplied and supplied.strip():
        return supplied.strip()
    return f"rl-{settings.release_version}:{local_kind}:{hashlib.sha256(local_id.encode()).hexdigest()[:32]}"


def _existing_or_conflict_bridge(local_kind: str, local_id: str, payload_hash: str) -> dict[str, Any] | None:
    existing = store.platform_core_binding(local_kind, local_id)
    if not existing:
        return None
    if existing.get("payload_hash") == payload_hash and existing.get("sync_state") == "synced" and existing.get("core_id"):
        return existing
    if existing.get("payload_hash") != payload_hash:
        raise CoreBindingConflict(
            "This Librarian evidence-bridge object is already bound to Platform Core with different content. "
            "Create an explicit revised snapshot/evidence object instead of overwriting governed Core state."
        )
    return None


def _failure_bridge(binding: dict[str, Any], exc: Exception) -> None:
    store.save_platform_core_binding({
        **binding,
        "sync_state": "failed",
        "updated_utc": utc_now(),
        "last_error": str(exc)[:2000],
    })


def _safe_fragment(value: str, limit: int = 72) -> str:
    keep = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or ""))
    while "--" in keep:
        keep = keep.replace("--", "-")
    keep = keep.strip("-")
    return (keep[:limit] or hashlib.sha256(str(value).encode()).hexdigest()[:limit])


def _snapshot_core_id(local_snapshot_id: str) -> str:
    digest = hashlib.sha256(local_snapshot_id.encode()).hexdigest()[:20]
    return f"sc:snapshot:research-librarian:{_safe_fragment(local_snapshot_id, 54)}:{digest}"


def _evidence_core_id(local_evidence_id: str) -> str:
    digest = hashlib.sha256(local_evidence_id.encode()).hexdigest()[:20]
    return f"sc:evidence:research-librarian:{_safe_fragment(local_evidence_id, 54)}:{digest}"


def _select_instance(source: dict[str, Any], requested: str | None) -> dict[str, Any]:
    instances = list(source.get("instances") or [])
    if requested:
        for item in instances:
            if str(item.get("instance_id") or "") == requested:
                return item
        raise ValueError(f"Source instance not found for canonical source: {requested}")
    if not instances:
        return {}
    resolved = [x for x in instances if x.get("content_fingerprint") or x.get("source_url")]
    return resolved[-1] if resolved else instances[-1]


def _canonical_url(source: dict[str, Any], instance: dict[str, Any]) -> str | None:
    url = str(instance.get("source_url") or "").strip()
    if url:
        return url
    identifiers = source.get("identifiers") or {}
    dois = identifiers.get("doi") or []
    if dois:
        return f"https://doi.org/{dois[0]}"
    arxiv = identifiers.get("arxiv") or []
    if arxiv:
        return f"https://arxiv.org/abs/{arxiv[0]}"
    return None


def evidence_bridge_capabilities() -> dict[str, Any]:
    return {
        "schema": CORE_EVIDENCE_BRIDGE_SCHEMA,
        "release": settings.release_version,
        "platform_core_minimum": settings.core_minimum_version,
        "source_snapshot_promotion": True,
        "passage_evidence_promotion": True,
        "canonical_source_identity_required": True,
        "durable_librarian_core_bindings": True,
        "immutable_promotions": True,
        "automatic_claim_creation": False,
        "automatic_stance_inference": False,
        "automatic_confidence_inference": False,
        "default_review_status": "unreviewed",
        "default_stance": "neutral",
        "core_is_governed_evidence_authority": True,
    }


async def promote_source_snapshot(
    request: CoreSourceSnapshotPromotionRequest,
    client: PlatformCoreClient | None = None,
) -> dict[str, Any]:
    source = get_source_graph_store().get(request.canonical_source_id)
    if not source:
        raise ValueError("Canonical Librarian source does not exist; resolve it before Core promotion.")
    if str(source.get("state") or "") == "stub":
        raise ValueError("Citation-only source stubs cannot be promoted as governed Core source snapshots until hydrated.")

    instance = _select_instance(source, request.source_instance_id)
    local_snapshot_id = request.local_snapshot_id or str(instance.get("instance_id") or request.canonical_source_id)
    local_kind = "source-snapshot"
    idempotency_key = _bridge_idempotency(local_kind, local_snapshot_id, request.idempotency_key)
    core_id = _snapshot_core_id(local_snapshot_id)

    content_hash = request.content_hash
    if request.content is not None:
        observed = hashlib.sha256(request.content.encode("utf-8")).hexdigest()
        if content_hash and content_hash != observed:
            raise ValueError("Provided source snapshot content_hash does not match content.")
        content_hash = observed
    if not content_hash:
        candidate = str(instance.get("content_fingerprint") or "").lower().strip()
        if len(candidate) == 64 and all(ch in "0123456789abcdef" for ch in candidate):
            content_hash = candidate
    if not content_hash:
        raise ValueError("A lowercase SHA-256 content_hash or snapshot content is required for Core promotion.")

    metadata = {
        **(source.get("metadata") or {}),
        **request.metadata,
        "source_product": "research-librarian",
        "source_release": settings.release_version,
        "integration_schema": CORE_INTEGRATION_SCHEMA,
        "evidence_bridge_schema": CORE_EVIDENCE_BRIDGE_SCHEMA,
        "canonical_source_id": request.canonical_source_id,
        "source_instance_id": str(instance.get("instance_id") or ""),
        "source_identifiers": source.get("identifiers") or {},
        "source_authors": source.get("authors") or [],
        "source_institutions": source.get("institutions") or [],
        "idempotency_key": idempotency_key,
    }
    payload: dict[str, Any] = {
        "id": core_id,
        "canonical_url": _canonical_url(source, instance),
        "title": request.title or source.get("title") or None,
        "publisher": request.publisher or None,
        "published_at": request.published_at.isoformat() if request.published_at else None,
        "retrieved_at": request.retrieved_at.isoformat() if request.retrieved_at else None,
        "media_type": request.media_type or instance.get("media_type") or "application/octet-stream",
        "content_hash": content_hash,
        "storage_uri": request.storage_uri,
        "archived_url": request.archived_url,
        "metadata": metadata,
        "actor": request.actor,
    }
    if request.content is not None:
        payload["content"] = request.content
        payload.pop("content_hash", None)
    payload = {k: v for k, v in payload.items() if v is not None}
    payload_hash = _sha(payload)
    existing = _existing_or_conflict_bridge(local_kind, local_snapshot_id, payload_hash)
    if existing:
        return {
            "schema": CORE_EVIDENCE_BRIDGE_SCHEMA,
            "idempotent_replay": True,
            "binding": existing,
            "canonical_source": source,
        }

    binding = _base_binding(local_kind, local_snapshot_id, "source-snapshot", payload_hash, idempotency_key)
    binding.update({
        "core_id": core_id,
        "canonical_source_id": request.canonical_source_id,
        "source_instance_id": str(instance.get("instance_id") or ""),
        "request": payload,
    })
    store.save_platform_core_binding(binding)
    core = client or PlatformCoreClient()
    try:
        result = await core.create_source_snapshot(payload)
    except PlatformCoreError as exc:
        if exc.status_code == 409:
            try:
                result = await core.source_snapshot(core_id)
                if str((result.get("metadata") or {}).get("canonical_source_id") or "") not in {"", request.canonical_source_id}:
                    raise PlatformCoreError("Recovered Core snapshot identity does not match the Librarian canonical source.", status_code=409, detail=result)
            except PlatformCoreError:
                _failure_bridge(binding, exc)
                raise
        else:
            _failure_bridge(binding, exc)
            raise
    synced = {
        **binding,
        "core_id": str(result.get("id") or core_id),
        "sync_state": "synced",
        "updated_utc": utc_now(),
        "last_error": "",
        "core_response": result,
    }
    saved = store.save_platform_core_binding(synced)
    return {
        "schema": CORE_EVIDENCE_BRIDGE_SCHEMA,
        "idempotent_replay": False,
        "binding": saved,
        "core": result,
        "canonical_source": source,
    }


async def promote_passage_evidence(
    request: CorePassageEvidencePromotionRequest,
    client: PlatformCoreClient | None = None,
) -> dict[str, Any]:
    source = get_source_graph_store().get(request.canonical_source_id)
    if not source:
        raise ValueError("Canonical Librarian source does not exist.")
    snapshot = store.platform_core_binding("source-snapshot", request.source_snapshot_local_id)
    if not snapshot or snapshot.get("sync_state") != "synced" or not snapshot.get("core_id"):
        raise CoreBindingConflict(
            "The passage cannot be promoted until its Librarian source snapshot has a synced Platform Core binding."
        )
    bound_source = str(snapshot.get("canonical_source_id") or "")
    if bound_source and bound_source != request.canonical_source_id:
        raise CoreBindingConflict("The source snapshot binding belongs to a different canonical Librarian source.")

    local_kind = "evidence-record"
    idempotency_key = _bridge_idempotency(local_kind, request.local_evidence_id, request.idempotency_key)
    core_id = _evidence_core_id(request.local_evidence_id)
    passage_hash = hashlib.sha256(request.statement.encode("utf-8")).hexdigest()
    provenance = {
        **request.provenance,
        "source_product": "research-librarian",
        "source_release": settings.release_version,
        "integration_schema": CORE_INTEGRATION_SCHEMA,
        "evidence_bridge_schema": CORE_EVIDENCE_BRIDGE_SCHEMA,
        "canonical_source_id": request.canonical_source_id,
        "source_snapshot_local_id": request.source_snapshot_local_id,
        "source_snapshot_core_id": snapshot.get("core_id"),
        "passage_id": request.passage_id or "",
        "chunk_id": request.chunk_id or "",
        "passage_sha256": passage_hash,
        "section_path": request.section_path,
        "page_start": request.page_start,
        "page_end": request.page_end,
        "idempotency_key": idempotency_key,
        "automated_truth_judgment": False,
    }
    metadata = {
        **request.metadata,
        "research_librarian_local_evidence_id": request.local_evidence_id,
        "canonical_source_id": request.canonical_source_id,
        "source_identifiers": source.get("identifiers") or {},
        "passage_sha256": passage_hash,
        "stance_supplied_explicitly": request.stance != "neutral",
        "confidence_supplied_explicitly": request.confidence is not None,
    }
    payload: dict[str, Any] = {
        "id": core_id,
        "evidence_type": request.evidence_type,
        "stance": request.stance,
        "claim_id": request.claim_id,
        "subject_entity_id": request.subject_entity_id,
        "source_snapshot_id": snapshot.get("core_id"),
        "statement": request.statement,
        "methodology": request.methodology,
        "confidence": request.confidence,
        "review_status": request.review_status,
        "provenance": provenance,
        "metadata": metadata,
        "actor": request.actor,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    payload_hash = _sha(payload)
    existing = _existing_or_conflict_bridge(local_kind, request.local_evidence_id, payload_hash)
    if existing:
        return {"schema": CORE_EVIDENCE_BRIDGE_SCHEMA, "idempotent_replay": True, "binding": existing}

    binding = _base_binding(local_kind, request.local_evidence_id, "evidence-record", payload_hash, idempotency_key)
    binding.update({
        "core_id": core_id,
        "canonical_source_id": request.canonical_source_id,
        "source_snapshot_local_id": request.source_snapshot_local_id,
        "source_snapshot_core_id": snapshot.get("core_id"),
        "request": payload,
    })
    store.save_platform_core_binding(binding)
    core = client or PlatformCoreClient()
    try:
        result = await core.create_evidence_record(payload)
    except PlatformCoreError as exc:
        if exc.status_code == 409:
            try:
                result = await core.evidence_record(core_id)
                core_provenance = result.get("provenance") or {}
                if str(core_provenance.get("canonical_source_id") or "") not in {"", request.canonical_source_id}:
                    raise PlatformCoreError("Recovered Core evidence identity does not match the Librarian canonical source.", status_code=409, detail=result)
            except PlatformCoreError:
                _failure_bridge(binding, exc)
                raise
        else:
            _failure_bridge(binding, exc)
            raise
    synced = {
        **binding,
        "core_id": str(result.get("id") or core_id),
        "sync_state": "synced",
        "updated_utc": utc_now(),
        "last_error": "",
        "core_response": result,
    }
    saved = store.save_platform_core_binding(synced)
    return {"schema": CORE_EVIDENCE_BRIDGE_SCHEMA, "idempotent_replay": False, "binding": saved, "core": result}
