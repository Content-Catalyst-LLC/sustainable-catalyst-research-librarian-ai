from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
from typing import Any, Iterable
import uuid

from .config import settings
from .models import EvidenceCitation, RetrievedSource

HANDOFF_SCHEMA = "sc-research-handoff/2.0"
ROUTE_SCHEMA = "sc-research-route/2.0"
ARTIFACT_SCHEMA = "sc-research-artifact-return/1.0"
CAPABILITIES_SCHEMA = "sc-platform-capabilities/1.1"
COMPATIBILITY_SCHEMA = "sc-platform-compatibility/1.0"
DELIVERY_SCHEMA = "sc-research-handoff-delivery/1.0"
RECEIPT_SCHEMA = "sc-research-handoff-receipt/1.0"

_DESTINATION_SPECS: dict[str, dict[str, Any]] = {
    "workbench": {
        "label": "Sustainable Catalyst Workbench",
        "minimum_version": "4.0.0",
        "payload_contract": "sc-workbench-task/1.0",
        "accepts": ["question", "equations", "variables", "units", "assumptions", "datasets", "evidence"],
        "returns": ["calculation_report", "graph", "validation_record", "reproducible_code"],
    },
    "decision_studio": {
        "label": "Sustainable Catalyst Decision Studio",
        "minimum_version": "1.0.0",
        "payload_contract": "sc-decision-packet-seed/1.0",
        "accepts": ["decision_question", "evidence", "alternatives", "criteria", "assumptions", "uncertainties"],
        "returns": ["decision_packet", "scenario_comparison", "audit_appendix", "brief"],
    },
    "site_intelligence": {
        "label": "Sustainable Catalyst Site Intelligence",
        "minimum_version": "2.0.0",
        "payload_contract": "sc-site-intelligence-query/1.0",
        "accepts": ["places", "countries", "indicators", "time_range", "source_requirements", "evidence"],
        "returns": ["country_brief", "indicator_dashboard", "map_view", "source_ledger"],
    },
    "lab": {
        "label": "Sustainable Catalyst Lab",
        "minimum_version": "0.6.0",
        "payload_contract": "sc-lab-workflow/1.0",
        "accepts": ["research_question", "hypotheses", "datasets", "instrumentation", "calculations", "evidence"],
        "returns": ["experiment_record", "calculation_notebook", "validation_report", "reproducibility_bundle"],
    },
    "feature_suggestions": {
        "label": "Feature Suggestions",
        "minimum_version": "3.0.0",
        "payload_contract": "sc-feature-suggestion/1.0",
        "accepts": ["requested_capability", "workflow_context", "evidence"],
        "returns": ["suggestion_record"],
    },
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _version_tuple(version: str) -> tuple[int, int, int] | None:
    match = re.search(r"(?<!\d)(\d+)\.(\d+)(?:\.(\d+))?", str(version or ""))
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3) or 0))


def version_compatibility(version: str, minimum_version: str, enabled: bool = True, url: str = "") -> dict[str, Any]:
    if not enabled or not url:
        return {"state": "disabled", "compatible": False, "verified": True, "reason": "Destination is disabled or has no URL."}
    current = _version_tuple(version)
    minimum = _version_tuple(minimum_version)
    if current is None:
        return {"state": "unverified", "compatible": True, "verified": False, "reason": "Destination version is unknown; intake must validate the contract."}
    compatible = bool(minimum and current >= minimum)
    return {
        "state": "compatible" if compatible else "incompatible",
        "compatible": compatible,
        "verified": True,
        "reason": "Destination meets the minimum supported version." if compatible else f"Destination requires version {minimum_version} or newer.",
    }


def _destination_config(destination: str) -> tuple[bool, str, str]:
    mapping = {
        "workbench": (settings.workbench_enabled, settings.workbench_url, settings.workbench_version),
        "decision_studio": (settings.decision_studio_enabled, settings.decision_studio_url, settings.decision_studio_version),
        "site_intelligence": (settings.site_intelligence_enabled, settings.site_intelligence_url, settings.site_intelligence_version),
        "lab": (settings.lab_enabled, settings.lab_url, settings.lab_version),
        "feature_suggestions": (settings.feature_suggestions_enabled, settings.feature_suggestions_url, settings.feature_suggestions_version),
    }
    return mapping[destination]


def capability_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for destination, spec in _DESTINATION_SPECS.items():
        enabled, url, version = _destination_config(destination)
        compatibility = version_compatibility(version, str(spec["minimum_version"]), enabled, url)
        catalog[destination] = {
            "id": destination,
            "label": spec["label"],
            "configured": bool(enabled and url),
            "available": bool(enabled and url and compatibility["compatible"]),
            "state": compatibility["state"],
            "url": url,
            "version": version or "unknown",
            "minimum_version": spec["minimum_version"],
            "contract": HANDOFF_SCHEMA,
            "payload_contract": spec["payload_contract"],
            "accepts": list(spec["accepts"]),
            "returns": list(spec["returns"]),
            "compatibility": compatibility,
        }
    return catalog


def public_capabilities() -> list[dict[str, Any]]:
    return [deepcopy(item) for item in capability_catalog().values()]


def compatibility_report() -> dict[str, Any]:
    capabilities = public_capabilities()
    counts = {state: sum(1 for item in capabilities if item["state"] == state) for state in ("compatible", "unverified", "incompatible", "disabled")}
    return {
        "schema": COMPATIBILITY_SCHEMA,
        "source_version": settings.release_version,
        "generated_utc": _now(),
        "counts": counts,
        "destinations": capabilities,
        "ready": not any(item["state"] == "incompatible" for item in capabilities),
    }


def available_capabilities() -> dict[str, dict[str, Any]]:
    return {key: value for key, value in capability_catalog().items() if value["available"]}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9_-]+", (text or "").lower())


def infer_destination(question: str, research_mode: str = "auto", route_hint: dict[str, Any] | None = None) -> str:
    hint = route_hint or {}
    explicit = str(hint.get("destination") or hint.get("handoff_target") or "").strip().lower().replace("-", "_")
    aliases = {"decision": "decision_studio", "decisionstudio": "decision_studio", "site": "site_intelligence", "siteintelligence": "site_intelligence", "science_lab": "lab", "laboratory": "lab", "feature": "feature_suggestions"}
    explicit = aliases.get(explicit, explicit)
    if explicit in capability_catalog():
        return explicit
    q = " ".join(_tokens(question))
    if re.search(r"\b(missing feature|feature request|unsupported|does not exist|new capability)\b", q):
        return "feature_suggestions"
    if research_mode == "decision" or re.search(r"\b(decision|tradeoff|scenario|alternative|criteria|recommendation|brief|packet)\b", q):
        return "decision_studio"
    if re.search(r"\b(country|countries|indicator|indicators|geographic|geospatial|map|earth observation|satellite|event|disaster|displacement)\b", q):
        return "site_intelligence"
    if re.search(r"\b(experiment|hypothesis|protocol|instrument|laboratory|spectrometry|biology|chemistry|physics|astronomy|engineering validation)\b", q):
        return "lab"
    if research_mode == "analyze" or re.search(r"\b(calculate|equation|formula|graph|model|simulation|units|sensitivity|statistics|code)\b", q):
        return "workbench"
    return ""


def suggested_destinations(question: str, research_mode: str = "auto", route_hint: dict[str, Any] | None = None) -> list[str]:
    available = available_capabilities()
    primary = infer_destination(question, research_mode, route_hint)
    result: list[str] = []
    if primary and primary in available:
        result.append(primary)
    q = (question or "").lower()
    if primary == "site_intelligence" and "decision_studio" in available and re.search(r"decision|compare|brief|scenario", q):
        result.append("decision_studio")
    if primary == "lab" and "workbench" in available and re.search(r"calculate|model|equation|statistics|simulate", q):
        result.append("workbench")
    if primary == "workbench" and "decision_studio" in available and re.search(r"decision|tradeoff|recommend", q):
        result.append("decision_studio")
    return list(dict.fromkeys(result))[:2]


def _source_context(matches: Iterable[RetrievedSource], evidence: Iterable[EvidenceCitation], max_sources: int | None = None) -> list[dict[str, Any]]:
    limit = max_sources or settings.handoff_source_limit
    evidence_by_record = {item.record_id: item for item in evidence}
    rows: list[dict[str, Any]] = []
    for source in list(matches)[:limit]:
        citation = evidence_by_record.get(source.id)
        rows.append({
            "record_id": source.id, "title": source.title, "url": source.url,
            "citation_label": source.citation_label or (citation.id if citation else ""),
            "section": source.section or (citation.section if citation else ""),
            "page": source.page or (citation.page if citation else None),
            "passage": source.passage or (citation.passage if citation else source.summary),
            "content_hash": source.score_breakdown.get("content_hash", "") if source.score_breakdown else "",
            "retrieval_reasons": list(source.retrieval_reasons),
        })
    return rows


def _extract_equations(question: str) -> list[str]:
    candidates = re.findall(r"(?:[A-Za-z][A-Za-z0-9_]*\s*=\s*[A-Za-z0-9_+\-*/^().]+|\b[A-Za-z]+\([^\n]{1,80}\))", question or "")
    return list(dict.fromkeys(item.strip() for item in candidates))[:8]


def _extract_units(question: str) -> list[str]:
    pattern = r"\b(?:m|km|cm|mm|kg|g|s|ms|h|K|C|Pa|kPa|MPa|W|kW|MW|V|A|ohm|Hz|mol|L|mL|%|USD)\b"
    return list(dict.fromkeys(re.findall(pattern, question or "", flags=re.IGNORECASE)))[:20]


def _extract_places(question: str) -> list[str]:
    known = ["United States", "Canada", "Mexico", "Pakistan", "India", "Kenya", "Nigeria", "China", "Japan", "Brazil", "Germany", "France", "United Kingdom", "Chicago", "St. Louis", "New York", "California"]
    lower = (question or "").lower()
    return [place for place in known if place.lower() in lower][:12]


def _target_payload(destination: str, question: str, evidence: list[dict[str, Any]], route_hint: dict[str, Any] | None) -> dict[str, Any]:
    hint = route_hint or {}
    if destination == "workbench":
        return {"contract": "sc-workbench-task/1.0", "task_type": str(hint.get("task_type") or "analysis"), "equations": list(hint.get("equations") or _extract_equations(question))[:20], "variables": list(hint.get("variables") or [])[:50], "units": list(hint.get("units") or _extract_units(question))[:30], "datasets": list(hint.get("datasets") or [])[:20], "requested_outputs": list(hint.get("requested_outputs") or ["calculation_report", "validation_warnings", "reproducible_method"]), "validation_requirements": ["show_inputs", "show_units", "show_assumptions", "show_method", "flag_out_of_range_values"], "evidence_context": evidence}
    if destination == "decision_studio":
        return {"contract": "sc-decision-packet-seed/1.0", "decision_question": question, "alternatives": list(hint.get("alternatives") or [])[:20], "criteria": list(hint.get("criteria") or [])[:30], "scenarios": list(hint.get("scenarios") or [])[:20], "evidence_ledger": evidence, "requested_outputs": list(hint.get("requested_outputs") or ["decision_packet", "assumption_register", "uncertainty_register", "audit_appendix"]), "workbench_result_ids": list(hint.get("workbench_result_ids") or [])[:20]}
    if destination == "site_intelligence":
        return {"contract": "sc-site-intelligence-query/1.0", "places": list(hint.get("places") or _extract_places(question))[:30], "countries": list(hint.get("countries") or [])[:30], "indicators": list(hint.get("indicators") or [])[:50], "time_range": dict(hint.get("time_range") or {}), "event_types": list(hint.get("event_types") or [])[:30], "source_requirements": list(hint.get("source_requirements") or ["public", "attributable", "freshness_visible", "methodology_visible"]), "requested_outputs": list(hint.get("requested_outputs") or ["source_aware_brief", "indicator_view", "map_view"]), "evidence_context": evidence}
    if destination == "lab":
        return {"contract": "sc-lab-workflow/1.0", "research_question": question, "domain": str(hint.get("domain") or "auto-detect"), "hypotheses": list(hint.get("hypotheses") or [])[:20], "experiment_type": str(hint.get("experiment_type") or "analysis-or-simulation"), "datasets": list(hint.get("datasets") or [])[:20], "instrumentation": list(hint.get("instrumentation") or [])[:30], "calculations": list(hint.get("calculations") or _extract_equations(question))[:30], "requested_outputs": list(hint.get("requested_outputs") or ["experiment_record", "validation_report", "reproducibility_bundle"]), "evidence_context": evidence}
    return {"contract": "sc-feature-suggestion/1.0", "requested_capability": question, "workflow_context": dict(hint), "evidence_context": evidence, "requested_outputs": ["suggestion_record"]}


def _token_secret() -> bytes:
    return (settings.api_key or "sc-research-librarian-local-token").encode("utf-8")


def issue_delivery_token(handoff_id: str, destination: str, expires_utc: str) -> str:
    message = f"{handoff_id}|{destination}|{expires_utc}".encode("utf-8")
    return hmac.new(_token_secret(), message, hashlib.sha256).hexdigest()


def validate_delivery_token(handoff: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    delivery = handoff.get("delivery") if isinstance(handoff.get("delivery"), dict) else {}
    expires_utc = str(delivery.get("token_expires_utc") or handoff.get("expires_utc") or "")
    supplied = token or str(delivery.get("token") or "")
    expected = issue_delivery_token(str(handoff.get("handoff_id") or ""), str(handoff.get("destination") or ""), expires_utc) if expires_utc else ""
    expiry = _parse_utc(expires_utc)
    expired = expiry is None or expiry <= _now_dt()
    valid = bool(supplied and expected and hmac.compare_digest(supplied, expected) and not expired)
    return {"ok": valid, "expired": expired, "expires_utc": expires_utc, "error": "" if valid else ("Delivery token expired." if expired else "Delivery token is invalid.")}


def _refingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    payload.pop("validation", None)
    copy = deepcopy(payload)
    copy.setdefault("provenance", {}).pop("payload_fingerprint", None)
    payload.setdefault("provenance", {})["payload_fingerprint"] = fingerprint(copy)
    payload["validation"] = validate_handoff(payload)
    return payload


def refresh_handoff_delivery(handoff: dict[str, Any], reason: str = "manual-refresh", increment_attempt: bool = False) -> dict[str, Any]:
    refreshed = deepcopy(handoff)
    delivery = refreshed.setdefault("delivery", {})
    attempt = int(delivery.get("attempt") or 0) + (1 if increment_attempt else 0)
    max_attempts = int(delivery.get("max_attempts") or settings.handoff_retry_limit)
    if attempt > max_attempts:
        raise ValueError("The handoff retry limit has been reached.")
    expires = (_now_dt() + timedelta(seconds=settings.handoff_ttl_seconds)).isoformat()
    delivery.update({"schema": DELIVERY_SCHEMA, "attempt": attempt, "max_attempts": max_attempts, "token_expires_utc": expires, "token": issue_delivery_token(str(refreshed.get("handoff_id") or ""), str(refreshed.get("destination") or ""), expires), "last_refresh_utc": _now(), "last_refresh_reason": reason[:240]})
    refreshed["expires_utc"] = expires
    refreshed["status"] = "retry-ready" if increment_attempt else "token-refreshed"
    return _refingerprint(refreshed)


def validate_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required = ["schema", "handoff_id", "created_utc", "source_system", "source_version", "question", "route", "destination", "payload", "provenance", "delivery"]
    for field in required:
        if field not in payload or payload[field] in (None, "", []):
            errors.append(f"Missing required field: {field}")
    if payload.get("schema") != HANDOFF_SCHEMA:
        errors.append(f"Unsupported handoff schema: {payload.get('schema', '')}")
    destination = str(payload.get("destination") or "")
    catalog = capability_catalog()
    capability = catalog.get(destination)
    if not capability:
        errors.append("Unknown destination.")
    elif not capability["available"]:
        errors.append(f"Destination is not available: {capability['compatibility']['reason']}")
    route = payload.get("route") if isinstance(payload.get("route"), dict) else {}
    if route.get("schema") != ROUTE_SCHEMA:
        errors.append("Route schema is missing or unsupported.")
    target = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    if not target.get("contract"):
        errors.append("Destination payload contract is missing.")
    elif capability and target.get("contract") != capability.get("payload_contract"):
        errors.append("Destination payload contract does not match the declared capability.")
    if not payload.get("evidence"):
        warnings.append("No verified source records are attached to this handoff.")
    token_validation = validate_delivery_token(payload)
    if not token_validation["ok"]:
        errors.append(token_validation["error"])
    provenance = payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    expected = provenance.get("payload_fingerprint")
    if expected:
        copy = deepcopy(payload)
        copy.pop("validation", None)
        copy.setdefault("provenance", {}).pop("payload_fingerprint", None)
        if expected != fingerprint(copy):
            errors.append("Payload fingerprint does not match the handoff contents.")
    return {"ok": not errors, "schema": HANDOFF_SCHEMA, "destination": destination, "compatibility": capability.get("compatibility", {}) if capability else {}, "token": token_validation, "errors": errors, "warnings": warnings}


def prepare_handoff(destination: str, question: str, research_mode: str, session_id: str, matches: list[RetrievedSource], evidence: list[EvidenceCitation], assumptions: list[str] | None = None, uncertainties: list[str] | None = None, route_hint: dict[str, Any] | None = None, idempotency_key: str = "") -> dict[str, Any]:
    destination = (destination or infer_destination(question, research_mode, route_hint)).strip().lower().replace("-", "_")
    capability = capability_catalog().get(destination)
    if not capability or not capability["available"]:
        reason = capability["compatibility"]["reason"] if capability else "Unknown destination."
        raise ValueError(f"Destination '{destination}' is not currently available. {reason}")
    sources = _source_context(matches, evidence)
    handoff_id = "handoff-" + uuid.uuid4().hex
    expires = (_now_dt() + timedelta(seconds=settings.handoff_ttl_seconds)).isoformat()
    route = {"schema": ROUTE_SCHEMA, "research_mode": research_mode, "destination": destination, "destination_label": capability["label"], "destination_url": capability["url"], "destination_version": capability["version"], "minimum_destination_version": capability["minimum_version"], "compatibility": capability["compatibility"], "reason": str((route_hint or {}).get("reason") or f"The request maps to the {capability['label']} input contract.")}
    envelope: dict[str, Any] = {
        "schema": HANDOFF_SCHEMA, "handoff_id": handoff_id, "created_utc": _now(), "expires_utc": expires,
        "source_system": "research_librarian", "source_version": settings.release_version, "session_id": session_id,
        "question": question, "route": route, "destination": destination, "destination_contract": HANDOFF_SCHEMA,
        "status": "prepared", "evidence": sources,
        "assumptions": [str(item)[:1000] for item in (assumptions or []) if str(item).strip()][:25],
        "uncertainties": [str(item)[:1000] for item in (uncertainties or []) if str(item).strip()][:25],
        "human_confirmation_required": True,
        "boundaries": ["The handoff is a reviewable draft and does not execute work automatically.", "Evidence, assumptions, units, methods, and consequential interpretations require human review.", "The destination must validate the contract, token, and capability version before accepting the payload."],
        "delivery": {"schema": DELIVERY_SCHEMA, "attempt": 0, "max_attempts": settings.handoff_retry_limit, "token_expires_utc": expires, "token": issue_delivery_token(handoff_id, destination, expires), "last_refresh_utc": _now(), "last_refresh_reason": "initial-prepare", "next_retry_utc": ""},
        "idempotency_key": str(idempotency_key or "")[:220],
        "provenance": {"source_record_ids": [item["record_id"] for item in sources], "source_urls": [item["url"] for item in sources], "retrieval_labels": [item["citation_label"] for item in sources if item["citation_label"]], "parent_handoff_id": str((route_hint or {}).get("parent_handoff_id") or ""), "chain": ["research_question", "verified_retrieval", "typed_handoff"]},
    }
    envelope["payload"] = _target_payload(destination, question, sources, route_hint)
    return _refingerprint(envelope)


def prepare_preview_handoffs(question: str, research_mode: str, session_id: str, matches: list[RetrievedSource], evidence: list[EvidenceCitation], route_hint: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for destination in suggested_destinations(question, research_mode, route_hint):
        try:
            previews.append(prepare_handoff(destination, question, research_mode, session_id, matches, evidence, route_hint=route_hint))
        except ValueError:
            continue
    return previews


def validate_receipt(payload: dict[str, Any], original_handoff: dict[str, Any] | None) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema") != RECEIPT_SCHEMA:
        errors.append("Unsupported handoff-receipt schema.")
    for field in ("receipt_id", "handoff_id", "destination", "status", "created_utc"):
        if not payload.get(field):
            errors.append(f"Missing required field: {field}")
    if original_handoff is None:
        errors.append("Original handoff was not found.")
    else:
        if payload.get("handoff_id") != original_handoff.get("handoff_id"):
            errors.append("Receipt does not reference the stored handoff.")
        if payload.get("destination") != original_handoff.get("destination"):
            errors.append("Receipt destination does not match the stored handoff.")
        if not payload.get("handoff_fingerprint"):
            errors.append("Receipt handoff fingerprint is required.")
        elif payload.get("handoff_fingerprint") != (original_handoff.get("provenance") or {}).get("payload_fingerprint"):
            errors.append("Receipt handoff fingerprint does not match the stored handoff.")
        if not payload.get("delivery_token"):
            errors.append("Receipt delivery token is required.")
        else:
            token_check = validate_delivery_token(original_handoff, str(payload.get("delivery_token") or ""))
            if not token_check["ok"]:
                errors.append(token_check["error"])
    allowed_status = {"accepted", "rejected", "processing", "completed", "failed"}
    if payload.get("status") not in allowed_status:
        errors.append("Receipt status is unsupported.")
    return {"ok": not errors, "schema": RECEIPT_SCHEMA, "errors": errors}


def validate_artifact_return(payload: dict[str, Any], original_handoff: dict[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    for field in ("schema", "artifact_id", "handoff_id", "destination", "artifact_type", "created_utc", "artifact", "provenance"):
        if field not in payload or payload[field] in (None, "", []):
            errors.append(f"Missing required field: {field}")
    if payload.get("schema") != ARTIFACT_SCHEMA:
        errors.append("Unsupported artifact-return schema.")
    destination = str(payload.get("destination") or "")
    capability = capability_catalog().get(destination)
    if not capability:
        errors.append("Unknown artifact destination.")
    elif str(payload.get("artifact_type") or "") not in set(capability.get("returns") or []):
        errors.append("Artifact type is not declared by the destination capability.")
    artifact_bytes = len(canonical_json(payload.get("artifact") or {}).encode("utf-8"))
    if artifact_bytes > settings.handoff_max_artifact_bytes:
        errors.append("Artifact payload exceeds the configured size limit.")
    artifact_fingerprint = fingerprint({"handoff_id": payload.get("handoff_id"), "destination": destination, "artifact_type": payload.get("artifact_type"), "artifact": payload.get("artifact")})
    supplied_fingerprint = str((payload.get("provenance") or {}).get("artifact_fingerprint") or "")
    if supplied_fingerprint and supplied_fingerprint != artifact_fingerprint:
        errors.append("Artifact fingerprint does not match the returned payload.")
    if original_handoff:
        base_validation = validate_handoff(original_handoff)
        non_token_errors = [error for error in base_validation["errors"] if "token" not in error.lower() and "expired" not in error.lower()]
        if non_token_errors:
            errors.append("Stored handoff no longer passes provenance validation.")
        if payload.get("handoff_id") != original_handoff.get("handoff_id"):
            errors.append("Artifact return does not reference the stored handoff.")
        if destination != original_handoff.get("destination"):
            errors.append("Artifact destination does not match the stored handoff.")
        supplied_handoff_fp = str((payload.get("provenance") or {}).get("research_librarian_handoff_fingerprint") or "")
        expected_handoff_fp = str((original_handoff.get("provenance") or {}).get("payload_fingerprint") or "")
        if supplied_handoff_fp and supplied_handoff_fp != expected_handoff_fp:
            errors.append("Artifact provenance does not match the original handoff fingerprint.")
    return {"ok": not errors, "errors": errors, "schema": ARTIFACT_SCHEMA, "artifact_fingerprint": artifact_fingerprint, "artifact_bytes": artifact_bytes}
