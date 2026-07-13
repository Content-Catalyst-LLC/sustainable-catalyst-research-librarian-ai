from __future__ import annotations

from copy import deepcopy
import re
from typing import Any


DEFAULT_RETRIEVAL_CONFIG: dict[str, Any] = {
    "profile": "balanced-v6.4.1",
    "weights": {
        "structural": 1.0,
        "lexical": 24.0,
        "semantic": 160.0,
        "rrf": 1400.0,
    },
    "rrf_k": 60,
    "thresholds": {
        "minimum_score": 8.0,
        "minimum_sources": 1,
        "minimum_best_lexical": 0.0,
        "minimum_best_semantic": 0.0,
        "ambiguity_margin": 40.0,
        "near_duplicate_title_similarity": 0.60,
        "unsupported_overlap": 0.06,
        "minimum_citation_coverage": 0.80,
    },
    "limits": {
        "max_sources": 10,
        "max_context_characters": 18000,
        "max_passage_characters": 1800,
        "benchmark_cases": 25,
    },
    "post_type_weights": {
        "article": 1.08,
        "post": 1.05,
        "page": 1.00,
        "document": 1.04,
        "pdf": 1.04,
    },
    "source_weights": {
        "wordpress": 1.0,
    },
    "exclusions": {
        "record_ids": [],
        "post_types": [],
        "sources": [],
        "url_prefixes": [],
    },
}


def _number(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _integer(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _strings(value: Any, maximum: int = 250) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[\r\n,]+", value)
    if not isinstance(value, list):
        return []
    output: list[str] = []
    for item in value:
        clean = str(item or "").strip()
        if clean and clean not in output:
            output.append(clean[:1000])
        if len(output) >= maximum:
            break
    return output


def _weight_map(value: Any, defaults: dict[str, float]) -> dict[str, float]:
    source = value if isinstance(value, dict) else {}
    output = dict(defaults)
    for key, raw in source.items():
        clean_key = re.sub(r"[^a-z0-9_.:-]", "", str(key).strip().lower())[:100]
        if clean_key:
            output[clean_key] = _number(raw, 1.0, 0.0, 5.0)
    return output


def sanitize_retrieval_config(value: Any) -> dict[str, Any]:
    incoming = value if isinstance(value, dict) else {}
    defaults = deepcopy(DEFAULT_RETRIEVAL_CONFIG)
    raw_weights = incoming.get("weights") if isinstance(incoming.get("weights"), dict) else {}
    raw_thresholds = incoming.get("thresholds") if isinstance(incoming.get("thresholds"), dict) else {}
    raw_limits = incoming.get("limits") if isinstance(incoming.get("limits"), dict) else {}
    raw_exclusions = incoming.get("exclusions") if isinstance(incoming.get("exclusions"), dict) else {}

    config = {
        "profile": re.sub(r"[^a-zA-Z0-9_.:-]", "", str(incoming.get("profile") or defaults["profile"]))[:100] or defaults["profile"],
        "weights": {
            "structural": _number(raw_weights.get("structural"), defaults["weights"]["structural"], 0.0, 10.0),
            "lexical": _number(raw_weights.get("lexical"), defaults["weights"]["lexical"], 0.0, 500.0),
            "semantic": _number(raw_weights.get("semantic"), defaults["weights"]["semantic"], 0.0, 500.0),
            "rrf": _number(raw_weights.get("rrf"), defaults["weights"]["rrf"], 0.0, 5000.0),
        },
        "rrf_k": _integer(incoming.get("rrf_k"), defaults["rrf_k"], 1, 500),
        "thresholds": {
            "minimum_score": _number(raw_thresholds.get("minimum_score"), defaults["thresholds"]["minimum_score"], 0.0, 5000.0),
            "minimum_sources": _integer(raw_thresholds.get("minimum_sources"), defaults["thresholds"]["minimum_sources"], 1, 10),
            "minimum_best_lexical": _number(raw_thresholds.get("minimum_best_lexical"), defaults["thresholds"]["minimum_best_lexical"], 0.0, 100.0),
            "minimum_best_semantic": _number(raw_thresholds.get("minimum_best_semantic"), defaults["thresholds"]["minimum_best_semantic"], 0.0, 1.0),
            "ambiguity_margin": _number(raw_thresholds.get("ambiguity_margin"), defaults["thresholds"]["ambiguity_margin"], 0.0, 1000.0),
            "near_duplicate_title_similarity": _number(raw_thresholds.get("near_duplicate_title_similarity"), defaults["thresholds"]["near_duplicate_title_similarity"], 0.0, 1.0),
            "unsupported_overlap": _number(raw_thresholds.get("unsupported_overlap"), defaults["thresholds"]["unsupported_overlap"], 0.0, 1.0),
            "minimum_citation_coverage": _number(raw_thresholds.get("minimum_citation_coverage"), defaults["thresholds"]["minimum_citation_coverage"], 0.0, 1.0),
        },
        "limits": {
            "max_sources": _integer(raw_limits.get("max_sources"), defaults["limits"]["max_sources"], 1, 25),
            "max_context_characters": _integer(raw_limits.get("max_context_characters"), defaults["limits"]["max_context_characters"], 2000, 60000),
            "max_passage_characters": _integer(raw_limits.get("max_passage_characters"), defaults["limits"]["max_passage_characters"], 300, 5000),
            "benchmark_cases": _integer(raw_limits.get("benchmark_cases"), defaults["limits"]["benchmark_cases"], 1, 100),
        },
        "post_type_weights": _weight_map(incoming.get("post_type_weights"), defaults["post_type_weights"]),
        "source_weights": _weight_map(incoming.get("source_weights"), defaults["source_weights"]),
        "exclusions": {
            "record_ids": _strings(raw_exclusions.get("record_ids")),
            "post_types": [item.lower() for item in _strings(raw_exclusions.get("post_types"), 100)],
            "sources": [item.lower() for item in _strings(raw_exclusions.get("sources"), 100)],
            "url_prefixes": _strings(raw_exclusions.get("url_prefixes"), 100),
        },
    }
    return config


def record_is_excluded(record: Any, config: dict[str, Any]) -> tuple[bool, str]:
    exclusions = config.get("exclusions", {})
    record_id = str(getattr(record, "id", ""))
    post_type = str(getattr(record, "post_type", "")).lower()
    source = str(getattr(record, "source", "")).lower()
    url = str(getattr(record, "url", ""))
    if record_id in set(exclusions.get("record_ids", [])):
        return True, "record-id"
    if post_type and post_type in set(exclusions.get("post_types", [])):
        return True, "post-type"
    if source and source in set(exclusions.get("sources", [])):
        return True, "source"
    for prefix in exclusions.get("url_prefixes", []):
        if prefix and url.startswith(prefix):
            return True, "url-prefix"
    return False, ""


def evidence_gate(matches: list[Any], diagnostics: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    thresholds = config.get("thresholds", {})
    minimum_sources = int(thresholds.get("minimum_sources", 1))
    minimum_score = float(thresholds.get("minimum_score", 0.0))
    minimum_lexical = float(thresholds.get("minimum_best_lexical", 0.0))
    minimum_semantic = float(thresholds.get("minimum_best_semantic", 0.0))
    best = matches[0] if matches else None
    reasons: list[str] = []
    if len(matches) < minimum_sources:
        reasons.append("insufficient-source-count")
    if best is None:
        reasons.append("no-source-match")
    elif not bool(getattr(best, "exact_title_match", False)):
        if float(getattr(best, "score", 0.0)) < minimum_score:
            reasons.append("best-score-below-threshold")
        if minimum_lexical > 0 and float(getattr(best, "lexical_score", 0.0)) < minimum_lexical:
            reasons.append("lexical-support-below-threshold")
        if minimum_semantic > 0 and float(getattr(best, "semantic_score", 0.0)) < minimum_semantic:
            reasons.append("semantic-support-below-threshold")
    if diagnostics.get("ambiguous"):
        reasons.append("near-duplicate-title-ambiguity")
    return {
        "ok": not reasons,
        "reasons": reasons,
        "minimum_sources": minimum_sources,
        "source_count": len(matches),
        "minimum_score": minimum_score,
        "best_score": round(float(getattr(best, "score", 0.0)), 4) if best else 0.0,
        "ambiguous": bool(diagnostics.get("ambiguous")),
        "ambiguity_candidates": diagnostics.get("ambiguity_candidates", []),
    }
