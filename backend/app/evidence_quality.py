from __future__ import annotations

"""Descriptive source evaluation and evidence-comparison contracts for v7.3.0.

The module intentionally does not compute a truth score, credibility score, or opaque
ranking. It exposes source metadata, missing metadata, provenance, methodology,
access, limitations, and corpus-level evidence gaps so a researcher can make the
judgment with the basis visible.
"""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from .models import utc_now

SOURCE_EVALUATION_SCHEMA = "sc-source-evaluation/1.0"
EVIDENCE_COMPARISON_SCHEMA = "sc-evidence-comparison/1.0"
EVIDENCE_GAP_SCHEMA = "sc-evidence-gap-report/1.0"
QUALITY_SIGNALS_SCHEMA = "sc-research-quality-signals/1.0"

EVIDENCE_LEVELS = {"primary", "secondary", "tertiary", "mixed", "unknown"}
ACCESS_STATES = {"open", "restricted", "subscription", "institutional", "local", "unknown"}
METHODOLOGY_STATES = {"available", "partial", "not-provided", "not-applicable", "unknown"}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, limit: int = 1000) -> str:
    return str(value or "").strip()[:limit]


def _first(*values: Any, limit: int = 1000) -> str:
    for value in values:
        clean = _text(value, limit)
        if clean:
            return clean
    return ""


def _list(value: Any, limit: int = 25, item_limit: int = 600) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        clean = _text(item, item_limit)
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
        if len(out) >= limit:
            break
    return out


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_level(value: Any) -> str:
    clean = _text(value, 40).lower().replace("_", "-")
    aliases = {
        "primary-source": "primary",
        "primary-research": "primary",
        "primary-data": "primary",
        "secondary-source": "secondary",
        "secondary-analysis": "secondary",
        "tertiary-source": "tertiary",
    }
    clean = aliases.get(clean, clean)
    return clean if clean in EVIDENCE_LEVELS else "unknown"


def _normalize_access(value: Any) -> str:
    clean = _text(value, 40).lower().replace("_", "-")
    aliases = {"public": "open", "open-access": "open", "paywalled": "subscription", "private": "restricted"}
    clean = aliases.get(clean, clean)
    return clean if clean in ACCESS_STATES else "unknown"


def _normalize_methodology(value: Any) -> str:
    if isinstance(value, bool):
        return "available" if value else "not-provided"
    clean = _text(value, 40).lower().replace("_", "-")
    aliases = {"yes": "available", "present": "available", "full": "available", "limited": "partial", "no": "not-provided", "none": "not-provided"}
    clean = aliases.get(clean, clean)
    return clean if clean in METHODOLOGY_STATES else "unknown"


def _publication_year(value: str) -> int | None:
    clean = _text(value, 80)
    if not clean:
        return None
    for token in clean.replace("/", "-").split("-"):
        if len(token) == 4 and token.isdigit():
            year = int(token)
            if 1500 <= year <= datetime.now(timezone.utc).year + 1:
                return year
    return None


def _signal(signal_id: str, label: str, state: str, detail: str, basis: str) -> dict[str, str]:
    return {"signal_id": signal_id, "label": label, "state": state, "detail": detail, "basis": basis}


def evaluate_source(source: dict[str, Any]) -> dict[str, Any]:
    payload = _dict(source.get("payload"))
    provenance = _dict(source.get("provenance"))
    metadata = _dict(payload.get("metadata"))
    citation = _dict(payload.get("citation"))
    methodology = _dict(payload.get("methodology"))

    publisher = _first(payload.get("publisher"), metadata.get("publisher"), provenance.get("provider"), limit=240)
    institution = _first(payload.get("institution"), metadata.get("institution"), payload.get("organization"), limit=240)
    publication_date = _first(payload.get("publication_date"), metadata.get("publication_date"), payload.get("date"), limit=80)
    source_type = _first(payload.get("source_type"), metadata.get("source_type"), source.get("object_type"), limit=100) or "unknown"
    evidence_level = _normalize_level(_first(payload.get("evidence_level"), metadata.get("evidence_level"), payload.get("source_level"), limit=80))

    methodology_state = _normalize_methodology(
        methodology.get("state") if methodology else payload.get("methodology_available")
    )
    if methodology and methodology_state == "unknown":
        methodology_state = "available" if any(_text(v) for v in methodology.values()) else "unknown"
    methodology_url = _first(methodology.get("url"), payload.get("methodology_url"), limit=1600)
    methodology_note = _first(methodology.get("description"), methodology.get("note"), payload.get("methodology_note"), limit=1200)

    citation_text = _first(citation.get("text"), payload.get("citation_text"), limit=2000)
    doi = _first(citation.get("doi"), payload.get("doi"), metadata.get("doi"), limit=240)
    isbn = _first(citation.get("isbn"), payload.get("isbn"), metadata.get("isbn"), limit=120)
    citation_available = bool(citation_text or doi or isbn)

    access_state = _normalize_access(_first(payload.get("access_state"), metadata.get("access_state"), payload.get("access"), limit=80))
    limitations = _list(payload.get("limitations") or metadata.get("limitations"), 20, 800)
    position = _first(payload.get("position"), payload.get("stance"), metadata.get("position"), limit=80).lower()

    canonical_url = _first(provenance.get("canonical_url"), payload.get("url"), limit=1600)
    source_record_id = _first(provenance.get("source_record_id"), payload.get("record_id"), limit=220)
    origin_system = _first(provenance.get("origin_system"), limit=120)
    provider = _first(provenance.get("provider"), limit=240)

    fields = {
        "publisher_or_institution": bool(publisher or institution),
        "publication_date": bool(publication_date),
        "evidence_level": evidence_level != "unknown",
        "methodology": methodology_state not in {"unknown", "not-provided"},
        "citation": citation_available,
        "access_state": access_state != "unknown",
        "provenance": bool(origin_system or provider or canonical_url or source_record_id),
        "limitations": bool(limitations),
    }
    present = sum(1 for value in fields.values() if value)
    metadata_state = "well-described" if present >= 7 else ("partially-described" if present >= 4 else "minimally-described")
    missing_fields = [key.replace("_", "-") for key, value in fields.items() if not value]

    signals = [
        _signal("evidence-level", "Evidence level", evidence_level, "Source role is explicitly described." if evidence_level != "unknown" else "Primary/secondary/tertiary role is not supplied.", "source metadata"),
        _signal("methodology", "Methodology", methodology_state, methodology_note or ("Methodology information is available." if methodology_state == "available" else "No usable methodology description is supplied."), "source metadata"),
        _signal("citation", "Citation metadata", "available" if citation_available else "not-provided", "Citation identifiers or formatted citation are present." if citation_available else "No DOI, ISBN, or citation text is supplied.", "source metadata"),
        _signal("access", "Access", access_state, "Access state reported by source metadata." if access_state != "unknown" else "Access state is not supplied.", "source metadata"),
        _signal("limitations", "Known limitations", "documented" if limitations else "not-provided", f"{len(limitations)} limitation note(s) recorded." if limitations else "No limitation notes are recorded.", "source metadata"),
        _signal("provenance", "Provenance", "available" if fields["provenance"] else "not-provided", "Origin/provider/record identifiers are preserved." if fields["provenance"] else "Origin metadata is incomplete.", "Library provenance"),
    ]

    result = {
        "schema": SOURCE_EVALUATION_SCHEMA,
        "object_id": _text(source.get("object_id"), 220),
        "title": _text(source.get("title") or "Untitled source", 500),
        "source_scope": _text(source.get("source_scope"), 80),
        "source_type": source_type,
        "evidence_level": evidence_level,
        "publisher": publisher,
        "institution": institution,
        "publication_date": publication_date,
        "publication_year": _publication_year(publication_date),
        "methodology": {"state": methodology_state, "url": methodology_url, "note": methodology_note},
        "citation": {"available": citation_available, "doi": doi, "isbn": isbn, "text": citation_text},
        "access_state": access_state,
        "provenance": {
            "origin_system": origin_system,
            "provider": provider,
            "canonical_url": canonical_url,
            "source_record_id": source_record_id,
        },
        "limitations": limitations,
        "position": position,
        "metadata_state": metadata_state,
        "missing_fields": missing_fields,
        "signals": signals,
        "governance": {
            "descriptive_only": True,
            "truth_score": None,
            "human_judgment_required": True,
            "metadata_not_independent_verification": True,
        },
    }
    result["fingerprint"] = _fingerprint(result)
    return result


def compare_sources(sources: list[dict[str, Any]], question: str = "") -> dict[str, Any]:
    evaluations = [evaluate_source(item) for item in sources[:100] if isinstance(item, dict)]
    dimensions = []
    for key, label in [
        ("source_type", "Source type"),
        ("evidence_level", "Evidence level"),
        ("publisher", "Publisher"),
        ("institution", "Institution"),
        ("publication_date", "Publication date"),
        ("access_state", "Access"),
        ("metadata_state", "Metadata state"),
    ]:
        values = [{"object_id": item["object_id"], "title": item["title"], "value": item.get(key) or "not-provided"} for item in evaluations]
        distinct = sorted({str(row["value"]) for row in values if str(row["value"])})
        dimensions.append({"dimension": key, "label": label, "values": values, "distinct_values": distinct, "varies": len(distinct) > 1})

    methodology_values = [
        {"object_id": item["object_id"], "title": item["title"], "value": item["methodology"]["state"]}
        for item in evaluations
    ]
    dimensions.append({"dimension": "methodology", "label": "Methodology", "values": methodology_values, "distinct_values": sorted({row["value"] for row in methodology_values}), "varies": len({row["value"] for row in methodology_values}) > 1})

    providers = [item["institution"] or item["publisher"] or item["provenance"]["provider"] for item in evaluations]
    providers = [item for item in providers if item]
    positions = [item["position"] for item in evaluations if item.get("position")]
    result = {
        "schema": EVIDENCE_COMPARISON_SCHEMA,
        "question": _text(question, 3000),
        "source_count": len(evaluations),
        "sources": evaluations,
        "dimensions": dimensions,
        "corpus": {
            "evidence_levels": dict(Counter(item["evidence_level"] for item in evaluations)),
            "methodology_states": dict(Counter(item["methodology"]["state"] for item in evaluations)),
            "access_states": dict(Counter(item["access_state"] for item in evaluations)),
            "source_scopes": dict(Counter(item["source_scope"] or "unknown" for item in evaluations)),
            "independent_provider_count": len(set(providers)),
            "positions": dict(Counter(positions)),
        },
        "governance": {
            "descriptive_comparison": True,
            "no_automatic_winner": True,
            "no_truth_score": True,
            "human_interpretation_required": True,
        },
        "generated_utc": utc_now(),
    }
    result["fingerprint"] = _fingerprint({k: v for k, v in result.items() if k != "generated_utc"})
    return result


def evidence_gaps(sources: list[dict[str, Any]], question: str = "") -> dict[str, Any]:
    evaluations = [evaluate_source(item) for item in sources[:200] if isinstance(item, dict)]
    gaps: list[dict[str, Any]] = []

    def add(gap_id: str, severity: str, category: str, statement: str, action: str, basis: str) -> None:
        gaps.append({"gap_id": gap_id, "severity": severity, "category": category, "statement": statement, "suggested_action": action, "basis": basis})

    if not evaluations:
        add("no-sources", "high", "coverage", "No sources are present in the selected research context.", "Add attributable sources before synthesis or comparison.", "0 evaluated sources")
    else:
        primary = [item for item in evaluations if item["evidence_level"] == "primary"]
        if not primary:
            add("no-primary-evidence", "medium", "source-mix", "No source is explicitly identified as primary evidence.", "Look for original datasets, official records, first-party documents, or primary research where appropriate.", "evidence_level metadata")
        providers = {item["institution"] or item["publisher"] or item["provenance"]["provider"] for item in evaluations}
        providers.discard("")
        if len(evaluations) >= 2 and len(providers) < 2:
            add("provider-concentration", "medium", "independence", "The source set does not show at least two distinct publishers or institutions.", "Add an independent source or record the reason a single-provider corpus is appropriate.", f"{len(providers)} distinct provider/institution labels")
        methodology_visible = [item for item in evaluations if item["methodology"]["state"] in {"available", "partial", "not-applicable"}]
        if not methodology_visible:
            add("methodology-visibility", "medium", "methodology", "Methodology is not visible for any evaluated source.", "Add a source with methods documentation or record why methodology is not applicable.", "methodology metadata")
        dated = [item for item in evaluations if item["publication_date"]]
        if not dated:
            add("undated-corpus", "medium", "temporal", "No evaluated source includes a publication date.", "Add dates or verify temporal relevance before making time-sensitive claims.", "publication_date metadata")
        citations = [item for item in evaluations if item["citation"]["available"]]
        if not citations:
            add("citation-metadata", "low", "citation", "No evaluated source includes DOI, ISBN, or formatted citation metadata.", "Capture citation metadata before export or formal research use.", "citation metadata")
        limitations = [item for item in evaluations if item["limitations"]]
        if not limitations:
            add("limitations-undocumented", "low", "limitations", "Known limitations are not documented for the current source set.", "Record source-specific limitations, uncertainty, exclusions, or data-quality caveats.", "limitations metadata")
        if len(evaluations) >= 2:
            positions = {item["position"] for item in evaluations if item.get("position")}
            q = _text(question, 3000).lower()
            comparison_intent = any(term in q for term in ["compare", "conflict", "contradict", "opposing", "alternative", "different", "versus", " vs "])
            if comparison_intent and len(positions) < 2:
                add("contrast-coverage", "medium", "perspective", "The source metadata does not establish contrasting positions for a comparison-oriented question.", "Add an opposing or materially different source, or explicitly record that the available evidence is one-sided.", "position/stance metadata")

    severity_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda row: (severity_order.get(row["severity"], 9), row["gap_id"]))
    result = {
        "schema": EVIDENCE_GAP_SCHEMA,
        "question": _text(question, 3000),
        "source_count": len(evaluations),
        "gap_count": len(gaps),
        "gaps": gaps,
        "status": "needs-evidence" if any(row["severity"] == "high" for row in gaps) else ("review-gaps" if gaps else "no-structural-gaps-detected"),
        "governance": {
            "structural_gap_detection_only": True,
            "absence_of_gap_is_not_proof": True,
            "human_review_required": True,
        },
        "generated_utc": utc_now(),
    }
    result["fingerprint"] = _fingerprint({k: v for k, v in result.items() if k != "generated_utc"})
    return result


def quality_summary(sources: list[dict[str, Any]], question: str = "") -> dict[str, Any]:
    comparison = compare_sources(sources, question)
    gaps = evidence_gaps(sources, question)
    summary = {
        "schema": QUALITY_SIGNALS_SCHEMA,
        "source_count": comparison["source_count"],
        "corpus": comparison["corpus"],
        "gap_count": gaps["gap_count"],
        "gap_status": gaps["status"],
        "gaps": gaps["gaps"][:12],
        "governance": {
            "descriptive_signals_only": True,
            "no_truth_score": True,
            "no_automatic_source_rejection": True,
            "human_judgment_required": True,
        },
    }
    summary["fingerprint"] = _fingerprint(summary)
    return summary


def compact_source_quality(source: dict[str, Any]) -> dict[str, Any]:
    """Return bounded descriptive metadata safe to carry with an authorized prompt context."""
    item = evaluate_source(source)
    return {
        "source_type": item["source_type"][:100],
        "evidence_level": item["evidence_level"],
        "publisher": item["publisher"][:240],
        "institution": item["institution"][:240],
        "publication_date": item["publication_date"][:80],
        "methodology_state": item["methodology"]["state"],
        "citation_available": bool(item["citation"]["available"]),
        "access_state": item["access_state"],
        "limitations_count": len(item["limitations"]),
        "metadata_state": item["metadata_state"],
        "quality_note": "Descriptive source metadata only; not a truth or credibility score.",
    }
