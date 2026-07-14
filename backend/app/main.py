from __future__ import annotations

from collections import defaultdict
import asyncio
import hashlib
import hmac
import json
from pathlib import Path
import re
import time
from typing import Any
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from . import __version__
from .calibration import evidence_gate, sanitize_retrieval_config
from .config import settings
from .models import (
    AskRequest,
    AskResponse,
    BenchmarkCase,
    BenchmarkRequest,
    EmbeddingProcessRequest,
    MaintenanceRequest,
    RetrievalCalibrationUpdate,
    RetrievalRequest,
    RetrievedSource,
    RollbackRequest,
    SessionResetRequest,
    StatusResponse,
    SyncRequest,
    SyncResponse,
    utc_now,
)
from .provider import configured as provider_configured
from .provider import embeddings_configured, generate_answer, generate_embedding, provider_state, verify_citations
from .retrieval import confidence, evidence_from_matches, related_titles, retrieve, retrieve_with_diagnostics
from .store import store


app = FastAPI(
    title="Sustainable Catalyst Research Librarian AI",
    version=__version__,
    description="Python knowledge intelligence, title-aware retrieval, and grounded AI guidance for Sustainable Catalyst.",
)
app.add_middleware(GZipMiddleware, minimum_size=900)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-SC-RL-Key"],
)

_sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)

_RESEARCH_MODES: dict[str, dict[str, str]] = {
    "auto": {"label": "Auto-detect", "instruction": "Infer the most useful site-scoped research workflow."},
    "title": {"label": "Find a title", "instruction": "Prioritize exact and near-exact canonical titles and series order."},
    "subject": {"label": "Explore a subject", "instruction": "Synthesize the strongest verified subject overview and connected concepts."},
    "path": {"label": "Build a research path", "instruction": "Return an ordered path through verified Sustainable Catalyst records."},
    "evidence": {"label": "Find evidence", "instruction": "Prioritize passages, sections, page references, and attributable evidence."},
    "analyze": {"label": "Analyze a question", "instruction": "Identify assumptions, methods, calculations, and appropriate Workbench actions."},
    "compare": {"label": "Compare records", "instruction": "Compare verified records without inventing differences or unsupported claims."},
    "decision": {"label": "Prepare a decision", "instruction": "Organize evidence, uncertainty, alternatives, and Decision Studio actions."},
}


def _resolve_research_mode(question: str, requested: str = "auto") -> str:
    clean = (requested or "auto").strip().lower()
    if clean in _RESEARCH_MODES and clean != "auto":
        return clean
    q = (question or "").lower()
    if any(term in q for term in ["titled", "exact title", "article called", "find the article"]):
        return "title"
    if any(term in q for term in ["evidence", "source", "citation", "page", "passage", "supporting"]):
        return "evidence"
    if any(term in q for term in ["compare", "difference", "versus", " vs "]):
        return "compare"
    if any(term in q for term in ["decision", "tradeoff", "scenario", "brief", "recommendation"]):
        return "decision"
    if any(term in q for term in ["calculate", "formula", "model", "analyze", "analysis", "graph", "simulate"]):
        return "analyze"
    if any(term in q for term in ["path", "sequence", "where should i start", "reading order", "learn"]):
        return "path"
    return "subject"


def _follow_up_prompts(mode: str, best: RetrievedSource | None, related: list[RetrievedSource]) -> list[str]:
    title = best.title if best else "this subject"
    prompts: list[str] = []
    if mode == "title":
        prompts = [f"What comes before and after {title} in its series?", f"Show the strongest passages in {title}."]
    elif mode == "evidence":
        prompts = [f"Which passages in {title} provide the strongest support?", "Show related records that disagree or add important context."]
    elif mode == "path":
        prompts = [f"Turn {title} into a five-step reading path.", "Which step should lead into Workbench or Site Intelligence?"]
    elif mode == "analyze":
        prompts = [f"What assumptions and variables should I extract from {title}?", "Prepare the next analytical step for Workbench."]
    elif mode == "compare":
        other = related[0].title if related else "the next closest record"
        prompts = [f"Compare {title} with {other} using only verified evidence.", "What important difference remains unresolved?"]
    elif mode == "decision":
        prompts = [f"What evidence and uncertainty from {title} belong in a decision packet?", "Prepare the next Decision Studio step."]
    else:
        prompts = [f"Explain the key concepts connected to {title}.", f"Build a research path starting with {title}."]
    return prompts[:3]


def _workspace_summary(mode: str, matches: list[RetrievedSource], related: list[RetrievedSource], ai_used: bool, gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "sc-research-librarian-public-workspace/1.1",
        "mode": mode,
        "mode_label": _RESEARCH_MODES.get(mode, _RESEARCH_MODES["auto"])["label"],
        "verified_sources": len(matches),
        "related_titles": len(related),
        "answer_kind": "citation-verified-ai" if ai_used else "deterministic-evidence",
        "evidence_gate_passed": bool(gate.get("ok")),
        "exports": ["copy", "markdown", "json", "print", "research-note"],
        "accessibility_profile": "wcag-focused-v6.5.1",
        "rendering_profile": "staged-v6.5.1",
    }


_SERVICE_STARTED_MONOTONIC = time.monotonic()
_SERVICE_STARTED_UTC = utc_now()


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
            "## I could not verify a strong Sustainable Catalyst source yet\n\n"
            "The current index does not contain a sufficiently strong title or section match. "
            "Try naming the subject, article title, country, calculation, or decision task more specifically.\n\n"
            "Open the Knowledge Library or submit a missing-capability report from the Sustainable Catalyst platform."
        )
    best = matches[0]
    best_location = best.section or "record summary"
    if best.page:
        best_location += f", page {best.page}"
    lines = [
        "## Best verified evidence",
        f"[{best.title}]({best.url}) — {best_location}. {best.passage or best.summary} [SC1]",
        "",
        "## Other relevant sources",
    ]
    for index, source in enumerate(matches[1:5], start=2):
        location = source.section or "record summary"
        if source.page:
            location += f", page {source.page}"
        lines.append(f"- [{source.title}]({source.url}) — {location}. {source.passage or source.summary} [SC{index}]")
    if related:
        lines.extend(["", "## Continue through the library"])
        for source in related[:4]:
            lines.append(f"- [{source.title}]({source.url})")
    lines.extend(
        [
            "",
            "This fallback uses exact-title, BM25 section matching, relationship signals, and any available verified semantic embeddings. No unsupported generated prose was added.",
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


def _actions(question: str, best: RetrievedSource | None, research_mode: str = "auto") -> list[dict[str, str]]:
    q = question.lower()
    actions: list[dict[str, str]] = []
    if best:
        actions.append({"label": "Open best match", "url": best.url, "type": "source"})
    if research_mode == "evidence" and best:
        actions.append({"label": "Open cited evidence", "url": best.url, "type": "evidence"})
    if any(term in q for term in ["country", "pakistan", "climate", "indicator", "public evidence", "compare countries"]):
        actions.append({"label": "Open Site Intelligence", "url": "/platform/site-intelligence/", "type": "evidence"})
    if research_mode == "analyze" or any(term in q for term in ["calculate", "formula", "graph", "model", "analysis", "simulate"]):
        actions.append({"label": "Use Workbench", "url": "/modeling-analytics/workbench/", "type": "analysis"})
    if research_mode == "decision" or any(term in q for term in ["decision", "brief", "scenario", "tradeoff", "recommendation"]):
        actions.append({"label": "Open Decision Studio", "url": "/platform/decision-studio/", "type": "decision"})
    actions.append({"label": "Report a missing route", "url": "/platform/feature-suggestions/", "type": "feedback"})
    return actions[:5]


def _startup_snapshot(summary: dict[str, Any] | None = None) -> dict[str, Any]:
    summary = summary or store.summary()
    uptime = max(0, int(time.monotonic() - _SERVICE_STARTED_MONOTONIC))
    warmup = max(0, settings.startup_warmup_seconds)
    warming = warmup > 0 and uptime < warmup
    if warming:
        progress = min(95, max(10, int((uptime / warmup) * 100)))
        phase = "opening-runtime-index" if int(summary.get("total_records", 0)) else "awaiting-index-recovery"
        state = "warming"
    elif int(summary.get("total_records", 0)) == 0:
        progress = 100
        phase = "awaiting-index-recovery"
        state = "ready"
    else:
        progress = 100
        phase = "ready"
        state = "ready"
    return {
        "startup_state": state,
        "startup_phase": phase,
        "startup_progress": progress,
        "service_started_utc": _SERVICE_STARTED_UTC,
        "uptime_seconds": uptime,
        "ready": not warming,
    }


def _status() -> StatusResponse:
    summary = store.summary()
    ai_ready = provider_configured()
    index_ready = int(summary.get("total_records", 0)) > 0
    startup = _startup_snapshot(summary)
    if startup["startup_state"] == "warming":
        state, label = "backend-warming", "Python Backend Warming"
    elif ai_ready and index_ready and provider_state.last_success_utc:
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
        semantic_retrieval=("exact-title+bm25+semantic+rrf" if float(summary.get("semantic_coverage", 0)) > 0 else "exact-title+bm25+rrf"),
        last_sync_utc=str(summary.get("last_sync_utc", "")),
        source_site=str(summary.get("source_site", "")),
        storage_engine=str(summary.get("storage_engine", "sqlite")),
        schema_version=int(summary.get("schema_version", 5)),
        index_version=int(summary.get("index_version", 0)),
        checksum=str(summary.get("checksum", "")),
        snapshot_count=int(summary.get("snapshot_count", 0)),
        staging_jobs=int(summary.get("staging_jobs", 0)),
        stalled_jobs=int(summary.get("stalled_jobs", 0)),
        recovery_needed=bool(summary.get("recovery_needed", False)),
        last_recovery_utc=str(summary.get("last_recovery_utc", "")),
        last_rollback_utc=str(summary.get("last_rollback_utc", "")),
        last_ai_success_utc=provider_state.last_success_utc,
        last_ai_failure_utc=provider_state.last_failure_utc,
        last_ai_error=provider_state.last_error,
        indexed_chunks=int(summary.get("indexed_chunks", 0)),
        embedded_chunks=int(summary.get("embedded_chunks", 0)),
        semantic_coverage=float(summary.get("semantic_coverage", 0.0)),
        embedding_model=str(summary.get("embedding_model", settings.gemini_embedding_model)),
        retrieval_profile=str(summary.get("retrieval_profile", "balanced-v6.5.0")),
        benchmark_runs=int(summary.get("benchmark_runs", 0)),
        **startup,
    )


async def _hybrid_retrieve(
    query: str,
    limit: int,
    calibration: dict[str, Any] | None = None,
    include_semantic: bool = True,
) -> tuple[list[RetrievedSource], dict[str, Any]]:
    config = sanitize_retrieval_config(calibration or store.retrieval_config())
    records = store.records()
    chunks = store.chunks()
    query_embedding: list[float] | None = None
    semantic_error = ""
    embedding_latency_ms = 0.0
    embedding_status = store.embedding_status()
    if (
        include_semantic
        and float(config["weights"]["semantic"]) > 0
        and settings.semantic_enabled
        and settings.semantic_query_embeddings
        and int(embedding_status.get("embedded_chunks", 0)) > 0
        and embeddings_configured()
    ):
        embedding_started = time.perf_counter()
        try:
            query_embedding = await generate_embedding(query, "RETRIEVAL_QUERY")
        except RuntimeError as exc:
            semantic_error = str(exc)[:500]
        embedding_latency_ms = (time.perf_counter() - embedding_started) * 1000
    matches, diagnostics = retrieve_with_diagnostics(query, records, chunks, limit, query_embedding, config)
    diagnostics["semantic_error"] = semantic_error
    diagnostics["semantic_coverage"] = embedding_status.get("semantic_coverage", 0.0)
    diagnostics["embedding_model"] = settings.gemini_embedding_model
    diagnostics["embedding_latency_ms"] = round(embedding_latency_ms, 3)
    diagnostics["context_character_estimate"] = sum(
        len(item.title) + len(item.url) + len(item.section) + len(item.passage)
        for item in matches
    )
    return matches, diagnostics


def _default_benchmark_cases() -> list[BenchmarkCase]:
    path = Path(__file__).resolve().parents[2] / "data" / "research_librarian_retrieval_benchmarks_v6.4.1.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return []
    raw_cases = payload.get("cases", []) if isinstance(payload, dict) else []
    output: list[BenchmarkCase] = []
    for raw in raw_cases:
        try:
            output.append(BenchmarkCase.model_validate(raw))
        except (ValueError, TypeError):
            continue
    return output


def _expected_rank(matches: list[RetrievedSource], case: BenchmarkCase) -> int | None:
    expected_title = re.sub(r"\s+", " ", case.expected_title.strip().lower())
    for rank, match in enumerate(matches, start=1):
        if case.expected_record_id and match.id == case.expected_record_id:
            return rank
        if expected_title and re.sub(r"\s+", " ", match.title.strip().lower()) == expected_title:
            return rank
    return None


def _benchmark_metrics(rows: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    ranks = [row.get(mode, {}).get("rank") for row in rows]
    valid_ranks = [int(rank) for rank in ranks if isinstance(rank, int) and rank > 0]
    count = max(1, len(rows))
    return {
        "cases": len(rows),
        "matched": len(valid_ranks),
        "hit_at_1": round(sum(1 for rank in valid_ranks if rank == 1) / count, 4),
        "hit_at_3": round(sum(1 for rank in valid_ranks if rank <= 3) / count, 4),
        "mrr": round(sum(1.0 / rank for rank in valid_ranks) / count, 4),
        "mean_latency_ms": round(sum(float(row.get(mode, {}).get("latency_ms", 0.0)) for row in rows) / count, 3),
        "ambiguous_cases": sum(1 for row in rows if row.get(mode, {}).get("ambiguous")),
        "no_result_cases": sum(1 for row in rows if not row.get(mode, {}).get("result_ids")),
    }


@app.get("/")
def root() -> dict[str, Any]:
    current = _status()
    return {
        "ok": True,
        "service": "Sustainable Catalyst Research Librarian AI",
        "version": __version__,
        "state": current.state,
        "indexed_records": current.indexed_records,
        "startup_state": current.startup_state,
        "startup_progress": current.startup_progress,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "environment": settings.environment, **_startup_snapshot()}


@app.get("/startup")
def startup() -> dict[str, Any]:
    return {"ok": True, "version": __version__, **_startup_snapshot()}


@app.get("/status", response_model=StatusResponse)
def status_endpoint() -> StatusResponse:
    return _status()


@app.post("/v1/knowledge/sync", response_model=SyncResponse, dependencies=[Depends(require_key)])
def sync_knowledge(payload: SyncRequest) -> SyncResponse:
    result = store.sync(
        records=payload.records,
        mode=payload.mode,
        source_site=payload.source_site,
        job_id=payload.job_id,
        batch_index=payload.batch_index,
        batch_count=payload.batch_count,
        deleted_ids=payload.deleted_ids,
        reason=payload.reason,
    )
    summary = result.summary
    return SyncResponse(
        mode=payload.mode,
        state=result.state,
        committed=result.committed,
        received=result.received,
        accepted=result.accepted,
        rejected=result.rejected,
        rejected_records=result.rejected_records,
        inserted=result.inserted,
        updated=result.updated,
        unchanged=result.unchanged,
        deleted=result.deleted,
        staged_records=result.staged_records,
        staged_deletions=result.staged_deletions,
        duplicate_batch=result.duplicate_batch,
        job_id=payload.job_id,
        batch_index=payload.batch_index,
        batch_count=payload.batch_count,
        total_records=int(summary["total_records"]),
        indexed_titles=int(summary["indexed_titles"]),
        index_version=int(summary.get("index_version", 0)),
        checksum=str(summary.get("checksum", "")),
        storage_engine=str(summary.get("storage_engine", "sqlite")),
        last_sync_utc=str(summary.get("last_sync_utc", "")),
        source_site=str(summary.get("source_site", "")),
    )


@app.get("/v1/knowledge/summary", response_model=StatusResponse, dependencies=[Depends(require_key)])
def knowledge_summary() -> StatusResponse:
    return _status()


@app.get("/v1/knowledge/manifest", dependencies=[Depends(require_key)])
def knowledge_manifest() -> dict[str, Any]:
    return {"ok": True, "version": __version__, **store.manifest()}


@app.post("/v1/knowledge/maintenance", dependencies=[Depends(require_key)])
def knowledge_maintenance(payload: MaintenanceRequest) -> dict[str, Any]:
    return {
        "version": __version__,
        **store.repair_stalled_jobs(payload.max_age_seconds, payload.purge_staging),
        "manifest": store.summary(),
    }


@app.get("/v1/knowledge/snapshots", dependencies=[Depends(require_key)])
def knowledge_snapshots() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "snapshots": store.list_snapshots()}


@app.get("/v1/knowledge/snapshots/validate", dependencies=[Depends(require_key)])
def knowledge_validate_snapshots() -> dict[str, Any]:
    return {"version": __version__, **store.validate_snapshots()}


@app.post("/v1/knowledge/rollback", dependencies=[Depends(require_key)])
def knowledge_rollback(payload: RollbackRequest) -> dict[str, Any]:
    try:
        result = store.rollback(payload.snapshot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Runtime index snapshot not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"version": __version__, **result}


@app.get("/v1/knowledge/embeddings/status", dependencies=[Depends(require_key)])
def embedding_status_endpoint() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "enabled": settings.semantic_enabled, **store.embedding_status()}


@app.post("/v1/knowledge/embeddings/process", dependencies=[Depends(require_key)])
async def process_embeddings(payload: EmbeddingProcessRequest) -> dict[str, Any]:
    if not embeddings_configured():
        raise HTTPException(status_code=503, detail="Gemini embeddings are not configured or semantic retrieval is disabled.")
    requested = min(payload.limit, settings.embedding_batch_limit)
    pending = store.pending_chunks(requested, settings.gemini_embedding_model)
    run_id = store.begin_embedding_run(settings.gemini_embedding_model, len(pending))
    processed = 0
    failed = 0
    last_error = ""
    for chunk in pending:
        try:
            vector = await generate_embedding(f"{chunk.heading}\n{chunk.passage}", "RETRIEVAL_DOCUMENT")
            if store.save_chunk_embedding(chunk.chunk_id, settings.gemini_embedding_model, vector):
                processed += 1
            else:
                failed += 1
        except RuntimeError as exc:
            failed += 1
            last_error = str(exc)[:1000]
            # A single provider/quota failure stops this bounded batch. The queue
            # remains resumable because completed chunk embeddings are persisted.
            break
        if payload.delay_ms:
            await asyncio.sleep(payload.delay_ms / 1000.0)
    store.finish_embedding_run(run_id, processed, failed, last_error)
    return {
        "ok": not last_error,
        "version": __version__,
        "run_id": run_id,
        "requested": len(pending),
        "processed": processed,
        "failed": failed,
        "error": last_error,
        **store.embedding_status(),
    }


@app.get("/v1/retrieval/config", dependencies=[Depends(require_key)])
def retrieval_config_endpoint() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "config": store.retrieval_config()}


@app.post("/v1/retrieval/config", dependencies=[Depends(require_key)])
def update_retrieval_config(payload: RetrievalCalibrationUpdate) -> dict[str, Any]:
    config = store.set_retrieval_config(payload.model_dump())
    return {"ok": True, "version": __version__, "config": config}


@app.get("/v1/retrieval/benchmark/history", dependencies=[Depends(require_key)])
def retrieval_benchmark_history() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "runs": store.benchmark_history(10)}


@app.post("/v1/retrieval/benchmark", dependencies=[Depends(require_key)])
async def retrieval_benchmark(payload: BenchmarkRequest) -> dict[str, Any]:
    config = store.retrieval_config()
    cases = payload.cases or _default_benchmark_cases()
    cases = cases[: int(config["limits"]["benchmark_cases"])]
    rows: list[dict[str, Any]] = []
    for case in cases:
        lexical_started = time.perf_counter()
        lexical_matches, lexical_diagnostics = await _hybrid_retrieve(case.query, payload.limit, config, include_semantic=False)
        lexical_latency = (time.perf_counter() - lexical_started) * 1000
        hybrid_started = time.perf_counter()
        hybrid_matches, hybrid_diagnostics = await _hybrid_retrieve(
            case.query, payload.limit, config, include_semantic=payload.include_semantic
        )
        hybrid_latency = (time.perf_counter() - hybrid_started) * 1000
        rows.append(
            {
                "query": case.query,
                "expected_record_id": case.expected_record_id,
                "expected_title": case.expected_title,
                "tags": case.tags,
                "lexical": {
                    "rank": _expected_rank(lexical_matches, case),
                    "result_ids": [item.id for item in lexical_matches],
                    "result_titles": [item.title for item in lexical_matches],
                    "latency_ms": round(lexical_latency, 3),
                    "ambiguous": bool(lexical_diagnostics.get("ambiguous")),
                },
                "hybrid": {
                    "rank": _expected_rank(hybrid_matches, case),
                    "result_ids": [item.id for item in hybrid_matches],
                    "result_titles": [item.title for item in hybrid_matches],
                    "latency_ms": round(hybrid_latency, 3),
                    "ambiguous": bool(hybrid_diagnostics.get("ambiguous")),
                    "semantic_used": bool(hybrid_diagnostics.get("semantic_used")),
                    "semantic_error": hybrid_diagnostics.get("semantic_error", ""),
                },
            }
        )
    report = {
        "ok": True,
        "version": __version__,
        "run_id": "benchmark-" + uuid.uuid4().hex,
        "created_utc": utc_now(),
        "profile": config["profile"],
        "case_count": len(rows),
        "include_semantic": payload.include_semantic,
        "metrics": {
            "lexical": _benchmark_metrics(rows, "lexical"),
            "hybrid": _benchmark_metrics(rows, "hybrid"),
        },
        "cases": rows,
    }
    if payload.persist:
        store.save_benchmark_run(report)
    return report


@app.post("/v1/session/reset", dependencies=[Depends(require_key)])
def reset_session(payload: SessionResetRequest) -> dict[str, Any]:
    session_id = _session_id(payload.session_id)
    removed_turns = len(_sessions.pop(session_id, []))
    return {"ok": True, "version": __version__, "session_id": session_id, "removed_turns": removed_turns}


@app.post("/v1/retrieve", response_model=list[RetrievedSource], dependencies=[Depends(require_key)])
async def retrieve_endpoint(payload: RetrievalRequest) -> list[RetrievedSource]:
    matches, _ = await _hybrid_retrieve(payload.query, payload.limit)
    return matches


@app.post("/v1/retrieve/explain", dependencies=[Depends(require_key)])
async def retrieve_explain_endpoint(payload: RetrievalRequest) -> dict[str, Any]:
    matches, diagnostics = await _hybrid_retrieve(payload.query, payload.limit)
    return {
        "ok": True,
        "version": __version__,
        "query": payload.query,
        "matches": [item.model_dump() for item in matches],
        "evidence": [item.model_dump() for item in evidence_from_matches(matches)],
        "diagnostics": diagnostics,
    }


@app.post("/v1/ask", response_model=AskResponse, dependencies=[Depends(require_key)])
async def ask(payload: AskRequest) -> AskResponse:
    _prune_sessions()
    session_id = _session_id(payload.session_id)
    research_mode = _resolve_research_mode(payload.question, payload.research_mode)
    records = store.records()
    calibration = store.retrieval_config()
    matches, retrieval_diagnostics = await _hybrid_retrieve(payload.question, settings.source_limit, calibration)
    gate = evidence_gate(matches, retrieval_diagnostics, calibration)
    best = matches[0] if matches else None
    related = related_titles(best, records, settings.related_limit, calibration)
    certainty = confidence(matches, retrieval_diagnostics)
    evidence = evidence_from_matches(matches)
    history = [
        {"role": str(turn.get("role", "user")), "content": str(turn.get("content", ""))}
        for turn in _sessions.get(session_id, [])[-settings.max_session_turns :]
    ]

    ai_used = False
    source = "python-hybrid-retrieval"
    provider = ""
    model = ""
    citation_verification: dict[str, Any] = {
        "ok": True,
        "required": settings.citation_required,
        "citation_count": 0,
        "fallback": True,
    }
    try:
        if not matches:
            raise RuntimeError("No grounded Sustainable Catalyst sources were retrieved.")
        if not gate.get("ok"):
            raise RuntimeError("Retrieved evidence did not pass the configured minimum-evidence gate: " + ", ".join(gate.get("reasons", [])))
        route_hint = dict(payload.route_hint or {})
        route_hint["research_mode"] = research_mode
        route_hint["research_mode_label"] = _RESEARCH_MODES[research_mode]["label"]
        route_hint["workspace_instruction"] = _RESEARCH_MODES[research_mode]["instruction"]
        answer = await generate_answer(payload.question, matches, related, history, route_hint, calibration)
        citation_verification = verify_citations(answer, matches, related, calibration)
        if not citation_verification.get("ok"):
            raise RuntimeError("Generated answer failed citation verification.")
        ai_used = True
        source = "python-gemini-citation-verified"
        provider = settings.provider
        model = settings.gemini_model
    except RuntimeError as exc:
        answer = _deterministic_answer(payload.question, matches, related)
        citation_verification = verify_citations(answer, matches, related, calibration)
        citation_verification["fallback"] = True
        citation_verification["fallback_reason"] = str(exc)[:500]

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
        actions=_actions(payload.question, best, research_mode),
        interpretation="Exact-title, BM25, semantic, and reciprocal-rank retrieval followed by citation-verified AI synthesis." if ai_used else "Exact-title and section-aware hybrid retrieval with deterministic verified evidence fallback.",
        clarification=("Which of the similarly titled Sustainable Catalyst records should be prioritized?" if retrieval_diagnostics.get("ambiguous") else ("" if certainty.get("level") != "low" else "Which Sustainable Catalyst subject, title, country, tool, or intended output should the search prioritize?")),
        confidence=certainty,
        evidence=evidence,
        citation_verification=citation_verification,
        retrieval_diagnostics=retrieval_diagnostics,
        evidence_gate=gate,
        research_mode=research_mode,
        follow_up_prompts=_follow_up_prompts(research_mode, best, related),
        workspace=_workspace_summary(research_mode, matches, related, ai_used, gate),
        session_turns=len(_sessions[session_id]) // 2,
        status=_status().model_dump(),
    )
