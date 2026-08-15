from __future__ import annotations

"""Persistent, inspectable research-state contracts for Research Librarian v7.4.0.

Research state is user/project workflow memory, not factual evidence. The module keeps
activity history, per-object review state, and open questions separate so that the
Librarian can continue work without silently converting prior user actions into claims.
"""

from collections import Counter
import hashlib
import json
from typing import Any
import uuid

from .models import utc_now

RESEARCH_ACTIVITY_SCHEMA = "sc-research-activity-event/1.0"
RESEARCH_OBJECT_STATE_SCHEMA = "sc-research-object-state/1.0"
OPEN_QUESTION_SCHEMA = "sc-research-open-question/1.0"
RESEARCH_STATE_SUMMARY_SCHEMA = "sc-research-state-summary/1.0"
RESEARCH_STATE_PROMPT_SCHEMA = "sc-research-state-prompt/1.0"

ACTIVITY_TYPES = {
    "search",
    "save",
    "open",
    "read",
    "review",
    "reject",
    "restore",
    "contradiction-flagged",
    "contradiction-resolved",
    "question-opened",
    "question-resolved",
    "question-deferred",
    "workspace-promotion-prepared",
    "workspace-promotion-imported",
    "federated-search",
    "federated-result-saved",
    "lifecycle-stage-transition",
    "lifecycle-checkpoint",
    "note",
}

READING_STATES = {"unread", "reading", "reviewed", "rejected"}
CONTRADICTION_STATES = {"none", "flagged", "resolved"}
QUESTION_STATUSES = {"open", "resolved", "deferred", "dismissed"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _string_list(value: Any, limit: int = 100, item_limit: int = 220) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        clean = str(item or "").strip()[:item_limit]
        if not clean or clean in seen:
            continue
        seen.add(clean)
        output.append(clean)
        if len(output) >= limit:
            break
    return output


def normalize_activity(payload: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    event_type = str(payload.get("event_type") or "note").strip().lower().replace("_", "-")
    if event_type not in ACTIVITY_TYPES:
        raise ValueError(f"Unsupported research activity type: {event_type or 'empty'}")
    clean = {
        "schema": RESEARCH_ACTIVITY_SCHEMA,
        "event_id": str(payload.get("event_id") or _id("research-event"))[:220],
        "owner_ref": str(payload.get("owner_ref") or "")[:220],
        "project_id": str(payload.get("project_id") or "")[:220],
        "context_id": str(payload.get("context_id") or "")[:220],
        "object_id": str(payload.get("object_id") or "")[:220],
        "event_type": event_type,
        "query": str(payload.get("query") or "").strip()[:3000],
        "note": str(payload.get("note") or "").strip()[:4000],
        "metadata": dict(payload.get("metadata") or {}),
        "created_utc": str(payload.get("created_utc") or now)[:80],
        "governance": {
            "workflow_memory_only": True,
            "not_evidence": True,
            "user_visible": True,
        },
    }
    clean["fingerprint"] = fingerprint({key: value for key, value in clean.items() if key != "fingerprint"})
    return clean


def normalize_object_state(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    now = utc_now()
    reading_state = str(payload.get("reading_state") or existing.get("reading_state") or "unread").strip().lower()
    contradiction_state = str(payload.get("contradiction_state") or existing.get("contradiction_state") or "none").strip().lower()
    if reading_state not in READING_STATES:
        raise ValueError(f"Unsupported reading state: {reading_state or 'empty'}")
    if contradiction_state not in CONTRADICTION_STATES:
        raise ValueError(f"Unsupported contradiction state: {contradiction_state or 'empty'}")
    clean = {
        "schema": RESEARCH_OBJECT_STATE_SCHEMA,
        "state_id": str(payload.get("state_id") or existing.get("state_id") or _id("object-state"))[:220],
        "owner_ref": str(payload.get("owner_ref") or existing.get("owner_ref") or "")[:220],
        "project_id": str(payload.get("project_id") or existing.get("project_id") or "")[:220],
        "context_id": str(payload.get("context_id") or existing.get("context_id") or "")[:220],
        "object_id": str(payload.get("object_id") or existing.get("object_id") or "")[:220],
        "reading_state": reading_state,
        "contradiction_state": contradiction_state,
        "note": str(payload.get("note") if "note" in payload else existing.get("note") or "").strip()[:4000],
        "first_seen_utc": str(existing.get("first_seen_utc") or payload.get("first_seen_utc") or now)[:80],
        "last_seen_utc": now,
        "reviewed_utc": str(payload.get("reviewed_utc") or existing.get("reviewed_utc") or (now if reading_state == "reviewed" else ""))[:80],
        "rejected_utc": str(payload.get("rejected_utc") or existing.get("rejected_utc") or (now if reading_state == "rejected" else ""))[:80],
        "updated_utc": now,
        "governance": {
            "state_is_user_workflow": True,
            "rejection_is_not_source_deletion": True,
            "contradiction_flag_requires_review": contradiction_state == "flagged",
        },
    }
    clean["fingerprint"] = fingerprint({key: value for key, value in clean.items() if key != "fingerprint"})
    return clean


def normalize_open_question(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = existing or {}
    now = utc_now()
    status = str(payload.get("status") or existing.get("status") or "open").strip().lower()
    if status not in QUESTION_STATUSES:
        raise ValueError(f"Unsupported research question status: {status or 'empty'}")
    question = str(payload.get("question") or existing.get("question") or "").strip()[:3000]
    if not question:
        raise ValueError("Research question text is required.")
    clean = {
        "schema": OPEN_QUESTION_SCHEMA,
        "question_id": str(payload.get("question_id") or existing.get("question_id") or _id("open-question"))[:220],
        "owner_ref": str(payload.get("owner_ref") or existing.get("owner_ref") or "")[:220],
        "project_id": str(payload.get("project_id") or existing.get("project_id") or "")[:220],
        "context_id": str(payload.get("context_id") or existing.get("context_id") or "")[:220],
        "question": question,
        "status": status,
        "linked_object_ids": _string_list(payload.get("linked_object_ids") if "linked_object_ids" in payload else existing.get("linked_object_ids"), 100),
        "resolution": str(payload.get("resolution") if "resolution" in payload else existing.get("resolution") or "").strip()[:6000],
        "created_utc": str(existing.get("created_utc") or payload.get("created_utc") or now)[:80],
        "updated_utc": now,
        "resolved_utc": str(payload.get("resolved_utc") or existing.get("resolved_utc") or (now if status == "resolved" else ""))[:80],
        "governance": {
            "open_question_is_not_fact": True,
            "resolution_requires_explicit_state_change": True,
        },
    }
    clean["fingerprint"] = fingerprint({key: value for key, value in clean.items() if key != "fingerprint"})
    return clean


def summarize_research_state(
    activities: list[dict[str, Any]],
    object_states: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    *,
    owner_ref: str = "",
    project_id: str = "",
    context_id: str = "",
) -> dict[str, Any]:
    activity_counts = dict(Counter(str(item.get("event_type") or "unknown") for item in activities))
    reading_counts = dict(Counter(str(item.get("reading_state") or "unread") for item in object_states))
    contradiction_counts = dict(Counter(str(item.get("contradiction_state") or "none") for item in object_states))
    question_counts = dict(Counter(str(item.get("status") or "open") for item in questions))
    recent_searches = [
        {
            "event_id": str(item.get("event_id") or ""),
            "query": str(item.get("query") or ""),
            "project_id": str(item.get("project_id") or ""),
            "context_id": str(item.get("context_id") or ""),
            "created_utc": str(item.get("created_utc") or ""),
        }
        for item in activities
        if str(item.get("event_type") or "") == "search" and str(item.get("query") or "").strip()
    ][:10]
    open_questions = [item for item in questions if str(item.get("status") or "open") == "open"][:25]
    review_queue = [item for item in object_states if str(item.get("reading_state") or "unread") in {"unread", "reading"}][:50]
    rejected = [item for item in object_states if str(item.get("reading_state") or "") == "rejected"][:50]
    contradicted = [item for item in object_states if str(item.get("contradiction_state") or "") == "flagged"][:50]
    summary = {
        "schema": RESEARCH_STATE_SUMMARY_SCHEMA,
        "owner_ref": owner_ref,
        "project_id": project_id,
        "context_id": context_id,
        "counts": {
            "activities": len(activities),
            "object_states": len(object_states),
            "questions": len(questions),
            "activity_types": activity_counts,
            "reading_states": reading_counts,
            "contradiction_states": contradiction_counts,
            "question_states": question_counts,
        },
        "recent_searches": recent_searches,
        "open_questions": open_questions,
        "review_queue": review_queue,
        "rejected_objects": rejected,
        "flagged_contradictions": contradicted,
        "governance": {
            "state_is_inspectable": True,
            "state_is_editable": True,
            "state_is_not_evidence": True,
            "rejected_objects_are_not_deleted": True,
            "open_questions_are_not_assumptions": True,
        },
        "generated_utc": utc_now(),
    }
    summary["fingerprint"] = fingerprint({key: value for key, value in summary.items() if key not in {"fingerprint", "generated_utc"}})
    return summary


def prompt_research_state(summary: dict[str, Any]) -> dict[str, Any]:
    """Create a bounded prompt view of explicit research workflow state.

    The prompt deliberately omits free-form notes/resolutions from object states and keeps
    prior searches/open questions labeled as workflow memory rather than evidence.
    """
    if not isinstance(summary, dict):
        return {}
    recent_searches = [
        {"query": str(item.get("query") or "")[:1000], "created_utc": str(item.get("created_utc") or "")[:80]}
        for item in list(summary.get("recent_searches") or [])[:8]
        if isinstance(item, dict) and str(item.get("query") or "").strip()
    ]
    open_questions = [
        {
            "question_id": str(item.get("question_id") or "")[:220],
            "question": str(item.get("question") or "")[:1200],
            "status": "open",
            "linked_object_ids": _string_list(item.get("linked_object_ids"), 20),
        }
        for item in list(summary.get("open_questions") or [])[:12]
        if isinstance(item, dict) and str(item.get("question") or "").strip()
    ]
    rejected_ids = [str(item.get("object_id") or "")[:220] for item in list(summary.get("rejected_objects") or [])[:50] if isinstance(item, dict) and str(item.get("object_id") or "")]
    flagged_ids = [str(item.get("object_id") or "")[:220] for item in list(summary.get("flagged_contradictions") or [])[:50] if isinstance(item, dict) and str(item.get("object_id") or "")]
    review_queue_ids = [str(item.get("object_id") or "")[:220] for item in list(summary.get("review_queue") or [])[:50] if isinstance(item, dict) and str(item.get("object_id") or "")]
    clean = {
        "schema": RESEARCH_STATE_PROMPT_SCHEMA,
        "project_id": str(summary.get("project_id") or "")[:220],
        "context_id": str(summary.get("context_id") or "")[:220],
        "recent_searches": recent_searches,
        "open_questions": open_questions,
        "review_queue_object_ids": review_queue_ids,
        "rejected_object_ids": rejected_ids,
        "flagged_contradiction_object_ids": flagged_ids,
        "boundary_note": "This is explicit, inspectable workflow memory. It is not factual evidence. Do not cite prior searches or open questions as support. Do not silently reopen resolved questions. Rejected items remain part of provenance but should not be treated as preferred evidence unless the user asks to revisit them.",
    }
    clean["fingerprint"] = fingerprint(clean)
    return clean
