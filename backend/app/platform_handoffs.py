from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Iterable
import uuid

from .config import settings
from .models import EvidenceCitation, RetrievedSource

HANDOFF_SCHEMA = "sc-research-handoff/2.0"
ROUTE_SCHEMA = "sc-research-route/2.0"
ARTIFACT_SCHEMA = "sc-research-artifact-return/1.0"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _capability(
    destination: str,
    label: str,
    url: str,
    enabled: bool,
    version: str,
    accepts: list[str],
    returns: list[str],
    health: str = "configured",
) -> dict[str, Any]:
    return {
        "id": destination,
        "label": label,
        "available": bool(enabled and url),
        "state": health if enabled and url else "disabled",
        "url": url,
        "version": version or "unknown",
        "contract": HANDOFF_SCHEMA,
        "accepts": accepts,
        "returns": returns,
    }


def capability_catalog() -> dict[str, dict[str, Any]]:
    """Return a public-safe capability registry.

    Capabilities are configuration-driven so unavailable destinations disappear
    from public actions without weakening retrieval or the deterministic fallback.
    """

    return {
        "workbench": _capability(
            "workbench",
            "Sustainable Catalyst Workbench",
            settings.workbench_url,
            settings.workbench_enabled,
            settings.workbench_version,
            ["question", "equations", "variables", "units", "assumptions", "datasets", "evidence"],
            ["calculation_report", "graph", "validation_record", "reproducible_code"],
        ),
        "decision_studio": _capability(
            "decision_studio",
            "Sustainable Catalyst Decision Studio",
            settings.decision_studio_url,
            settings.decision_studio_enabled,
            settings.decision_studio_version,
            ["decision_question", "evidence", "alternatives", "criteria", "assumptions", "uncertainties"],
            ["decision_packet", "scenario_comparison", "audit_appendix", "brief"],
        ),
        "site_intelligence": _capability(
            "site_intelligence",
            "Sustainable Catalyst Site Intelligence",
            settings.site_intelligence_url,
            settings.site_intelligence_enabled,
            settings.site_intelligence_version,
            ["places", "countries", "indicators", "time_range", "source_requirements", "evidence"],
            ["country_brief", "indicator_dashboard", "map_view", "source_ledger"],
        ),
        "lab": _capability(
            "lab",
            "Sustainable Catalyst Lab",
            settings.lab_url,
            settings.lab_enabled,
            settings.lab_version,
            ["research_question", "hypotheses", "datasets", "instrumentation", "calculations", "evidence"],
            ["experiment_record", "calculation_notebook", "validation_report", "reproducibility_bundle"],
        ),
        "feature_suggestions": _capability(
            "feature_suggestions",
            "Feature Suggestions",
            settings.feature_suggestions_url,
            settings.feature_suggestions_enabled,
            settings.feature_suggestions_version,
            ["requested_capability", "workflow_context", "evidence"],
            ["suggestion_record"],
        ),
    }


def public_capabilities() -> list[dict[str, Any]]:
    return [deepcopy(item) for item in capability_catalog().values()]


def available_capabilities() -> dict[str, dict[str, Any]]:
    return {key: value for key, value in capability_catalog().items() if value["available"]}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9_-]+", (text or "").lower())


def infer_destination(question: str, research_mode: str = "auto", route_hint: dict[str, Any] | None = None) -> str:
    hint = route_hint or {}
    explicit = str(hint.get("destination") or hint.get("handoff_target") or "").strip().lower().replace("-", "_")
    aliases = {
        "decision": "decision_studio",
        "decisionstudio": "decision_studio",
        "site": "site_intelligence",
        "siteintelligence": "site_intelligence",
        "science_lab": "lab",
        "laboratory": "lab",
        "feature": "feature_suggestions",
    }
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
        rows.append(
            {
                "record_id": source.id,
                "title": source.title,
                "url": source.url,
                "citation_label": source.citation_label or (citation.id if citation else ""),
                "section": source.section or (citation.section if citation else ""),
                "page": source.page or (citation.page if citation else None),
                "passage": source.passage or (citation.passage if citation else source.summary),
                "content_hash": source.score_breakdown.get("content_hash", "") if source.score_breakdown else "",
                "retrieval_reasons": list(source.retrieval_reasons),
            }
        )
    return rows


def _extract_equations(question: str) -> list[str]:
    candidates = re.findall(r"(?:[A-Za-z][A-Za-z0-9_]*\s*=\s*[A-Za-z0-9_+\-*/^().]+|\b[A-Za-z]+\([^\n]{1,80}\))", question or "")
    return list(dict.fromkeys(item.strip() for item in candidates))[:8]


def _extract_units(question: str) -> list[str]:
    unit_pattern = r"\b(?:m|km|cm|mm|kg|g|s|ms|h|K|C|Pa|kPa|MPa|W|kW|MW|V|A|ohm|Hz|mol|L|mL|%|USD)\b"
    return list(dict.fromkeys(re.findall(unit_pattern, question or "", flags=re.IGNORECASE)))[:20]


def _extract_places(question: str) -> list[str]:
    known = [
        "United States", "Canada", "Mexico", "Pakistan", "India", "Kenya", "Nigeria", "China", "Japan",
        "Brazil", "Germany", "France", "United Kingdom", "Chicago", "St. Louis", "New York", "California",
    ]
    lower = (question or "").lower()
    return [place for place in known if place.lower() in lower][:12]


def _common_envelope(
    destination: str,
    question: str,
    research_mode: str,
    session_id: str,
    matches: list[RetrievedSource],
    evidence: list[EvidenceCitation],
    assumptions: list[str] | None,
    uncertainties: list[str] | None,
    route_hint: dict[str, Any] | None,
) -> dict[str, Any]:
    capabilities = capability_catalog()
    capability = capabilities.get(destination)
    if not capability or not capability["available"]:
        raise ValueError(f"Destination '{destination}' is not currently available.")
    sources = _source_context(matches, evidence)
    route = {
        "schema": ROUTE_SCHEMA,
        "research_mode": research_mode,
        "destination": destination,
        "destination_label": capability["label"],
        "destination_url": capability["url"],
        "destination_version": capability["version"],
        "reason": str((route_hint or {}).get("reason") or f"The request maps to the {capability['label']} input contract."),
    }
    envelope = {
        "schema": HANDOFF_SCHEMA,
        "handoff_id": "handoff-" + uuid.uuid4().hex,
        "created_utc": _now(),
        "expires_utc": "",
        "source_system": "research_librarian",
        "source_version": settings.release_version,
        "session_id": session_id,
        "question": question,
        "route": route,
        "destination": destination,
        "destination_contract": HANDOFF_SCHEMA,
        "status": "prepared",
        "evidence": sources,
        "assumptions": [str(item)[:1000] for item in (assumptions or []) if str(item).strip()][:25],
        "uncertainties": [str(item)[:1000] for item in (uncertainties or []) if str(item).strip()][:25],
        "human_confirmation_required": True,
        "boundaries": [
            "The handoff is a reviewable draft and does not execute work automatically.",
            "Evidence, assumptions, units, methods, and consequential interpretations require human review.",
            "The destination must validate the contract and its own capability version before accepting the payload.",
        ],
        "provenance": {
            "source_record_ids": [item["record_id"] for item in sources],
            "source_urls": [item["url"] for item in sources],
            "retrieval_labels": [item["citation_label"] for item in sources if item["citation_label"]],
            "parent_handoff_id": str((route_hint or {}).get("parent_handoff_id") or ""),
            "chain": ["research_question", "verified_retrieval", "typed_handoff"],
        },
    }
    return envelope


def _target_payload(destination: str, question: str, evidence: list[dict[str, Any]], route_hint: dict[str, Any] | None) -> dict[str, Any]:
    hint = route_hint or {}
    if destination == "workbench":
        return {
            "contract": "sc-workbench-task/1.0",
            "task_type": str(hint.get("task_type") or "analysis"),
            "equations": list(hint.get("equations") or _extract_equations(question))[:20],
            "variables": list(hint.get("variables") or [])[:50],
            "units": list(hint.get("units") or _extract_units(question))[:30],
            "datasets": list(hint.get("datasets") or [])[:20],
            "requested_outputs": list(hint.get("requested_outputs") or ["calculation_report", "validation_warnings", "reproducible_method"]),
            "validation_requirements": ["show_inputs", "show_units", "show_assumptions", "show_method", "flag_out_of_range_values"],
            "evidence_context": evidence,
        }
    if destination == "decision_studio":
        return {
            "contract": "sc-decision-packet-seed/1.0",
            "decision_question": question,
            "alternatives": list(hint.get("alternatives") or [])[:20],
            "criteria": list(hint.get("criteria") or [])[:30],
            "scenarios": list(hint.get("scenarios") or [])[:20],
            "evidence_ledger": evidence,
            "requested_outputs": list(hint.get("requested_outputs") or ["decision_packet", "assumption_register", "uncertainty_register", "audit_appendix"]),
            "workbench_result_ids": list(hint.get("workbench_result_ids") or [])[:20],
        }
    if destination == "site_intelligence":
        return {
            "contract": "sc-site-intelligence-query/1.0",
            "places": list(hint.get("places") or _extract_places(question))[:30],
            "countries": list(hint.get("countries") or [])[:30],
            "indicators": list(hint.get("indicators") or [])[:50],
            "time_range": dict(hint.get("time_range") or {}),
            "event_types": list(hint.get("event_types") or [])[:30],
            "source_requirements": list(hint.get("source_requirements") or ["public", "attributable", "freshness_visible", "methodology_visible"]),
            "requested_outputs": list(hint.get("requested_outputs") or ["source_aware_brief", "indicator_view", "map_view"]),
            "evidence_context": evidence,
        }
    if destination == "lab":
        return {
            "contract": "sc-lab-workflow/1.0",
            "research_question": question,
            "domain": str(hint.get("domain") or "auto-detect"),
            "hypotheses": list(hint.get("hypotheses") or [])[:20],
            "experiment_type": str(hint.get("experiment_type") or "analysis-or-simulation"),
            "datasets": list(hint.get("datasets") or [])[:20],
            "instrumentation": list(hint.get("instrumentation") or [])[:30],
            "calculations": list(hint.get("calculations") or _extract_equations(question))[:30],
            "requested_outputs": list(hint.get("requested_outputs") or ["experiment_record", "validation_report", "reproducibility_bundle"]),
            "evidence_context": evidence,
        }
    return {
        "contract": "sc-feature-suggestion/1.0",
        "requested_capability": question,
        "workflow_context": dict(hint),
        "evidence_context": evidence,
        "requested_outputs": ["suggestion_record"],
    }


def validate_handoff(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required = ["schema", "handoff_id", "created_utc", "source_system", "source_version", "question", "route", "destination", "payload", "provenance"]
    for field in required:
        if field not in payload or payload[field] in (None, "", []):
            errors.append(f"Missing required field: {field}")
    if payload.get("schema") != HANDOFF_SCHEMA:
        errors.append(f"Unsupported handoff schema: {payload.get('schema', '')}")
    destination = str(payload.get("destination") or "")
    catalog = capability_catalog()
    if destination not in catalog:
        errors.append("Unknown destination.")
    elif not catalog[destination]["available"]:
        errors.append("Destination is not currently available.")
    route = payload.get("route") if isinstance(payload.get("route"), dict) else {}
    if route.get("schema") != ROUTE_SCHEMA:
        errors.append("Route schema is missing or unsupported.")
    target = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    if not target.get("contract"):
        errors.append("Destination payload contract is missing.")
    if not payload.get("evidence"):
        warnings.append("No verified source records are attached to this handoff.")
    provenance = payload.get("provenance") if isinstance(payload.get("provenance"), dict) else {}
    expected = provenance.get("payload_fingerprint")
    if expected:
        copy = deepcopy(payload)
        copy.pop("validation", None)
        copy.setdefault("provenance", {}).pop("payload_fingerprint", None)
        actual = _fingerprint(copy)
        if expected != actual:
            errors.append("Payload fingerprint does not match the handoff contents.")
    return {
        "ok": not errors,
        "schema": HANDOFF_SCHEMA,
        "destination": destination,
        "errors": errors,
        "warnings": warnings,
    }


def prepare_handoff(
    destination: str,
    question: str,
    research_mode: str,
    session_id: str,
    matches: list[RetrievedSource],
    evidence: list[EvidenceCitation],
    assumptions: list[str] | None = None,
    uncertainties: list[str] | None = None,
    route_hint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    destination = (destination or infer_destination(question, research_mode, route_hint)).strip().lower().replace("-", "_")
    envelope = _common_envelope(destination, question, research_mode, session_id, matches, evidence, assumptions, uncertainties, route_hint)
    envelope["payload"] = _target_payload(destination, question, envelope["evidence"], route_hint)
    fingerprint_copy = deepcopy(envelope)
    envelope["provenance"]["payload_fingerprint"] = _fingerprint(fingerprint_copy)
    validation = validate_handoff(envelope)
    envelope["validation"] = validation
    return envelope


def prepare_preview_handoffs(
    question: str,
    research_mode: str,
    session_id: str,
    matches: list[RetrievedSource],
    evidence: list[EvidenceCitation],
    route_hint: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    previews: list[dict[str, Any]] = []
    for destination in suggested_destinations(question, research_mode, route_hint):
        try:
            previews.append(prepare_handoff(destination, question, research_mode, session_id, matches, evidence, route_hint=route_hint))
        except ValueError:
            continue
    return previews


def validate_artifact_return(payload: dict[str, Any], original_handoff: dict[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    required = ["schema", "artifact_id", "handoff_id", "destination", "artifact_type", "created_utc", "artifact", "provenance"]
    for field in required:
        if field not in payload or payload[field] in (None, "", []):
            errors.append(f"Missing required field: {field}")
    if payload.get("schema") != ARTIFACT_SCHEMA:
        errors.append("Unsupported artifact-return schema.")
    if original_handoff:
        if payload.get("handoff_id") != original_handoff.get("handoff_id"):
            errors.append("Artifact return does not reference the stored handoff.")
        if payload.get("destination") != original_handoff.get("destination"):
            errors.append("Artifact destination does not match the stored handoff.")
    return {"ok": not errors, "errors": errors, "schema": ARTIFACT_SCHEMA}
