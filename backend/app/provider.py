from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any

import httpx

from .config import settings
from .models import RetrievedSource


_CITATION_RE = re.compile(r"\[SC(\d+)\]")
_MARKDOWN_URL_RE = re.compile(r"\]\(([^)\s]+)(?:\s+[^)]*)?\)")
_RAW_URL_RE = re.compile(r"https?://[^\s)\]>]+")


class ProviderState:
    def __init__(self) -> None:
        self.last_success_utc = ""
        self.last_failure_utc = ""
        self.last_error = ""

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def success(self) -> None:
        self.last_success_utc = self.now()
        self.last_error = ""

    def failure(self, error: str) -> None:
        self.last_failure_utc = self.now()
        self.last_error = error[:1000]


provider_state = ProviderState()


def configured() -> bool:
    return settings.provider == "gemini" and bool(settings.gemini_api_key and settings.gemini_model)


def embeddings_configured() -> bool:
    return settings.semantic_enabled and settings.provider == "gemini" and bool(
        settings.gemini_api_key and settings.gemini_embedding_model
    )


def _source_context(matches: list[RetrievedSource]) -> str:
    blocks: list[str] = []
    for index, source in enumerate(matches, start=1):
        location = source.section or "Record summary"
        if source.page:
            location = f"{location}; PDF/document page {source.page}"
        blocks.append(
            "\n".join(
                [
                    f"SOURCE SC{index}",
                    f"Citation token: [SC{index}]",
                    f"Title: {source.title}",
                    f"URL: {source.url}",
                    f"Type: {source.post_type}",
                    f"Location: {location}",
                    f"Series: {source.series or 'Not specified'}",
                    f"Article map: {source.article_map or 'Not specified'}",
                    f"Parent: {source.parent_title or 'Not specified'}",
                    f"Evidence passage: {source.passage or source.summary or 'No passage available'}",
                    f"Retrieval reasons: {', '.join(source.retrieval_reasons) or source.match_type}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _system_instruction() -> str:
    return (
        "You are Sustainable Catalyst Research Librarian AI, a production-quality, site-scoped research guide. "
        "Use only the supplied Sustainable Catalyst evidence records and platform actions. Never invent a title, link, source, passage, page, or capability. "
        "Every substantive factual paragraph must end with one or more supplied citation tokens such as [SC1]. "
        "Use a page number only when the source explicitly supplies one. "
        "Lead with a direct answer, name exact source titles, and distinguish retrieved evidence from interpretation. "
        "When evidence is incomplete, state the limitation and ask one focused clarification. "
        "Do not expose retrieval scores or internal implementation details. Do not act as a general chatbot or provide professional advice."
    )


async def generate_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    if not embeddings_configured():
        raise RuntimeError("Gemini embeddings are not configured on the Python backend.")
    model_name = settings.gemini_embedding_model.replace("models/", "", 1).strip()
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:embedContent"
    payload = {
        "model": f"models/{model_name}",
        "content": {"parts": [{"text": text[:30000]}]},
        "taskType": task_type,
    }
    headers = {"X-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        values = ((data.get("embedding") or {}).get("values") or [])
        embedding = [float(value) for value in values]
        if not embedding:
            raise RuntimeError("Gemini returned no embedding values.")
        return embedding
    except (httpx.HTTPError, ValueError, KeyError, RuntimeError) as exc:
        provider_state.failure(str(exc))
        raise RuntimeError(str(exc)) from exc


def verify_citations(
    answer: str,
    matches: list[RetrievedSource],
    related: list[RetrievedSource] | None = None,
) -> dict[str, Any]:
    related = related or []
    citation_numbers = [int(value) for value in _CITATION_RE.findall(answer or "")]
    valid_numbers = set(range(1, len(matches) + 1))
    invalid_citations = sorted({value for value in citation_numbers if value not in valid_numbers})
    allowed_urls = {item.url.rstrip("/") for item in [*matches, *related] if item.url}
    found_urls = set(_MARKDOWN_URL_RE.findall(answer or "")) | set(_RAW_URL_RE.findall(answer or ""))
    unknown_urls: list[str] = []
    for url in found_urls:
        clean = url.rstrip("/")
        if clean in allowed_urls:
            continue
        unknown_urls.append(url)
    missing_required = bool(settings.citation_required and matches and not citation_numbers)
    ok = not invalid_citations and not unknown_urls and not missing_required
    return {
        "ok": ok,
        "required": settings.citation_required,
        "citation_count": len(citation_numbers),
        "unique_citations": [f"SC{value}" for value in sorted(set(citation_numbers)) if value in valid_numbers],
        "invalid_citations": [f"SC{value}" for value in invalid_citations],
        "unknown_urls": sorted(unknown_urls),
        "missing_required_citations": missing_required,
        "verified_source_count": len(matches),
    }


async def generate_answer(
    question: str,
    matches: list[RetrievedSource],
    related: list[RetrievedSource],
    history: list[dict[str, str]],
    route_hint: dict[str, Any],
) -> str:
    if not configured():
        raise RuntimeError("Gemini is not configured on the Python backend.")

    history_text = "\n".join(
        f"{item.get('role', 'user').upper()}: {item.get('content', '')[:1200]}" for item in history[-settings.max_session_turns :]
    )
    related_text = "\n".join(f"- {item.title}: {item.url}" for item in related[: settings.related_limit])
    prompt = f"""Visitor question:
{question}

Recent session context:
{history_text or 'No prior turns.'}

WordPress route hint:
{json.dumps(route_hint or {}, ensure_ascii=False)}

Verified Sustainable Catalyst evidence:
{_source_context(matches)}

Related indexed titles for navigation only:
{related_text or 'No related titles were found.'}

Write a concise but substantial Markdown answer using this structure:
1. Direct answer.
2. Verified evidence — explain the strongest matching passages and titles.
3. Suggested research path — three to five ordered steps using only supplied source links.
4. Public evidence or analysis actions when relevant.
5. One focused follow-up question only when clarification materially improves the route.

Citation contract:
- End every substantive factual paragraph with one or more valid tokens such as [SC1].
- Do not create citation tokens beyond the supplied SC numbers.
- Do not link to any URL that was not supplied above.
- Do not cite a PDF page unless the matching source explicitly supplied that page.
- Do not expose scores, embeddings, or internal reason codes."""

    model_name = settings.gemini_model.replace("models/", "", 1).strip()
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": _system_instruction()}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": settings.temperature,
            "maxOutputTokens": settings.max_output_tokens,
        },
    }
    headers = {"X-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        candidates = data.get("candidates") or []
        parts = (((candidates[0] if candidates else {}).get("content") or {}).get("parts") or [])
        text = "\n".join(str(part.get("text", "")) for part in parts if part.get("text")).strip()
        if not text:
            raise RuntimeError("Gemini returned no answer text.")
        provider_state.success()
        return text
    except (httpx.HTTPError, ValueError, KeyError, RuntimeError) as exc:
        provider_state.failure(str(exc))
        raise RuntimeError(str(exc)) from exc
