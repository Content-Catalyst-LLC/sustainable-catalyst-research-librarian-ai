from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import httpx

from .config import settings
from .models import RetrievedSource


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


def _source_context(matches: list[RetrievedSource]) -> str:
    blocks: list[str] = []
    for index, source in enumerate(matches, start=1):
        blocks.append(
            "\n".join(
                [
                    f"SOURCE {index}",
                    f"Title: {source.title}",
                    f"URL: {source.url}",
                    f"Type: {source.post_type}",
                    f"Series: {source.series or 'Not specified'}",
                    f"Article map: {source.article_map or 'Not specified'}",
                    f"Parent: {source.parent_title or 'Not specified'}",
                    f"Summary: {source.summary or 'No summary available'}",
                    f"Retrieval: {source.match_type}; score={source.score}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _system_instruction() -> str:
    return (
        "You are Sustainable Catalyst Research Librarian AI, a production-quality, site-scoped research guide. "
        "Your purpose is to understand the visitor's intent and recommend the strongest actual Sustainable Catalyst titles, "
        "series, article maps, evidence workspaces, analytical tools, repositories, and decision workflows. "
        "Use only the supplied Sustainable Catalyst sources and platform actions. Never invent a title, link, source, or capability. "
        "Lead with a direct, useful answer rather than internal route machinery. Name exact page and article titles whenever they are present. "
        "For country questions, prioritize Site Intelligence and Country Intelligence, then connect relevant library titles. "
        "When the user appears to be asking for an exact title, explicitly confirm the title and link it. "
        "When evidence is incomplete, state the limitation and ask one focused clarification. "
        "Keep internal scoring out of the prose. Do not act as a general chatbot or provide professional advice."
    )


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

Grounded Sustainable Catalyst sources:
{_source_context(matches)}

Related indexed titles:
{related_text or 'No related titles were found.'}

Write a concise but substantial answer using this structure:
1. A direct answer in two or three sentences.
2. Best matches — name the strongest exact Sustainable Catalyst titles and explain why each fits.
3. Suggested research path — give three to five ordered steps using only supplied links.
4. Public evidence or analysis actions — mention Site Intelligence, Workbench, or Decision Studio only when supported by the question and supplied context.
5. One focused follow-up question only when clarification would materially improve the route.

Use Markdown headings and links. Do not expose retrieval scores, API details, or internal reason codes."""

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
