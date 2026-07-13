from __future__ import annotations

from collections import Counter, defaultdict
import math
import re
import unicodedata
from urllib.parse import unquote
from typing import Any

from .models import EvidenceCitation, KnowledgeChunk, KnowledgeRecord, RetrievedSource


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "in", "is", "it", "me",
    "my", "of", "on", "or", "our", "should", "that", "the", "this", "to", "use", "what", "when", "where",
    "which", "with", "would", "you", "your", "about", "find", "show", "help", "need", "want", "looking",
}


def normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = unquote(normalized).lower().replace("&", " and ")
    return " ".join(TOKEN_RE.findall(normalized))


def tokens(value: str) -> list[str]:
    return [token for token in normalize(value).split() if len(token) > 1 and token not in STOPWORDS]


def classify_intent(query: str) -> str:
    normalized = normalize(query)
    term_set = set(tokens(query))
    if any(value in normalized for value in ("exact title", "article called", "page called", "title named")):
        return "exact-title-lookup"
    if term_set & {"pdf", "document", "page", "citation", "cite", "passage"}:
        return "document-evidence"
    if term_set & {"country", "countries", "indicator", "map", "geospatial", "climate", "disaster"}:
        return "country-or-indicator-research"
    if term_set & {"calculate", "equation", "formula", "model", "simulate", "graph", "statistics"}:
        return "calculation-or-modeling"
    if term_set & {"decision", "tradeoff", "scenario", "recommendation", "brief"}:
        return "decision-support"
    if term_set & {"compare", "comparison", "difference", "versus", "relationship"}:
        return "comparative-research"
    return "subject-exploration"


def _overlap(query_tokens: set[str], value: str) -> float:
    candidate = set(tokens(value))
    if not query_tokens or not candidate:
        return 0.0
    return len(query_tokens & candidate) / max(1, len(query_tokens))


def _taxonomy_text(record: KnowledgeRecord) -> str:
    values: list[str] = []
    for terms in record.taxonomies.values():
        values.extend(terms)
    return " ".join(values)


def _field_term_score(query_counts: Counter[str], value: str, weight: float) -> float:
    candidate_counts = Counter(tokens(value))
    if not candidate_counts:
        return 0.0
    score = 0.0
    for token, count in query_counts.items():
        if token in candidate_counts:
            score += weight * min(count, candidate_counts[token])
    return score


def score_record(query: str, record: KnowledgeRecord) -> tuple[float, dict[str, float], str, bool]:
    q_norm = normalize(query)
    title_norm = normalize(record.title)
    slug_norm = normalize(record.slug.replace("-", " "))
    query_tokens = tokens(query)
    q_set = set(query_tokens)
    query_counts = Counter(query_tokens)
    breakdown: dict[str, float] = {}
    exact_title = bool(q_norm and q_norm == title_norm)

    if exact_title:
        breakdown["exact_title"] = 1000.0
    elif title_norm and title_norm in q_norm:
        breakdown["title_phrase_in_query"] = 420.0
    elif q_norm and q_norm in title_norm:
        breakdown["query_phrase_in_title"] = 360.0

    if slug_norm and q_norm == slug_norm:
        breakdown["exact_slug"] = 300.0
    elif slug_norm and q_norm and (slug_norm in q_norm or q_norm in slug_norm):
        breakdown["slug_phrase"] = 150.0

    title_overlap = _overlap(q_set, record.title)
    if title_overlap:
        breakdown["title_tokens"] = 180.0 * title_overlap

    heading_text = " ".join(record.headings)
    heading_overlap = _overlap(q_set, heading_text)
    if heading_overlap:
        breakdown["headings"] = 105.0 * heading_overlap

    relationship_text = " ".join([record.series, record.article_map, record.parent_title])
    relationship_overlap = _overlap(q_set, relationship_text)
    if relationship_overlap:
        breakdown["series_map_parent"] = 90.0 * relationship_overlap

    taxonomy_overlap = _overlap(q_set, _taxonomy_text(record))
    if taxonomy_overlap:
        breakdown["taxonomy"] = 70.0 * taxonomy_overlap

    breakdown["title_terms"] = _field_term_score(query_counts, record.title, 16.0)
    breakdown["summary_terms"] = _field_term_score(query_counts, record.summary, 5.0)
    breakdown["content_terms"] = min(50.0, _field_term_score(query_counts, record.content[:18000], 1.3))

    if record.post_type in {"page", "article", "post"}:
        breakdown["public_content_type"] = 4.0
    if record.series or record.article_map:
        breakdown["structured_library_record"] = 8.0

    score = sum(breakdown.values())
    if exact_title:
        match_type = "exact-title"
    elif breakdown.get("title_phrase_in_query") or breakdown.get("query_phrase_in_title"):
        match_type = "title-phrase"
    elif title_overlap >= 0.75:
        match_type = "strong-title"
    elif relationship_overlap >= 0.5:
        match_type = "series-or-map"
    elif heading_overlap >= 0.5:
        match_type = "heading"
    else:
        match_type = "hybrid-lexical"
    return round(score, 4), {key: round(value, 4) for key, value in breakdown.items() if value > 0}, match_type, exact_title


def _cosine(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


def _bm25_scores(query: str, chunks: list[KnowledgeChunk]) -> dict[str, float]:
    query_terms = tokens(query)
    if not query_terms or not chunks:
        return {}
    documents: dict[str, list[str]] = {
        chunk.chunk_id: tokens(f"{chunk.heading} {chunk.heading} {chunk.passage}") for chunk in chunks
    }
    lengths = [len(values) for values in documents.values() if values]
    average_length = sum(lengths) / max(1, len(lengths))
    document_frequency: Counter[str] = Counter()
    for values in documents.values():
        document_frequency.update(set(values))
    total_documents = max(1, len(documents))
    scores: dict[str, float] = {}
    k1, b = 1.5, 0.75
    for chunk_id, values in documents.items():
        if not values:
            continue
        counts = Counter(values)
        document_length = len(values)
        score = 0.0
        for term in query_terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            df = document_frequency.get(term, 0)
            idf = math.log(1.0 + ((total_documents - df + 0.5) / (df + 0.5)))
            denominator = frequency + k1 * (1.0 - b + b * (document_length / max(1.0, average_length)))
            score += idf * ((frequency * (k1 + 1.0)) / denominator)
        if score > 0:
            scores[chunk_id] = score
    return scores


def _rrf(rank: int | None, k: int = 60) -> float:
    return 0.0 if rank is None else 1.0 / (k + rank)


def retrieve_with_diagnostics(
    query: str,
    records: list[KnowledgeRecord],
    chunks: list[KnowledgeChunk] | None = None,
    limit: int = 10,
    query_embedding: list[float] | None = None,
) -> tuple[list[RetrievedSource], dict[str, Any]]:
    chunks = chunks or []
    records_by_id = {record.id: record for record in records}
    structural: dict[str, tuple[float, dict[str, float], str, bool]] = {
        record.id: score_record(query, record) for record in records
    }
    bm25 = _bm25_scores(query, chunks)
    semantic = {
        chunk.chunk_id: max(0.0, _cosine(query_embedding, chunk.embedding))
        for chunk in chunks
        if query_embedding and chunk.embedding
    }
    lexical_rank = {
        chunk_id: rank for rank, (chunk_id, _) in enumerate(sorted(bm25.items(), key=lambda item: item[1], reverse=True), start=1)
    }
    semantic_rank = {
        chunk_id: rank for rank, (chunk_id, _) in enumerate(sorted(semantic.items(), key=lambda item: item[1], reverse=True), start=1)
        if _ > 0
    }
    structural_rank = {
        record_id: rank
        for rank, (record_id, _) in enumerate(
            sorted(structural.items(), key=lambda item: item[1][0], reverse=True), start=1
        )
    }

    best_chunk: dict[str, tuple[KnowledgeChunk, float, float, float]] = {}
    for chunk in chunks:
        lexical_score = bm25.get(chunk.chunk_id, 0.0)
        semantic_score = semantic.get(chunk.chunk_id, 0.0)
        fusion = (
            _rrf(lexical_rank.get(chunk.chunk_id))
            + _rrf(semantic_rank.get(chunk.chunk_id))
            + _rrf(structural_rank.get(chunk.record_id))
        )
        combined = lexical_score * 24.0 + semantic_score * 160.0 + fusion * 1400.0
        prior = best_chunk.get(chunk.record_id)
        if prior is None or combined > prior[3]:
            best_chunk[chunk.record_id] = (chunk, lexical_score, semantic_score, combined)

    ranked: list[RetrievedSource] = []
    for record_id, record in records_by_id.items():
        structural_score, breakdown, match_type, exact = structural[record_id]
        chunk_data = best_chunk.get(record_id)
        lexical_score = semantic_score = chunk_fusion = 0.0
        chunk = None
        if chunk_data:
            chunk, lexical_score, semantic_score, chunk_fusion = chunk_data
        total_score = structural_score + chunk_fusion
        if total_score <= 0:
            continue
        reasons: list[str] = []
        if exact:
            reasons.append("exact-title")
        if lexical_score > 0:
            reasons.append("bm25-section-match")
        if semantic_score > 0:
            reasons.append("semantic-similarity")
        if breakdown.get("series_map_parent"):
            reasons.append("relationship-context")
        if chunk and chunk.page:
            reasons.append("page-aware-document")
        section = chunk.heading if chunk else ""
        page = chunk.page if chunk else None
        passage = chunk.passage[:1200] if chunk else record.summary[:1200]
        ranked.append(
            RetrievedSource(
                id=record.id,
                title=record.title,
                url=record.url,
                summary=record.summary[:1000],
                post_type=record.post_type,
                slug=record.slug,
                series=record.series,
                article_map=record.article_map,
                parent_title=record.parent_title,
                score=round(total_score, 4),
                score_breakdown={
                    **breakdown,
                    "bm25": round(lexical_score, 5),
                    "semantic_cosine": round(semantic_score, 5),
                    "reciprocal_rank_fusion": round(chunk_fusion, 5),
                },
                match_type="hybrid-semantic" if semantic_score > 0 else match_type,
                exact_title_match=exact,
                source=record.source,
                route_id=record.route_id,
                chunk_id=chunk.chunk_id if chunk else "",
                section=section,
                page=page,
                passage=passage,
                lexical_score=round(lexical_score, 5),
                semantic_score=round(semantic_score, 5),
                fusion_score=round(chunk_fusion, 5),
                retrieval_reasons=reasons or [match_type],
            )
        )

    ranked.sort(
        key=lambda item: (
            item.exact_title_match,
            item.score,
            item.semantic_score,
            item.lexical_score,
            -len(item.title),
        ),
        reverse=True,
    )
    selected = ranked[:limit]
    for index, item in enumerate(selected, start=1):
        item.evidence_id = f"SC{index}"
        item.citation_label = f"[SC{index}]"

    diagnostics = {
        "intent": classify_intent(query),
        "retrieval_mode": "exact-title+bm25+semantic+rrf" if semantic else "exact-title+bm25+rrf",
        "records_considered": len(records),
        "chunks_considered": len(chunks),
        "lexical_matches": len(bm25),
        "semantic_matches": sum(1 for value in semantic.values() if value > 0),
        "semantic_used": bool(semantic),
        "query_embedding_dimensions": len(query_embedding or []),
        "result_count": len(selected),
        "exact_title_match": bool(selected and selected[0].exact_title_match),
    }
    return selected, diagnostics


def retrieve(query: str, records: list[KnowledgeRecord], limit: int = 10) -> list[RetrievedSource]:
    # Backward-compatible lexical/title API used by older tests and callers.
    matches, _ = retrieve_with_diagnostics(query, records, [], limit, None)
    return matches


def related_titles(best: RetrievedSource | None, records: list[KnowledgeRecord], limit: int = 8) -> list[RetrievedSource]:
    if best is None:
        return []
    relationship_query = " ".join(
        value for value in [best.series, best.article_map, best.parent_title, best.title] if value
    )
    ranked = retrieve(relationship_query, records, limit=limit + 4)
    return [item for item in ranked if item.id != best.id][:limit]


def evidence_from_matches(matches: list[RetrievedSource]) -> list[EvidenceCitation]:
    evidence: list[EvidenceCitation] = []
    for index, source in enumerate(matches, start=1):
        evidence.append(
            EvidenceCitation(
                id=source.evidence_id or f"SC{index}",
                record_id=source.id,
                chunk_id=source.chunk_id,
                title=source.title,
                url=source.url,
                section=source.section,
                page=source.page,
                passage=source.passage or source.summary,
                source_type=source.post_type,
                record_version=source.score_breakdown.get("record_version", "") if source.score_breakdown else "",
                reason=", ".join(source.retrieval_reasons) or source.match_type,
            )
        )
    return evidence


def confidence(matches: list[RetrievedSource]) -> dict[str, float | str | list[str]]:
    if not matches:
        return {
            "level": "low",
            "score": 12,
            "explanation": "No strong Sustainable Catalyst title, section, or source match was found.",
            "signals": ["no-source-match"],
        }
    best = matches[0]
    second_score = matches[1].score if len(matches) > 1 else 0.0
    separation = max(0.0, best.score - second_score)
    if best.exact_title_match:
        level, score = "high", 98
    elif best.semantic_score >= 0.72 and best.lexical_score > 0:
        level, score = "high", min(94, 82 + int(separation / 100))
    elif best.match_type in {"title-phrase", "strong-title"} and best.score >= 180:
        level, score = "high", min(93, 76 + int(separation / 100))
    elif best.score >= 85:
        level, score = "medium", min(84, 58 + int(separation / 100))
    else:
        level, score = "low", min(55, 25 + int(best.score / 8))
    signals = list(dict.fromkeys([*best.retrieval_reasons, best.match_type, f"source-count:{len(matches)}"]))
    return {
        "level": level,
        "score": score,
        "explanation": f"The strongest result is a {best.match_type} match supported by {len(matches)} grounded source candidate(s).",
        "signals": signals,
    }
