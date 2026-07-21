from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any
import uuid

from .models import KnowledgeRecord, RetrievedSource, utc_now

POLICY_SCHEMA = "sc-research-governance-policy/1.0"
TRACE_SCHEMA = "sc-research-answer-trace/1.0"
EVALUATION_SCHEMA = "sc-research-quality-evaluation/1.0"
RELEASE_GATE_SCHEMA = "sc-research-release-gate/1.0"
METHODOLOGY_SCHEMA = "sc-research-methodology/1.0"
SOURCE_REVIEW_SCHEMA = "sc-research-source-review/1.0"

DEFAULT_GOVERNANCE_POLICY: dict[str, Any] = {
    "schema": POLICY_SCHEMA,
    "profile": "public-trust-v7.0.8",
    "source_controls": {
        "require_approved_sources": False,
        "exclude_rejected_sources": True,
        "stale_after_days": 730,
        "warn_on_stale_sources": True,
        "block_expired_reviews": False,
    },
    "quality_thresholds": {
        "exact_title_accuracy": 0.90,
        "hit_at_3": 0.85,
        "citation_precision": 0.95,
        "citation_completeness": 0.90,
        "unsupported_claim_rate_max": 0.05,
        "route_accuracy": 0.80,
        "pdf_page_accuracy": 0.80,
        "fallback_success": 0.95,
        "minimum_answer_quality": 0.80,
    },
    "retention": {
        "answer_trace_days": 30,
        "quality_evaluation_days": 365,
        "governance_event_days": 365,
        "store_query_text": False,
        "store_answer_text": False,
        "hash_session_ids": True,
    },
    "human_review": {
        "required_for_policy_changes": True,
        "required_for_release_override": True,
        "required_for_source_exclusion": True,
        "allow_automatic_publication": False,
    },
    "boundaries": {
        "professional_advice": ["medical", "legal", "financial", "clinical"],
        "diagnosis_or_certification": False,
        "autonomous_publishing": False,
        "unreviewed_ranking_changes": False,
    },
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _bounded_float(value: Any, default: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def sanitize_governance_policy(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    defaults = DEFAULT_GOVERNANCE_POLICY
    source = raw.get("source_controls") if isinstance(raw.get("source_controls"), dict) else {}
    thresholds = raw.get("quality_thresholds") if isinstance(raw.get("quality_thresholds"), dict) else {}
    retention = raw.get("retention") if isinstance(raw.get("retention"), dict) else {}
    human = raw.get("human_review") if isinstance(raw.get("human_review"), dict) else {}
    boundaries = raw.get("boundaries") if isinstance(raw.get("boundaries"), dict) else {}
    clean = {
        "schema": POLICY_SCHEMA,
        "profile": str(raw.get("profile") or defaults["profile"])[:100],
        "source_controls": {
            "require_approved_sources": bool(source.get("require_approved_sources", defaults["source_controls"]["require_approved_sources"])),
            "exclude_rejected_sources": bool(source.get("exclude_rejected_sources", defaults["source_controls"]["exclude_rejected_sources"])),
            "stale_after_days": _bounded_int(source.get("stale_after_days"), defaults["source_controls"]["stale_after_days"], 1, 3650),
            "warn_on_stale_sources": bool(source.get("warn_on_stale_sources", defaults["source_controls"]["warn_on_stale_sources"])),
            "block_expired_reviews": bool(source.get("block_expired_reviews", defaults["source_controls"]["block_expired_reviews"])),
        },
        "quality_thresholds": {},
        "retention": {
            "answer_trace_days": _bounded_int(retention.get("answer_trace_days"), defaults["retention"]["answer_trace_days"], 1, 3650),
            "quality_evaluation_days": _bounded_int(retention.get("quality_evaluation_days"), defaults["retention"]["quality_evaluation_days"], 30, 3650),
            "governance_event_days": _bounded_int(retention.get("governance_event_days"), defaults["retention"]["governance_event_days"], 30, 3650),
            "store_query_text": bool(retention.get("store_query_text", defaults["retention"]["store_query_text"])),
            "store_answer_text": bool(retention.get("store_answer_text", defaults["retention"]["store_answer_text"])),
            "hash_session_ids": bool(retention.get("hash_session_ids", defaults["retention"]["hash_session_ids"])),
        },
        "human_review": {
            "required_for_policy_changes": bool(human.get("required_for_policy_changes", defaults["human_review"]["required_for_policy_changes"])),
            "required_for_release_override": bool(human.get("required_for_release_override", defaults["human_review"]["required_for_release_override"])),
            "required_for_source_exclusion": bool(human.get("required_for_source_exclusion", defaults["human_review"]["required_for_source_exclusion"])),
            "allow_automatic_publication": False,
        },
        "boundaries": {
            "professional_advice": [str(item)[:80] for item in boundaries.get("professional_advice", defaults["boundaries"]["professional_advice"]) if str(item).strip()][:20],
            "diagnosis_or_certification": False,
            "autonomous_publishing": False,
            "unreviewed_ranking_changes": False,
        },
    }
    for key, default in defaults["quality_thresholds"].items():
        if key.endswith("_max"):
            clean["quality_thresholds"][key] = _bounded_float(thresholds.get(key), default)
        else:
            clean["quality_thresholds"][key] = _bounded_float(thresholds.get(key), default)
    clean["policy_fingerprint"] = fingerprint({k: v for k, v in clean.items() if k != "policy_fingerprint"})
    return clean


def source_governance(
    matches: list[RetrievedSource],
    records: list[KnowledgeRecord],
    reviews: dict[str, dict[str, Any]],
    policy: dict[str, Any],
) -> tuple[list[RetrievedSource], dict[str, Any]]:
    record_map = {record.id: record for record in records}
    controls = policy["source_controls"]
    now = datetime.now(timezone.utc)
    allowed: list[RetrievedSource] = []
    excluded: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    states = {"approved": 0, "review": 0, "excluded": 0, "unreviewed": 0}
    for match in matches:
        review = reviews.get(match.id, {})
        state = str(review.get("state") or "unreviewed")
        if state not in states:
            state = "unreviewed"
        states[state] += 1
        expires = str(review.get("expires_utc") or "")
        expired = False
        if expires:
            try:
                expired = datetime.fromisoformat(expires.replace("Z", "+00:00")) <= now
            except ValueError:
                expired = True
        if state == "excluded" and controls["exclude_rejected_sources"]:
            excluded.append({"record_id": match.id, "reason": "source-review-excluded"})
            continue
        if controls["require_approved_sources"] and (state != "approved" or (expired and controls["block_expired_reviews"])):
            excluded.append({"record_id": match.id, "reason": "source-not-currently-approved"})
            continue
        record = record_map.get(match.id)
        if controls["warn_on_stale_sources"] and record and record.modified_utc:
            try:
                modified = datetime.fromisoformat(record.modified_utc.replace("Z", "+00:00"))
                age_days = max(0, (now - modified).days)
                if age_days > int(controls["stale_after_days"]):
                    warnings.append({"record_id": match.id, "reason": "source-may-be-stale", "age_days": str(age_days)})
            except ValueError:
                warnings.append({"record_id": match.id, "reason": "source-date-invalid"})
        allowed.append(match)
    return allowed, {
        "schema": SOURCE_REVIEW_SCHEMA,
        "policy_profile": policy.get("profile", ""),
        "allowed": len(allowed),
        "excluded": excluded,
        "warnings": warnings,
        "states": states,
    }


def evaluate_answer_quality(
    *,
    citation_verification: dict[str, Any],
    evidence_gate: dict[str, Any],
    retrieval_diagnostics: dict[str, Any],
    matches: list[RetrievedSource],
    ai_used: bool,
) -> dict[str, Any]:
    citations_ok = bool(citation_verification.get("ok"))
    coverage = _bounded_float(citation_verification.get("coverage", 1.0 if citations_ok else 0.0), 0.0)
    gate_ok = bool(evidence_gate.get("ok"))
    source_strength = min(1.0, len(matches) / max(1, int(evidence_gate.get("minimum_source_count") or 2)))
    ambiguity = bool(retrieval_diagnostics.get("ambiguous"))
    invented_urls = len(citation_verification.get("invented_urls", []) or [])
    invalid_labels = len(citation_verification.get("invalid_labels", []) or [])
    unsupported = len(citation_verification.get("unsupported_claims", []) or [])
    integrity = 1.0 if not (invented_urls or invalid_labels or unsupported) else 0.0
    score = round(
        (0.35 * (1.0 if citations_ok else 0.0))
        + (0.20 * coverage)
        + (0.20 * (1.0 if gate_ok else 0.0))
        + (0.15 * source_strength)
        + (0.10 * integrity)
        - (0.10 if ambiguity else 0.0),
        4,
    )
    score = max(0.0, min(1.0, score))
    return {
        "schema": EVALUATION_SCHEMA,
        "quality_score": score,
        "citation_verified": citations_ok,
        "citation_coverage": coverage,
        "evidence_gate_passed": gate_ok,
        "source_count": len(matches),
        "ambiguous": ambiguity,
        "unsupported_claims": unsupported,
        "invented_urls": invented_urls,
        "invalid_citation_labels": invalid_labels,
        "generation_mode": "citation-verified-ai" if ai_used else "deterministic-evidence-fallback",
        "review_required": score < 0.80 or not citations_ok or not gate_ok,
    }


def build_answer_trace(
    *,
    query: str,
    answer: str,
    session_id: str,
    policy: dict[str, Any],
    model: str,
    provider: str,
    ai_used: bool,
    source: str,
    research_mode: str,
    matches: list[RetrievedSource],
    citation_verification: dict[str, Any],
    evidence_gate: dict[str, Any],
    retrieval_diagnostics: dict[str, Any],
    index_version: int,
    index_checksum: str,
    retrieval_profile: str,
) -> dict[str, Any]:
    retention = policy["retention"]
    quality = evaluate_answer_quality(
        citation_verification=citation_verification,
        evidence_gate=evidence_gate,
        retrieval_diagnostics=retrieval_diagnostics,
        matches=matches,
        ai_used=ai_used,
    )
    trace = {
        "schema": TRACE_SCHEMA,
        "trace_id": "trace-" + uuid.uuid4().hex,
        "created_utc": utc_now(),
        "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "session_reference": hashlib.sha256(session_id.encode("utf-8")).hexdigest() if retention["hash_session_ids"] else session_id,
        "research_mode": research_mode,
        "source": source,
        "provider": provider,
        "model": model,
        "prompt_version": "research-librarian-answer-v7.0.8",
        "index_version": int(index_version),
        "index_checksum": index_checksum,
        "retrieval_profile": retrieval_profile,
        "policy_profile": policy.get("profile", ""),
        "policy_fingerprint": policy.get("policy_fingerprint", ""),
        "source_record_ids": [item.id for item in matches],
        "evidence_labels": [item.citation_label for item in matches if item.citation_label],
        "citation_verification": citation_verification,
        "evidence_gate": evidence_gate,
        "retrieval_summary": {
            "intent": retrieval_diagnostics.get("intent", ""),
            "ambiguous": bool(retrieval_diagnostics.get("ambiguous")),
            "total_latency_ms": retrieval_diagnostics.get("total_latency_ms", 0),
            "semantic_coverage": retrieval_diagnostics.get("semantic_coverage", 0),
        },
        "quality": quality,
        "human_review": {"status": "pending" if quality["review_required"] else "not-required", "reviewer": "", "reviewed_utc": ""},
    }
    if retention["store_query_text"]:
        trace["query"] = query[:3000]
    if retention["store_answer_text"]:
        trace["answer"] = answer[:12000]
    trace["trace_fingerprint"] = fingerprint(trace)
    return trace


def evaluate_release_gate(metrics: dict[str, Any], policy: dict[str, Any], release_version: str, override: bool = False, reviewer: str = "") -> dict[str, Any]:
    thresholds = policy["quality_thresholds"]
    normalized = {
        "exact_title_accuracy": _bounded_float(metrics.get("exact_title_accuracy"), 0.0),
        "hit_at_3": _bounded_float(metrics.get("hit_at_3"), 0.0),
        "citation_precision": _bounded_float(metrics.get("citation_precision"), 0.0),
        "citation_completeness": _bounded_float(metrics.get("citation_completeness"), 0.0),
        "unsupported_claim_rate": _bounded_float(metrics.get("unsupported_claim_rate"), 1.0),
        "route_accuracy": _bounded_float(metrics.get("route_accuracy"), 0.0),
        "pdf_page_accuracy": _bounded_float(metrics.get("pdf_page_accuracy"), 0.0),
        "fallback_success": _bounded_float(metrics.get("fallback_success"), 0.0),
        "mean_answer_quality": _bounded_float(metrics.get("mean_answer_quality"), 0.0),
    }
    checks = {
        "exact_title_accuracy": normalized["exact_title_accuracy"] >= thresholds["exact_title_accuracy"],
        "hit_at_3": normalized["hit_at_3"] >= thresholds["hit_at_3"],
        "citation_precision": normalized["citation_precision"] >= thresholds["citation_precision"],
        "citation_completeness": normalized["citation_completeness"] >= thresholds["citation_completeness"],
        "unsupported_claim_rate": normalized["unsupported_claim_rate"] <= thresholds["unsupported_claim_rate_max"],
        "route_accuracy": normalized["route_accuracy"] >= thresholds["route_accuracy"],
        "pdf_page_accuracy": normalized["pdf_page_accuracy"] >= thresholds["pdf_page_accuracy"],
        "fallback_success": normalized["fallback_success"] >= thresholds["fallback_success"],
        "mean_answer_quality": normalized["mean_answer_quality"] >= thresholds["minimum_answer_quality"],
    }
    failures = [name for name, passed in checks.items() if not passed]
    critical = [name for name in failures if name in {"citation_precision", "citation_completeness", "unsupported_claim_rate"}]
    decision = "pass" if not failures else ("block" if critical else "review")
    override_applied = bool(override and reviewer and policy["human_review"]["required_for_release_override"])
    if override_applied:
        decision = "human-override"
    report = {
        "schema": RELEASE_GATE_SCHEMA,
        "gate_id": "gate-" + uuid.uuid4().hex,
        "created_utc": utc_now(),
        "release_version": str(release_version)[:80],
        "policy_profile": policy.get("profile", ""),
        "policy_fingerprint": policy.get("policy_fingerprint", ""),
        "metrics": normalized,
        "thresholds": thresholds,
        "checks": checks,
        "failures": failures,
        "critical_failures": critical,
        "decision": decision,
        "override": {"applied": override_applied, "reviewer": str(reviewer)[:160]},
        "automatic_publication_allowed": False,
    }
    report["gate_fingerprint"] = fingerprint(report)
    return report


def public_methodology(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": METHODOLOGY_SCHEMA,
        "title": "Research Librarian Methodology and Limitations",
        "version": "7.0.8",
        "principles": [
            "Retrieval occurs before generation.",
            "Exact titles and verified Sustainable Catalyst records have priority.",
            "Generated answers must cite supplied evidence identifiers.",
            "Deterministic evidence remains available when AI is unavailable or fails verification.",
            "Typed platform handoffs preserve evidence and require explicit user action.",
            "Ranking, source exclusions, release overrides, and publication remain under human control.",
        ],
        "evaluation": [
            "Exact-title accuracy and top-three retrieval relevance",
            "Citation precision and completeness",
            "Unsupported-claim and invented-link detection",
            "Route selection and PDF page-reference accuracy",
            "Fallback continuity and answer-quality scores",
        ],
        "limitations": [
            "The system is limited to synchronized Sustainable Catalyst records and configured platform tools.",
            "A citation indicates retrieved support; it does not make every interpretation uncontested.",
            "Older records may require freshness review.",
            "The system does not diagnose, certify, or replace medical, legal, financial, or other professional judgment.",
            "AI-generated synthesis remains reviewable and can be replaced by deterministic evidence output.",
        ],
        "human_control": policy["human_review"],
        "retention_summary": {
            "answer_trace_days": policy["retention"]["answer_trace_days"],
            "query_text_stored": policy["retention"]["store_query_text"],
            "answer_text_stored": policy["retention"]["store_answer_text"],
        },
        "policy_profile": policy.get("profile", ""),
        "generated_utc": utc_now(),
    }
