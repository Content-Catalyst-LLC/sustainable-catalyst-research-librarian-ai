from __future__ import annotations

from collections import Counter
import math
import re
import unicodedata
from urllib.parse import unquote

from .models import KnowledgeRecord, RetrievedSource


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
        breakdown["exact_title"] = 420.0
    elif title_norm and title_norm in q_norm:
        breakdown["title_phrase_in_query"] = 280.0
    elif q_norm and q_norm in title_norm:
        breakdown["query_phrase_in_title"] = 230.0

    if slug_norm and q_norm == slug_norm:
        breakdown["exact_slug"] = 250.0
    elif slug_norm and (slug_norm in q_norm or q_norm in slug_norm):
        breakdown["slug_phrase"] = 135.0

    title_overlap = _overlap(q_set, record.title)
    if title_overlap:
        breakdown["title_tokens"] = 150.0 * title_overlap

    heading_text = " ".join(record.headings)
    heading_overlap = _overlap(q_set, heading_text)
    if heading_overlap:
        breakdown["headings"] = 95.0 * heading_overlap

    relationship_text = " ".join([record.series, record.article_map, record.parent_title])
    relationship_overlap = _overlap(q_set, relationship_text)
    if relationship_overlap:
        breakdown["series_map_parent"] = 85.0 * relationship_overlap

    taxonomy_overlap = _overlap(q_set, _taxonomy_text(record))
    if taxonomy_overlap:
        breakdown["taxonomy"] = 65.0 * taxonomy_overlap

    breakdown["title_terms"] = _field_term_score(query_counts, record.title, 14.0)
    breakdown["summary_terms"] = _field_term_score(query_counts, record.summary, 5.0)
    breakdown["content_terms"] = min(48.0, _field_term_score(query_counts, record.content[:18000], 1.5))

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
        match_type = "hybrid-keyword"
    return round(score, 4), {key: round(value, 4) for key, value in breakdown.items() if value > 0}, match_type, exact_title


def _to_source(record: KnowledgeRecord, score: float, breakdown: dict[str, float], match_type: str, exact: bool) -> RetrievedSource:
    return RetrievedSource(
        id=record.id,
        title=record.title,
        url=record.url,
        summary=record.summary[:1000],
        post_type=record.post_type,
        slug=record.slug,
        series=record.series,
        article_map=record.article_map,
        parent_title=record.parent_title,
        score=score,
        score_breakdown=breakdown,
        match_type=match_type,
        exact_title_match=exact,
        source=record.source,
        route_id=record.route_id,
    )


def retrieve(query: str, records: list[KnowledgeRecord], limit: int = 10) -> list[RetrievedSource]:
    ranked: list[RetrievedSource] = []
    for record in records:
        score, breakdown, match_type, exact = score_record(query, record)
        if score <= 0:
            continue
        ranked.append(_to_source(record, score, breakdown, match_type, exact))
    ranked.sort(key=lambda item: (item.exact_title_match, item.score, len(item.title)), reverse=True)
    return ranked[:limit]


def related_titles(best: RetrievedSource | None, records: list[KnowledgeRecord], limit: int = 8) -> list[RetrievedSource]:
    if best is None:
        return []
    relationship_query = " ".join(
        value for value in [best.series, best.article_map, best.parent_title, best.title] if value
    )
    ranked = retrieve(relationship_query, records, limit=limit + 4)
    return [item for item in ranked if item.id != best.id][:limit]


def confidence(matches: list[RetrievedSource]) -> dict[str, float | str | list[str]]:
    if not matches:
        return {
            "level": "low",
            "score": 12,
            "explanation": "No strong Sustainable Catalyst title or source match was found.",
            "signals": ["no-source-match"],
        }
    best = matches[0]
    second_score = matches[1].score if len(matches) > 1 else 0.0
    separation = max(0.0, best.score - second_score)
    if best.exact_title_match:
        level, score = "high", 98
    elif best.match_type in {"title-phrase", "strong-title"} and best.score >= 140:
        level, score = "high", min(94, 76 + int(separation / 10))
    elif best.score >= 75:
        level, score = "medium", min(82, 55 + int(separation / 10))
    else:
        level, score = "low", min(52, 25 + int(best.score / 3))
    return {
        "level": level,
        "score": score,
        "explanation": f"The best match is a {best.match_type} result with {len(matches)} grounded source candidate(s).",
        "signals": [best.match_type, "title-aware-retrieval", f"source-count:{len(matches)}"],
    }
