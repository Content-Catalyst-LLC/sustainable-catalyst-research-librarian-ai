from __future__ import annotations

"""Research Librarian v8.4 advanced retrieval orchestration.

This module deliberately keeps retrieval relevance separate from Platform Core
research/evidence governance. It plans deterministic query variants, applies
metadata filters, fuses independent retrieval runs, reranks candidates using
transparent lexical/semantic features, removes duplicates, and applies a
maximum-marginal-relevance style diversity pass.
"""

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import math
import re
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .calibration import sanitize_retrieval_config
from .models import KnowledgeChunk, KnowledgeRecord, RetrievedSource
from .retrieval import classify_intent, normalize, retrieve_with_diagnostics, tokens

ADVANCED_RETRIEVAL_SCHEMA = "sc-research-librarian-advanced-retrieval/1.0"
QUERY_PLAN_SCHEMA = "sc-research-librarian-query-plan/1.0"

_COMPARISON_SPLIT = re.compile(r"\s+(?:vs\.?|versus|compared\s+(?:to|with)|against)\s+", re.IGNORECASE)
_CLAUSE_SPLIT = re.compile(r"\s*(?:;|\||\n+)\s*")
_QUOTED = re.compile(r"[\"“”']([^\"“”']{3,160})[\"“”']")


def _unique(values: list[str], limit: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = " ".join(str(value or "").split()).strip()
        key = normalize(clean)
        if clean and key and key not in seen:
            output.append(clean)
            seen.add(key)
        if len(output) >= limit:
            break
    return output


def build_query_plan(query: str, max_queries: int = 4) -> dict[str, Any]:
    """Create deterministic, non-generative query variants.

    Variants are derived only from user-supplied text. This avoids hidden query
    expansion that could introduce concepts not present in the research request.
    """
    query = " ".join((query or "").split()).strip()
    max_queries = max(1, min(8, int(max_queries or 1)))
    intent = classify_intent(query)
    variants: list[dict[str, Any]] = [{"query": query, "kind": "original", "weight": 1.0}]

    quoted = _unique(_QUOTED.findall(query), 3)
    for value in quoted:
        variants.append({"query": value, "kind": "quoted-phrase", "weight": 0.90})

    comparison_parts = _unique(_COMPARISON_SPLIT.split(query), 4)
    if len(comparison_parts) > 1:
        for value in comparison_parts:
            variants.append({"query": value, "kind": "comparison-component", "weight": 0.78})

    clause_parts: list[str] = []
    for part in _CLAUSE_SPLIT.split(query):
        clean = " ".join(part.split()).strip(" ,")
        if clean and clean != query and len(tokens(clean)) >= 2:
            clause_parts.append(clean)
    for value in _unique(clause_parts, 3):
        variants.append({"query": value, "kind": "clause", "weight": 0.72})

    keyword_tokens: list[str] = []
    for token in tokens(query):
        if token not in keyword_tokens:
            keyword_tokens.append(token)
    if 2 <= len(keyword_tokens) <= 16:
        keyword_query = " ".join(keyword_tokens)
        if normalize(keyword_query) != normalize(query):
            variants.append({"query": keyword_query, "kind": "keyword", "weight": 0.82})

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for variant in variants:
        key = normalize(variant["query"])
        if key and key not in seen:
            deduped.append(variant)
            seen.add(key)
        if len(deduped) >= max_queries:
            break

    return {
        "schema": QUERY_PLAN_SCHEMA,
        "query": query,
        "intent": intent,
        "strategy": "deterministic-user-text-decomposition",
        "generative_expansion": False,
        "variants": deduped,
        "variant_count": len(deduped),
    }


def _parse_utc(value: str) -> datetime | None:
    clean = str(value or "").strip()
    if not clean:
        return None
    try:
        parsed = datetime.fromisoformat(clean.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _lower_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def apply_retrieval_filters(
    records: list[KnowledgeRecord], filters: dict[str, Any] | None
) -> tuple[list[KnowledgeRecord], dict[str, Any]]:
    raw = filters if isinstance(filters, dict) else {}
    post_types = _lower_set(raw.get("post_types"))
    sources = _lower_set(raw.get("sources"))
    series = _lower_set(raw.get("series"))
    record_ids = {str(item).strip() for item in (raw.get("record_ids") or []) if str(item).strip()}
    url_prefixes = [str(item).strip() for item in (raw.get("url_prefixes") or []) if str(item).strip()]
    taxonomy_filters = raw.get("taxonomies") if isinstance(raw.get("taxonomies"), dict) else {}
    taxonomy_filters = {str(k).strip().lower(): _lower_set(v) for k, v in taxonomy_filters.items() if str(k).strip()}
    modified_from = _parse_utc(str(raw.get("modified_from_utc") or ""))
    modified_to = _parse_utc(str(raw.get("modified_to_utc") or ""))

    reasons: dict[str, int] = defaultdict(int)
    selected: list[KnowledgeRecord] = []
    for record in records:
        reason = ""
        if post_types and record.post_type.lower() not in post_types:
            reason = "post-type-filter"
        elif sources and record.source.lower() not in sources:
            reason = "source-filter"
        elif series and record.series.lower() not in series:
            reason = "series-filter"
        elif record_ids and record.id not in record_ids:
            reason = "record-id-filter"
        elif url_prefixes and not any(record.url.startswith(prefix) for prefix in url_prefixes):
            reason = "url-prefix-filter"
        elif taxonomy_filters:
            taxonomies = {str(k).lower(): {str(x).strip().lower() for x in v} for k, v in record.taxonomies.items()}
            for taxonomy, required in taxonomy_filters.items():
                if required and not (taxonomies.get(taxonomy, set()) & required):
                    reason = f"taxonomy-filter:{taxonomy}"
                    break
        if not reason and (modified_from or modified_to):
            modified = _parse_utc(record.modified_utc)
            if modified is None:
                reason = "modified-date-missing"
            elif modified_from and modified < modified_from:
                reason = "modified-before-range"
            elif modified_to and modified > modified_to:
                reason = "modified-after-range"
        if reason:
            reasons[reason] += 1
        else:
            selected.append(record)

    active = bool(post_types or sources or series or record_ids or url_prefixes or taxonomy_filters or modified_from or modified_to)
    return selected, {
        "active": active,
        "records_before": len(records),
        "records_after": len(selected),
        "records_removed": len(records) - len(selected),
        "removal_reasons": dict(reasons),
    }


def _canonical_url(value: str) -> str:
    try:
        parts = urlsplit(value or "")
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))
    except Exception:
        return str(value or "").strip().lower().rstrip("/")


def _jaccard_text(left: str, right: str) -> float:
    a = set(tokens(left))
    b = set(tokens(right))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _record_signature(record: KnowledgeRecord) -> tuple[str, str, str]:
    return (
        _canonical_url(record.url),
        str(record.content_hash or "").strip().lower(),
        normalize(record.title),
    )


def _deduplicate(
    ranked: list[RetrievedSource],
    records_by_id: dict[str, KnowledgeRecord],
    title_threshold: float,
    passage_threshold: float,
) -> tuple[list[RetrievedSource], list[dict[str, Any]]]:
    kept: list[RetrievedSource] = []
    removed: list[dict[str, Any]] = []
    signatures: list[tuple[str, str, str]] = []
    for candidate in ranked:
        record = records_by_id.get(candidate.id)
        signature = _record_signature(record) if record else (_canonical_url(candidate.url), "", normalize(candidate.title))
        duplicate_of = ""
        duplicate_reason = ""
        for index, existing in enumerate(kept):
            existing_record = records_by_id.get(existing.id)
            existing_sig = signatures[index]
            if signature[0] and signature[0] == existing_sig[0]:
                duplicate_of, duplicate_reason = existing.id, "canonical-url"
                break
            if signature[1] and signature[1] == existing_sig[1]:
                duplicate_of, duplicate_reason = existing.id, "content-hash"
                break
            title_similarity = _jaccard_text(candidate.title, existing.title)
            passage_similarity = _jaccard_text(candidate.passage or candidate.summary, existing.passage or existing.summary)
            if title_similarity >= title_threshold and passage_similarity >= passage_threshold:
                duplicate_of, duplicate_reason = existing.id, "near-duplicate-content"
                break
        if duplicate_of:
            removed.append({"id": candidate.id, "duplicate_of": duplicate_of, "reason": duplicate_reason})
            continue
        kept.append(candidate)
        signatures.append(signature)
    return kept, removed


def _rerank_score(query: str, source: RetrievedSource, hit_count: int, advanced: dict[str, Any]) -> tuple[float, dict[str, float]]:
    q_tokens = set(tokens(query))
    title_tokens = set(tokens(source.title))
    body_tokens = set(tokens(" ".join([source.title, source.summary, source.section, source.passage])))
    coverage = len(q_tokens & body_tokens) / max(1, len(q_tokens))
    title_coverage = len(q_tokens & title_tokens) / max(1, len(q_tokens))
    normalized_query = normalize(query)
    normalized_text = normalize(" ".join([source.title, source.section, source.passage]))
    phrase_match = 1.0 if normalized_query and normalized_query in normalized_text else 0.0
    lexical_semantic = math.log1p(max(0.0, source.lexical_score)) * 4.0 + max(0.0, source.semantic_score) * 12.0
    components = {
        "advanced_query_coverage": coverage * float(advanced["rerank_coverage_weight"]),
        "advanced_title_coverage": title_coverage * float(advanced["rerank_title_weight"]),
        "advanced_phrase_bonus": phrase_match * float(advanced["rerank_phrase_bonus"]),
        "advanced_multi_query_hits": max(0, hit_count - 1) * float(advanced["rerank_multi_query_hit_bonus"]),
        "advanced_lexical_semantic_support": lexical_semantic,
    }
    return sum(components.values()), {key: round(value, 5) for key, value in components.items() if value > 0}


def _diverse_select(ranked: list[RetrievedSource], limit: int, diversity_lambda: float) -> tuple[list[RetrievedSource], list[dict[str, Any]]]:
    if limit <= 0 or not ranked:
        return [], []
    if len(ranked) <= limit:
        return ranked, []
    diversity_lambda = max(0.50, min(1.0, float(diversity_lambda)))
    selected: list[RetrievedSource] = [ranked[0]]
    remaining = ranked[1:]
    decisions: list[dict[str, Any]] = []
    max_score = max(1.0, ranked[0].score)
    while remaining and len(selected) < limit:
        best_index = 0
        best_value = -10.0
        best_similarity = 0.0
        for index, candidate in enumerate(remaining):
            relevance = max(0.0, candidate.score) / max_score
            similarity = max(
                _jaccard_text(
                    " ".join([candidate.title, candidate.summary, candidate.passage]),
                    " ".join([chosen.title, chosen.summary, chosen.passage]),
                )
                for chosen in selected
            )
            value = diversity_lambda * relevance - (1.0 - diversity_lambda) * similarity
            if value > best_value:
                best_index, best_value, best_similarity = index, value, similarity
        chosen = remaining.pop(best_index)
        chosen.retrieval_reasons = list(dict.fromkeys([*chosen.retrieval_reasons, "diversity-selected"]))
        selected.append(chosen)
        decisions.append({
            "id": chosen.id,
            "mmr": round(best_value, 6),
            "max_similarity_to_selected": round(best_similarity, 5),
        })
    return selected, decisions


def advanced_retrieve_with_diagnostics(
    query: str,
    records: list[KnowledgeRecord],
    chunks: list[KnowledgeChunk] | None = None,
    limit: int = 10,
    query_embedding: list[float] | None = None,
    calibration: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
    *,
    advanced_enabled: bool = True,
    max_queries_override: int | None = None,
    candidate_pool_override: int | None = None,
) -> tuple[list[RetrievedSource], dict[str, Any]]:
    started = time.perf_counter()
    config = sanitize_retrieval_config(calibration)
    advanced = config["advanced"]
    if not advanced_enabled or not bool(advanced["enabled"]):
        return retrieve_with_diagnostics(query, records, chunks or [], limit, query_embedding, config)

    filtered_records, filter_diagnostics = apply_retrieval_filters(records, filters)
    allowed_ids = {item.id for item in filtered_records}
    filtered_chunks = [chunk for chunk in (chunks or []) if chunk.record_id in allowed_ids]
    records_by_id = {record.id: record for record in filtered_records}

    max_queries = max_queries_override or int(advanced["max_queries"])
    candidate_pool = candidate_pool_override or int(advanced["candidate_pool"])
    candidate_pool = max(limit, min(25, candidate_pool))
    plan = build_query_plan(query, max_queries if bool(advanced["multi_query"]) else 1)

    candidate_config = deepcopy(config)
    candidate_config["limits"]["max_sources"] = max(candidate_pool, min(25, int(config["limits"]["max_sources"])))
    aggregate: dict[str, dict[str, Any]] = {}
    query_runs: list[dict[str, Any]] = []
    fusion_k = max(1, int(advanced["query_fusion_k"]))

    for variant_index, variant in enumerate(plan["variants"]):
        variant_query = str(variant["query"])
        embedding = query_embedding if variant_index == 0 else None
        matches, diagnostics = retrieve_with_diagnostics(
            variant_query,
            filtered_records,
            filtered_chunks,
            candidate_pool,
            embedding,
            candidate_config,
        )
        query_runs.append({
            "query": variant_query,
            "kind": variant["kind"],
            "weight": variant["weight"],
            "result_count": len(matches),
            "semantic_used": bool(diagnostics.get("semantic_used")),
            "latency_ms": diagnostics.get("retrieval_latency_ms", 0.0),
        })
        for rank, source in enumerate(matches, start=1):
            state = aggregate.setdefault(source.id, {"source": source.model_copy(deep=True), "fusion": 0.0, "hits": 0, "best_rank": rank})
            state["fusion"] += float(variant["weight"]) * (1.0 / (fusion_k + rank))
            state["hits"] += 1
            state["best_rank"] = min(int(state["best_rank"]), rank)
            if source.exact_title_match or source.score > state["source"].score:
                state["source"] = source.model_copy(deep=True)

    reranked: list[RetrievedSource] = []
    for state in aggregate.values():
        source: RetrievedSource = state["source"]
        query_fusion = float(state["fusion"]) * float(advanced["query_fusion_weight"])
        rerank_bonus, components = _rerank_score(query, source, int(state["hits"]), advanced)
        source.score = round(source.score + query_fusion + (rerank_bonus if bool(advanced["rerank"]) else 0.0), 5)
        source.fusion_score = round(source.fusion_score + query_fusion, 5)
        source.score_breakdown = {
            **source.score_breakdown,
            "advanced_query_fusion": round(query_fusion, 5),
            **(components if bool(advanced["rerank"]) else {}),
            "advanced_query_hits": float(state["hits"]),
            "advanced_best_variant_rank": float(state["best_rank"]),
        }
        if int(state["hits"]) > 1:
            source.retrieval_reasons = list(dict.fromkeys([*source.retrieval_reasons, "multi-query-consensus"]))
        if bool(advanced["rerank"]):
            source.retrieval_reasons = list(dict.fromkeys([*source.retrieval_reasons, "transparent-rerank"]))
        reranked.append(source)

    reranked.sort(
        key=lambda item: (
            item.exact_title_match,
            item.score,
            item.semantic_score,
            item.lexical_score,
            -len(item.title),
        ),
        reverse=True,
    )

    deduped, duplicate_removals = _deduplicate(
        reranked,
        records_by_id,
        float(advanced["duplicate_title_similarity"]),
        float(advanced["duplicate_passage_similarity"]),
    )
    bounded_limit = min(limit, int(config["limits"]["max_sources"]))
    if bool(advanced["diversity"]):
        selected, diversity_decisions = _diverse_select(deduped, bounded_limit, float(advanced["diversity_lambda"]))
    else:
        selected, diversity_decisions = deduped[:bounded_limit], []

    for index, item in enumerate(selected, start=1):
        item.evidence_id = f"SC{index}"
        item.citation_label = f"[SC{index}]"

    total_ms = (time.perf_counter() - started) * 1000
    diagnostics = {
        "schema": ADVANCED_RETRIEVAL_SCHEMA,
        "retrieval_mode": "exact-title+bm25+semantic+rrf+multi-query+rerank+dedupe+diversity",
        "advanced_enabled": True,
        "query_plan": plan,
        "filters": filter_diagnostics,
        "candidate_pool_limit": candidate_pool,
        "candidate_count": len(aggregate),
        "deduplicated_candidate_count": len(deduped),
        "duplicates_removed": duplicate_removals,
        "duplicate_count": len(duplicate_removals),
        "rerank_enabled": bool(advanced["rerank"]),
        "diversity_enabled": bool(advanced["diversity"]),
        "diversity_lambda": float(advanced["diversity_lambda"]),
        "diversity_decisions": diversity_decisions,
        "multi_query_enabled": bool(advanced["multi_query"]),
        "query_runs": query_runs,
        "semantic_used": bool(query_embedding),
        "query_embedding_dimensions": len(query_embedding or []),
        "result_count": len(selected),
        "exact_title_match": bool(selected and selected[0].exact_title_match),
        "intent": plan["intent"],
        "retrieval_profile": config["profile"],
        "advanced": advanced,
        "retrieval_latency_ms": round(total_ms, 3),
    }
    return selected, diagnostics
