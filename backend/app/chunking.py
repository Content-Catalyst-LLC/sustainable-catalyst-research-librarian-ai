from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Iterable

from .models import KnowledgeRecord


_WORD_RE = re.compile(r"\S+")


@dataclass(frozen=True)
class ChunkSeed:
    chunk_id: str
    record_id: str
    heading: str
    page: int | None
    passage: str
    position: int
    content_hash: str


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _chunk_id(record_id: str, position: int, heading: str, page: int | None, passage: str) -> str:
    digest = hashlib.sha256()
    digest.update(record_id.encode("utf-8"))
    digest.update(b"|")
    digest.update(str(position).encode("ascii"))
    digest.update(b"|")
    digest.update(heading.encode("utf-8"))
    digest.update(b"|")
    digest.update(str(page or 0).encode("ascii"))
    digest.update(b"|")
    digest.update(passage.encode("utf-8"))
    return f"chunk:{digest.hexdigest()[:32]}"


def _content_hash(heading: str, page: int | None, passage: str) -> str:
    payload = f"{heading}\n{page or 0}\n{passage}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _window_words(text: str, max_words: int, overlap_words: int) -> Iterable[str]:
    words = _WORD_RE.findall(_clean(text))
    if not words:
        return
    start = 0
    while start < len(words):
        end = min(len(words), start + max_words)
        yield " ".join(words[start:end])
        if end >= len(words):
            break
        start = max(start + 1, end - overlap_words)


def _metadata_sections(record: KnowledgeRecord) -> list[dict[str, Any]]:
    raw = record.metadata.get("sections", []) if isinstance(record.metadata, dict) else []
    if not isinstance(raw, list):
        return []
    sections: list[dict[str, Any]] = []
    for item in raw[:120]:
        if not isinstance(item, dict):
            continue
        text = _clean(item.get("text") or item.get("content") or item.get("passage"))
        if not text:
            continue
        page_value = item.get("page")
        try:
            page = int(page_value) if page_value not in (None, "") else None
        except (TypeError, ValueError):
            page = None
        sections.append(
            {
                "heading": _clean(item.get("heading") or item.get("title") or "Document section")[:500],
                "page": page if page and page > 0 else None,
                "text": text,
            }
        )
    return sections


def chunk_record(record: KnowledgeRecord, max_words: int = 220, overlap_words: int = 35) -> list[ChunkSeed]:
    """Create deterministic, section-aware chunks for lexical and semantic retrieval.

    WordPress v6.4.1 supplies explicit section metadata when available. Older
    records remain compatible through summary, heading, and sliding-window
    fallbacks. PDF/library records may provide a page number per section.
    """

    candidates: list[tuple[str, int | None, str]] = []
    sections = _metadata_sections(record)
    if sections:
        for section in sections:
            for passage in _window_words(section["text"], max_words, overlap_words):
                candidates.append((section["heading"], section["page"], passage))
    else:
        if record.summary:
            candidates.append(("Summary", None, _clean(record.summary)))
        content_windows = list(_window_words(record.content, max_words, overlap_words))
        headings = [value for value in (_clean(item) for item in record.headings) if value]
        for position, passage in enumerate(content_windows):
            heading = "Article text"
            if headings:
                heading_index = min(len(headings) - 1, int((position / max(1, len(content_windows))) * len(headings)))
                heading = headings[heading_index]
            candidates.append((heading, None, passage))
        if not content_windows:
            for heading in headings:
                candidates.append((heading, None, heading))

    # A title-only chunk ensures exact-title lookup remains available even for
    # records with no extractable body text.
    title_passage = _clean(" — ".join(value for value in [record.title, record.summary] if value))
    if title_passage:
        candidates.insert(0, ("Title and summary", None, title_passage))

    chunks: list[ChunkSeed] = []
    seen: set[tuple[str, int | None, str]] = set()
    for position, (heading, page, passage) in enumerate(candidates):
        heading = _clean(heading)[:500]
        passage = _clean(passage)[:12000]
        key = (heading.lower(), page, passage.lower())
        if not passage or key in seen:
            continue
        seen.add(key)
        chunks.append(
            ChunkSeed(
                chunk_id=_chunk_id(record.id, position, heading, page, passage),
                record_id=record.id,
                heading=heading,
                page=page,
                passage=passage,
                position=position,
                content_hash=_content_hash(heading, page, passage),
            )
        )
    return chunks[:300]
