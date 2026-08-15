from __future__ import annotations

"""Governed Workspace artifact promotion contracts for Research Librarian v7.7.0.

A promotion is an exportable research handoff snapshot, not publication and not a
claim that the included evidence is true. It preserves source ownership/scope,
participant attribution, research-state boundaries, and source fingerprints so
Workspace can ingest the packet without laundering provenance.
"""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
import uuid

PROMOTION_SCHEMA = "sc-workspace-artifact-promotion/1.0"
PROMOTION_PACKET_SCHEMA = "sc-workspace-research-handoff/1.0"
PROMOTION_SUMMARY_SCHEMA = "sc-workspace-promotion-summary/1.0"
PROMOTION_RECEIPT_SCHEMA = "sc-workspace-promotion-receipt/1.0"
WORKSPACE_IMPORT_CONTRACT = "sc-workspace-research-import/1.0"

ARTIFACT_TYPES = {
    "notebook": {
        "label": "Workspace Notebook",
        "contract": "sc-workspace-notebook-seed/1.0",
        "sections": ["research-context", "sources", "open-questions", "research-notes", "room-collaboration"],
    },
    "evidence-set": {
        "label": "Workspace Evidence Set",
        "contract": "sc-workspace-evidence-set/1.0",
        "sections": ["sources", "evidence-quality", "contradictions", "provenance"],
    },
    "analysis": {
        "label": "Workspace Analysis",
        "contract": "sc-workspace-analysis-seed/1.0",
        "sections": ["research-question", "sources", "evidence-quality", "open-questions", "contradictions", "assumptions"],
    },
    "document": {
        "label": "Workspace Document",
        "contract": "sc-workspace-document-seed/1.0",
        "sections": ["research-context", "outline", "sources", "citation-pack", "open-questions"],
    },
    "citation-pack": {
        "label": "Workspace Citation Pack",
        "contract": "sc-workspace-citation-pack/1.0",
        "sections": ["citations", "sources", "provenance"],
    },
}

PROMOTION_STATES = {"prepared", "exported", "imported", "superseded", "cancelled"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _safe_list(value: Any, limit: int = 200) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value[:limit]:
        clean = str(item or "").strip()[:220]
        if clean and clean not in out:
            out.append(clean)
    return out


def _source_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    provenance = dict(item.get("provenance") or {})
    relationships = dict(item.get("relationships") or {})
    payload = dict(item.get("payload") or {})
    return {
        "object_id": str(item.get("object_id") or "")[:220],
        "object_type": str(item.get("object_type") or "source")[:80],
        "title": str(item.get("title") or "Untitled source")[:500],
        "description": str(item.get("description") or "")[:4000],
        "owner_ref": str(item.get("owner_ref") or "")[:220],
        "source_scope": str(item.get("source_scope") or "my-library")[:80],
        "visibility": str(item.get("visibility") or "private")[:40],
        "status": str(item.get("status") or "saved")[:60],
        "tags": [str(v)[:100] for v in list(item.get("tags") or [])[:50]],
        "source_record_id": str(provenance.get("source_record_id") or payload.get("source_record_id") or "")[:220],
        "url": str(provenance.get("url") or payload.get("url") or item.get("url") or "")[:2000],
        "citation": dict(provenance.get("citation") or payload.get("citation") or {}),
        "publisher": str(provenance.get("publisher") or payload.get("publisher") or "")[:500],
        "published_date": str(provenance.get("published_date") or payload.get("published_date") or "")[:80],
        "methodology": str(provenance.get("methodology") or payload.get("methodology") or "")[:4000],
        "limitations": str(provenance.get("limitations") or payload.get("limitations") or "")[:4000],
        "relationships": {
            "project_ids": _safe_list(relationships.get("project_ids"), 100),
            "room_ids": _safe_list(relationships.get("room_ids"), 100),
        },
        "source_fingerprint": str(item.get("fingerprint") or "")[:128],
        "governance": {
            "source_scope_preserved": True,
            "owner_attribution_preserved": True,
            "promotion_does_not_change_editorial_status": True,
        },
    }


def _citation_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    citation = dict(source.get("citation") or {})
    return {
        "object_id": source.get("object_id", ""),
        "title": source.get("title", ""),
        "url": source.get("url", ""),
        "publisher": source.get("publisher", ""),
        "published_date": source.get("published_date", ""),
        "citation": citation,
        "source_scope": source.get("source_scope", ""),
        "owner_ref": source.get("owner_ref", ""),
        "source_fingerprint": source.get("source_fingerprint", ""),
    }


def build_workspace_packet(
    *,
    artifact_type: str,
    title: str,
    owner_ref: str,
    project: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    sources: list[dict[str, Any]] | None = None,
    research_state: dict[str, Any] | None = None,
    evidence_quality: dict[str, Any] | None = None,
    room_synthesis: dict[str, Any] | None = None,
    selected_object_ids: list[str] | None = None,
    include_rejected: bool = False,
    notes: str = "",
    promotion_id: str = "",
) -> dict[str, Any]:
    artifact_type = str(artifact_type or "notebook").strip().lower()
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"Unsupported Workspace artifact type: {artifact_type or 'empty'}")
    owner_ref = str(owner_ref or "").strip()[:220]
    if not owner_ref:
        raise ValueError("Workspace promotion requires owner_ref.")

    source_rows = [_source_snapshot(item) for item in list(sources or [])[:500] if isinstance(item, dict)]
    selected = set(_safe_list(selected_object_ids or [], 500))
    if selected:
        source_rows = [item for item in source_rows if item["object_id"] in selected]

    state = dict(research_state or {})
    state_rows = list(state.get("object_states") or [])
    rejected_ids = {
        str(item.get("object_id") or "")
        for item in state_rows
        if isinstance(item, dict) and str(item.get("reading_state") or "").lower() == "rejected"
    }
    if not include_rejected:
        source_rows = [item for item in source_rows if item["object_id"] not in rejected_ids]

    room = dict(room_synthesis or {})
    context_data = dict(context or {})
    project_data = dict(project or {})
    quality = dict(evidence_quality or {})
    open_questions = list(state.get("open_questions") or [])[:200]
    contradictions = [
        item for item in state_rows
        if isinstance(item, dict) and str(item.get("contradiction_state") or "none") != "none"
    ][:200]

    packet = {
        "schema": PROMOTION_PACKET_SCHEMA,
        "workspace_import_contract": WORKSPACE_IMPORT_CONTRACT,
        "promotion_id": str(promotion_id or _id("workspace-promotion"))[:220],
        "artifact_type": artifact_type,
        "artifact_contract": ARTIFACT_TYPES[artifact_type]["contract"],
        "artifact_label": ARTIFACT_TYPES[artifact_type]["label"],
        "title": str(title or ARTIFACT_TYPES[artifact_type]["label"]).strip()[:500],
        "owner_ref": owner_ref,
        "created_utc": utc_now(),
        "project": {
            "project_id": str(project_data.get("project_id") or "")[:220],
            "title": str(project_data.get("title") or "")[:500],
            "objective": str(project_data.get("objective") or "")[:4000],
            "fingerprint": str(project_data.get("fingerprint") or "")[:128],
        },
        "research_context": {
            "context_id": str(context_data.get("context_id") or "")[:220],
            "title": str(context_data.get("title") or "")[:500],
            "scopes": _safe_list(context_data.get("scopes"), 10),
            "project_id": str(context_data.get("project_id") or "")[:220],
            "room_id": str(context_data.get("room_id") or "")[:220],
            "fingerprint": str(context_data.get("fingerprint") or "")[:128],
        },
        "sources": source_rows,
        "citation_pack": [_citation_snapshot(item) for item in source_rows],
        "open_questions": open_questions,
        "contradictions": contradictions,
        "evidence_quality": quality,
        "room_collaboration": room,
        "research_notes": str(notes or "")[:12000],
        "requested_sections": list(ARTIFACT_TYPES[artifact_type]["sections"]),
        "promotion_options": {
            "include_rejected": bool(include_rejected),
            "selected_object_ids": sorted(selected),
        },
        "provenance": {
            "source_count": len(source_rows),
            "source_fingerprints": {item["object_id"]: item["source_fingerprint"] for item in source_rows if item["object_id"]},
            "participant_attribution_preserved": True,
            "personal_and_room_state_remain_distinct": True,
            "source_scope_preserved": True,
            "promotion_is_snapshot": True,
        },
        "governance": {
            "promotion_is_not_publication": True,
            "promotion_is_not_editorial_approval": True,
            "promotion_is_not_truth_judgment": True,
            "workspace_import_requires_explicit_user_action": True,
            "workspace_may_not_silently_reclassify_source_scope": True,
            "rejected_sources_excluded_by_default": True,
        },
    }
    packet["packet_fingerprint"] = fingerprint({k: v for k, v in packet.items() if k != "packet_fingerprint"})
    return packet


def normalize_promotion(payload: dict[str, Any], packet: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    now = utc_now()
    status = str(payload.get("status") or existing.get("status") or "prepared").strip().lower()
    if status not in PROMOTION_STATES:
        raise ValueError(f"Unsupported Workspace promotion state: {status or 'empty'}")
    record = {
        "schema": PROMOTION_SCHEMA,
        "promotion_id": str(packet.get("promotion_id") or payload.get("promotion_id") or existing.get("promotion_id") or _id("workspace-promotion"))[:220],
        "owner_ref": str(payload.get("owner_ref") or existing.get("owner_ref") or packet.get("owner_ref") or "")[:220],
        "project_id": str(payload.get("project_id") or existing.get("project_id") or (packet.get("project") or {}).get("project_id") or "")[:220],
        "context_id": str(payload.get("context_id") or existing.get("context_id") or (packet.get("research_context") or {}).get("context_id") or "")[:220],
        "room_id": str(payload.get("room_id") or existing.get("room_id") or (packet.get("research_context") or {}).get("room_id") or "")[:220],
        "artifact_type": str(packet.get("artifact_type") or payload.get("artifact_type") or existing.get("artifact_type") or "notebook")[:80],
        "title": str(packet.get("title") or payload.get("title") or existing.get("title") or "Workspace research handoff")[:500],
        "status": status,
        "created_utc": str(existing.get("created_utc") or payload.get("created_utc") or now)[:80],
        "updated_utc": now,
        "packet_fingerprint": str(packet.get("packet_fingerprint") or "")[:128],
        "packet": packet,
        "receipt": dict(existing.get("receipt") or {}),
        "governance": dict(packet.get("governance") or {}),
    }
    record["fingerprint"] = fingerprint({k: v for k, v in record.items() if k != "fingerprint"})
    return record


def apply_promotion_receipt(promotion: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    expected = str(promotion.get("packet_fingerprint") or "")
    received = str(receipt.get("packet_fingerprint") or "")
    if not expected or received != expected:
        raise ValueError("Workspace receipt packet fingerprint does not match the prepared promotion.")
    status = str(receipt.get("status") or "imported").strip().lower()
    if status not in {"imported", "exported"}:
        raise ValueError("Workspace receipt status must be imported or exported.")
    clean_receipt = {
        "schema": PROMOTION_RECEIPT_SCHEMA,
        "promotion_id": str(promotion.get("promotion_id") or "")[:220],
        "packet_fingerprint": expected,
        "status": status,
        "workspace_artifact_id": str(receipt.get("workspace_artifact_id") or "")[:220],
        "workspace_artifact_type": str(receipt.get("workspace_artifact_type") or promotion.get("artifact_type") or "")[:80],
        "workspace_url": str(receipt.get("workspace_url") or "")[:2000],
        "received_utc": str(receipt.get("received_utc") or utc_now())[:80],
        "actor_ref": str(receipt.get("actor_ref") or "")[:220],
        "governance": {"receipt_confirms_transfer_only": True, "does_not_confirm_publication": True},
    }
    clean_receipt["fingerprint"] = fingerprint({k: v for k, v in clean_receipt.items() if k != "fingerprint"})
    updated = dict(promotion)
    updated["status"] = status
    updated["receipt"] = clean_receipt
    updated["updated_utc"] = utc_now()
    updated["fingerprint"] = fingerprint({k: v for k, v in updated.items() if k != "fingerprint"})
    return updated


def promotion_summary(promotions: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = Counter(str(item.get("status") or "prepared") for item in promotions)
    by_type = Counter(str(item.get("artifact_type") or "notebook") for item in promotions)
    return {
        "schema": PROMOTION_SUMMARY_SCHEMA,
        "count": len(promotions),
        "by_status": dict(by_status),
        "by_artifact_type": dict(by_type),
        "recent": promotions[:25],
        "governance": {"promotion_outbox_is_not_publication_log": True},
    }


def artifact_catalog() -> list[dict[str, Any]]:
    return [
        {"id": key, "label": value["label"], "contract": value["contract"], "sections": list(value["sections"])}
        for key, value in ARTIFACT_TYPES.items()
    ]
