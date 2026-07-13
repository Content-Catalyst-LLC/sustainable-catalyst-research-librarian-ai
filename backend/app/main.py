from __future__ import annotations

from collections import defaultdict
import hashlib
import hmac
import json
import re
import time
from typing import Any
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .models import (
    AskRequest,
    AskResponse,
    RetrievalRequest,
    RetrievedSource,
    StatusResponse,
    SyncRequest,
    SyncResponse,
    utc_now,
)
from .provider import configured as provider_configured
from .provider import generate_answer, provider_state
from .retrieval import confidence, related_titles, retrieve
from .store import store


app = FastAPI(
    title="Sustainable Catalyst Research Librarian AI",
    version=__version__,
    description="Python knowledge intelligence, title-aware retrieval, and grounded AI guidance for Sustainable Catalyst.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-SC-RL-Key"],
)

_sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)


def require_key(x_sc_rl_key: str = Header(default="")) -> None:
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SC_RL_BACKEND_API_KEY is not configured on the backend.",
        )
    if not x_sc_rl_key or not hmac.compare_digest(hashlib.sha256(x_sc_rl_key.encode()).digest(), hashlib.sha256(settings.api_key.encode()).digest()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid backend integration key.")


def _session_id(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", value or "")[:180]
    return clean or uuid.uuid4().hex


def _prune_sessions() -> None:
    cutoff = time.time() - settings.session_ttl_seconds
    expired: list[str] = []
    for session_id, turns in _sessions.items():
        if not turns or float(turns[-1].get("ts", 0)) < cutoff:
            expired.append(session_id)
    for session_id in expired:
        _sessions.pop(session_id, None)


def _deterministic_answer(question: str, matches: list[RetrievedSource], related: list[RetrievedSource]) -> str:
    if not matches:
        return (
            "## I could not verify a strong Sustainable Catalyst title yet\n\n"
            "The knowledge index does not currently contain a sufficiently strong match for this question. "
            "Try naming the subject, article title, country, calculation, or decision task more specifically.\n\n"
            "[Open the Knowledge Library](/knowledge-libraries/) or [submit a missing-capability report](/platform/feature-suggestions/)."
        )
    best = matches[0]
    lines = [
        "## Best verified match",
        f"[{best.title}]({best.url})",
        "",
        best.summary or "This is the strongest title-aware match in the current Sustainable Catalyst index.",
        "",
        "## Other relevant titles",
    ]
    for source in matches[1:5]:
        lines.append(f"- [{source.title}]({source.url}) — {source.summary[:220]}")
    if related:
        lines.extend(["", "## Continue through the library"])
        for source in related[:4]:
            lines.append(f"- [{source.title}]({source.url})")
    lines.extend(
        [
            "",
            "The Python knowledge service found these results through exact-title, title-phrase, heading, series, article-map, taxonomy, and content matching. AI generation is currently unavailable, so no unsupported prose was added.",
        ]
    )
    return "\n".join(lines)


def _research_path(matches: list[RetrievedSource], related: list[RetrievedSource]) -> list[dict[str, str]]:
    path: list[dict[str, str]] = []
    seen: set[str] = set()
    for source in [*matches[:3], *related[:3]]:
        if source.url in seen:
            continue
        seen.add(source.url)
        path.append({"title": source.title, "url": source.url, "reason": source.match_type})
        if len(path) >= 5:
            break
    return path


def _actions(question: str, best: RetrievedSource | None) -> list[dict[str, str]]:
    q = question.lower()
    actions: list[dict[str, str]] = []
    if best:
        actions.append({"label": "Open best match", "url": best.url, "type": "source"})
    if any(term in q for term in ["country", "pakistan", "climate", "indicator", "public evidence", "compare countries"]):
        actions.append({"label": "Open Site Intelligence", "url": "/platform/site-intelligence/", "type": "evidence"})
    if any(term in q for term in ["calculate", "formula", "graph", "model", "analysis", "simulate"]):
        actions.append({"label": "Use Workbench", "url": "/modeling-analytics/workbench/", "type": "analysis"})
    if any(term in q for term in ["decision", "brief", "scenario", "tradeoff", "recommendation"]):
        actions.append({"label": "Open Decision Studio", "url": "/platform/decision-studio/", "type": "decision"})
    actions.append({"label": "Report a missing route", "url": "/platform/feature-suggestions/", "type": "feedback"})
    return actions[:5]


def _status() -> StatusResponse:
    summary = store.summary()
    ai_ready = provider_configured()
    index_ready = int(summary.get("total_records", 0)) > 0
    if ai_ready and index_ready and provider_state.last_success_utc:
        state, label = "online", "AI and Knowledge Index Online"
    elif ai_ready and index_ready:
        state, label = "ready", "AI Configured — Knowledge Index Ready"
    elif index_ready:
        state, label = "retrieval-only", "Knowledge Index Online — AI Not Configured"
    else:
        state, label = "needs-sync", "Knowledge Index Needs Sync"
    return StatusResponse(
        version=__version__,
        state=state,
        label=label,
        provider=settings.provider,
        model=settings.gemini_model if settings.provider == "gemini" else "",
        ai_configured=ai_ready,
        index_ready=index_ready,
        indexed_records=int(summary.get("total_records", 0)),
        indexed_titles=int(summary.get("indexed_titles", 0)),
        semantic_retrieval="title-aware-hybrid",
        last_sync_utc=str(summary.get("last_sync_utc", "")),
        source_site=str(summary.get("source_site", "")),
        last_ai_success_utc=provider_state.last_success_utc,
        last_ai_failure_utc=provider_state.last_failure_utc,
        last_ai_error=provider_state.last_error,
    )


@app.get("/")
def root() -> dict[str, Any]:
    current = _status()
    return {
        "ok": True,
        "service": "Sustainable Catalyst Research Librarian AI",
        "version": __version__,
        "state": current.state,
        "indexed_records": current.indexed_records,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "environment": settings.environment}


@app.get("/status", response_model=StatusResponse)
def status_endpoint() -> StatusResponse:
    return _status()


@app.post("/v1/knowledge/sync", response_model=SyncResponse, dependencies=[Depends(require_key)])
def sync_knowledge(payload: SyncRequest) -> SyncResponse:
    meta = store.sync(payload.records, payload.mode, payload.source_site)
    summary = store.summary()
    return SyncResponse(
        mode=payload.mode,
        received=len(payload.records),
        accepted=len(payload.records),
        rejected=0,
        job_id=payload.job_id,
        batch_index=payload.batch_index,
        batch_count=payload.batch_count,
        total_records=int(summary["total_records"]),
        indexed_titles=int(summary["indexed_titles"]),
        last_sync_utc=str(meta["last_sync_utc"]),
        source_site=str(meta.get("source_site", "")),
    )


@app.get("/v1/knowledge/summary", response_model=StatusResponse, dependencies=[Depends(require_key)])
def knowledge_summary() -> StatusResponse:
    return _status()


@app.post("/v1/retrieve", response_model=list[RetrievedSource], dependencies=[Depends(require_key)])
def retrieve_endpoint(payload: RetrievalRequest) -> list[RetrievedSource]:
    return retrieve(payload.query, store.records(), payload.limit)


@app.post("/v1/ask", response_model=AskResponse, dependencies=[Depends(require_key)])
async def ask(payload: AskRequest) -> AskResponse:
    _prune_sessions()
    session_id = _session_id(payload.session_id)
    records = store.records()
    matches = retrieve(payload.question, records, settings.source_limit)
    best = matches[0] if matches else None
    related = related_titles(best, records, settings.related_limit)
    certainty = confidence(matches)
    history = [
        {"role": str(turn.get("role", "user")), "content": str(turn.get("content", ""))}
        for turn in _sessions.get(session_id, [])[-settings.max_session_turns :]
    ]

    ai_used = False
    source = "python-title-aware-retrieval"
    provider = ""
    model = ""
    try:
        if not matches:
            raise RuntimeError("No grounded Sustainable Catalyst sources were retrieved.")
        answer = await generate_answer(payload.question, matches, related, history, payload.route_hint)
        ai_used = True
        source = "python-gemini-grounded"
        provider = settings.provider
        model = settings.gemini_model
    except RuntimeError:
        answer = _deterministic_answer(payload.question, matches, related)

    _sessions[session_id].extend(
        [
            {"role": "user", "content": payload.question, "ts": time.time()},
            {"role": "assistant", "content": answer[:5000], "ts": time.time()},
        ]
    )
    _sessions[session_id] = _sessions[session_id][-settings.max_session_turns * 2 :]

    return AskResponse(
        answer=answer,
        source=source,
        ai_used=ai_used,
        provider=provider,
        model=model,
        session_id=session_id,
        best_match=best,
        matches=matches,
        related_titles=related,
        research_path=_research_path(matches, related),
        actions=_actions(payload.question, best),
        interpretation="Title-aware Sustainable Catalyst knowledge retrieval followed by grounded AI synthesis." if ai_used else "Title-aware Sustainable Catalyst knowledge retrieval without AI synthesis.",
        clarification="" if certainty.get("level") != "low" else "Which Sustainable Catalyst subject, title, country, tool, or intended output should the search prioritize?",
        confidence=certainty,
        status=_status().model_dump(),
    )
