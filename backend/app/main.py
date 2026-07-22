from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
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
    PlatformHandoffPrepareRequest,
    PlatformHandoffValidateRequest,
    HandoffRetryRequest,
    HandoffTokenRefreshRequest,
    HandoffReceiptRequest,
    GovernancePolicyUpdate,
    SourceReviewRequest,
    QualityEvaluationRequest,
    ReleaseGateRequest,
    RetentionRunRequest,
    ResearchProjectRequest, ResearchInvestigationRequest, ProjectEntityRequest, WorkflowTemplateRequest, ContradictionRequest, UncertaintyRegisterRequest, PlatformBackupImportRequest,
    ArtifactReturnRequest,
    RetrievalCalibrationUpdate,
    RetrievalRequest,
    RetrievedSource,
    RollbackRequest,
    SessionResetRequest,
    StatusResponse,
    SyncRequest,
    SyncResponse,
    SyncReconcileRequest,
    utc_now,
)
from .provider import configured as provider_configured
from .provider import credential_diagnostics, embeddings_configured, generate_embedding, provider_state, verify_citations
from .generation_adapter import adapter_status, generate as generate_answer
from .platform_handoffs import (
    ARTIFACT_SCHEMA,
    HANDOFF_SCHEMA,
    RECEIPT_SCHEMA,
    compatibility_report,
    fingerprint,
    refresh_handoff_delivery,
    validate_receipt,
    available_capabilities,
    prepare_handoff,
    prepare_preview_handoffs,
    public_capabilities,
    validate_artifact_return,
    validate_handoff,
)
from .retrieval import confidence, evidence_from_matches, related_titles, retrieve, retrieve_with_diagnostics
from .governance import build_answer_trace, evaluate_release_gate, public_methodology, sanitize_governance_policy, source_governance
from .store import store
from .platform_v7 import API_SCHEMA, BACKUP_SCHEMA, backup_envelope, contradiction_report, normalize_investigation, normalize_project, uncertainty_register, verify_backup, workflow_template


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
        "schema": "sc-research-librarian-public-workspace/2.0",
        "mode": mode,
        "mode_label": _RESEARCH_MODES.get(mode, _RESEARCH_MODES["auto"])["label"],
        "verified_sources": len(matches),
        "related_titles": len(related),
        "answer_kind": "citation-verified-ai" if ai_used else "deterministic-evidence",
        "evidence_gate_passed": bool(gate.get("ok")),
        "exports": ["copy", "markdown", "json", "print", "research-note"],
        "accessibility_profile": "wcag-focused-v6.5.1",
        "rendering_profile": "staged-v6.5.1",
        "handoff_profile": "cross-product-reliability-v6.6.1",
        "governance_profile": store.governance_policy().get("profile", "public-trust-v7.1.0"),
        "available_destinations": list(available_capabilities().keys()),
        "connected_platform": store.connected_platform_summary(),
        "generation_boundary": adapter_status(),
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


def _idempotency_payload_hash(payload: dict[str, Any]) -> str:
    clean = dict(payload)
    clean.pop("idempotency_key", None)
    clean.pop("created_utc", None)
    return fingerprint(clean)


def _idempotency_event(event_type: str, key: str, payload: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None]:
    event_key = f"{event_type}:{key.strip()}" if key and key.strip() else ""
    payload_hash = _idempotency_payload_hash(payload)
    existing = store.cross_product_event(event_key) if event_key else None
    if existing and existing.get("payload_hash") != payload_hash:
        raise HTTPException(status_code=409, detail="Idempotency key was already used with a different payload.")
    return event_key, payload_hash, existing


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
    capabilities = available_capabilities()
    actions: list[dict[str, str]] = []
    if best:
        actions.append({"label": "Open best match", "url": best.url, "type": "source"})
    if research_mode == "evidence" and best:
        actions.append({"label": "Open cited evidence", "url": best.url, "type": "evidence"})
    if "site_intelligence" in capabilities and any(term in q for term in ["country", "climate", "indicator", "public evidence", "compare countries", "map", "earth observation"]):
        item = capabilities["site_intelligence"]
        actions.append({"label": "Prepare Site Intelligence handoff", "url": item["url"], "type": "site_intelligence", "handoff": "site_intelligence"})
    if "workbench" in capabilities and (research_mode == "analyze" or any(term in q for term in ["calculate", "formula", "graph", "model", "analysis", "simulate", "equation"])):
        item = capabilities["workbench"]
        actions.append({"label": "Prepare Workbench handoff", "url": item["url"], "type": "workbench", "handoff": "workbench"})
    if "lab" in capabilities and any(term in q for term in ["experiment", "hypothesis", "laboratory", "instrument", "spectrometry", "biology", "chemistry", "physics"]):
        item = capabilities["lab"]
        actions.append({"label": "Prepare Lab handoff", "url": item["url"], "type": "lab", "handoff": "lab"})
    if "decision_studio" in capabilities and (research_mode == "decision" or any(term in q for term in ["decision", "brief", "scenario", "tradeoff", "recommendation", "alternative"])):
        item = capabilities["decision_studio"]
        actions.append({"label": "Prepare Decision Studio handoff", "url": item["url"], "type": "decision_studio", "handoff": "decision_studio"})
    if "feature_suggestions" in capabilities:
        item = capabilities["feature_suggestions"]
        actions.append({"label": "Report a missing route", "url": item["url"], "type": "feedback", "handoff": "feature_suggestions"})
    return actions[:6]


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
    capabilities = public_capabilities()
    available_count = sum(1 for item in capabilities if item.get("available"))
    handoff_summary = store.platform_handoff_summary()
    indexed_chunks = int(summary.get("indexed_chunks", 0))
    embedded_chunks = int(summary.get("embedded_chunks", 0))
    pending_chunks = max(0, indexed_chunks - embedded_chunks)
    provider_online = bool(provider_state.last_success_utc) and not (
        provider_state.last_failure_utc
        and provider_state.last_failure_utc > provider_state.last_success_utc
    )
    if startup["startup_state"] == "warming":
        state, label = "backend-warming", "Research service starting"
        recommended_action = "wait-for-backend"
    elif not index_ready and ai_ready:
        state, label = "index-empty", "Gemini connected — build the knowledge index"
        recommended_action = "build-index"
    elif not index_ready:
        state, label = "index-empty", "Build the knowledge index"
        recommended_action = "configure-provider-and-build-index" if not ai_ready else "build-index"
    elif pending_chunks and ai_ready:
        state, label = "indexing", "Knowledge index ready — semantic indexing in progress"
        recommended_action = "continue-embeddings"
    elif ai_ready and provider_online:
        state, label = "online", "Research service online"
        recommended_action = "none"
    elif ai_ready:
        state, label = "ready", "Knowledge index ready — Gemini configured"
        recommended_action = "test-provider"
    else:
        state, label = "retrieval-only", "Knowledge index ready — deterministic retrieval active"
        recommended_action = "configure-provider"
    generation_state = "online" if provider_online else ("configured" if ai_ready else "not-configured")
    index_state = "ready" if index_ready else "empty"
    if not index_ready:
        embedding_state = "waiting-for-index"
    elif indexed_chunks <= 0:
        embedding_state = "not-required"
    elif pending_chunks:
        embedding_state = "pending"
    else:
        embedding_state = "complete"
    readiness_percent = 25
    if ai_ready:
        readiness_percent += 25
    if index_ready:
        readiness_percent += 25
    if index_ready and (indexed_chunks <= 0 or pending_chunks == 0):
        readiness_percent += 25
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
        indexed_chunks=indexed_chunks,
        embedded_chunks=embedded_chunks,
        pending_chunks=pending_chunks,
        generation_state=generation_state,
        index_state=index_state,
        embedding_state=embedding_state,
        recommended_action=recommended_action,
        readiness_percent=readiness_percent,
        semantic_coverage=float(summary.get("semantic_coverage", 0.0)),
        embedding_model=str(summary.get("embedding_model", settings.gemini_embedding_model)),
        retrieval_profile=str(summary.get("retrieval_profile", "balanced-v6.5.0")),
        benchmark_runs=int(summary.get("benchmark_runs", 0)),
        platform_capabilities=len(capabilities),
        available_platform_capabilities=available_count,
        handoff_count=int(handoff_summary.get("handoff_count", 0)),
        artifact_return_count=int(handoff_summary.get("artifact_return_count", 0)),
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
    policy = store.governance_policy()
    matches, source_review = source_governance(matches, records, store.source_review_map(), policy)
    matches = matches[:limit]
    diagnostics["source_governance"] = source_review
    diagnostics["governance_policy_profile"] = policy.get("profile", "")
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
        defer_commit=payload.defer_commit,
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


@app.get("/v1/knowledge/sync/jobs/{job_id}", dependencies=[Depends(require_key)])
def sync_job_status(job_id: str) -> dict[str, Any]:
    return store.sync_job_status(job_id)


@app.delete("/v1/knowledge/sync/jobs/{job_id}", dependencies=[Depends(require_key)])
def reset_sync_job(job_id: str) -> dict[str, Any]:
    return store.reset_sync_job(job_id)


@app.post("/v1/knowledge/sync/jobs/{job_id}/reconcile", dependencies=[Depends(require_key)])
def reconcile_sync_job(job_id: str, payload: SyncReconcileRequest) -> dict[str, Any]:
    """Compare backend transaction state with the WordPress-owned batch manifest."""
    return {
        "ok": True,
        "version": __version__,
        **store.reconcile_sync_job(job_id, payload.expected_batch_count),
        "recovery_generation": payload.recovery_generation,
    }


@app.post("/v1/knowledge/sync/jobs/{job_id}/commit", dependencies=[Depends(require_key)])
def queue_sync_job_commit(job_id: str) -> dict[str, Any]:
    """Initialize or resume the durable incremental activation state machine."""
    try:
        queued = store.queue_sync_commit(job_id, "wordpress-postgres-generation-v7.1.0")
    except ValueError as exc:
        message = str(exc)
        code = status.HTTP_404_NOT_FOUND if "does not exist" in message else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=message) from exc
    return {"ok": True, "version": __version__, **queued}


@app.post("/v1/knowledge/sync/jobs/{job_id}/commit/step", dependencies=[Depends(require_key)])
def advance_sync_job_commit(job_id: str) -> dict[str, Any]:
    """Advance one bounded activation step and persist its cursor before returning."""
    try:
        advanced = store.advance_sync_commit(job_id, "wordpress-postgres-generation-v7.1.0")
    except ValueError as exc:
        message = str(exc)
        code = status.HTTP_404_NOT_FOUND if "does not exist" in message else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"ok": True, "version": __version__, **advanced}


@app.get("/v1/knowledge/summary", response_model=StatusResponse, dependencies=[Depends(require_key)])
def knowledge_summary() -> StatusResponse:
    return _status()




@app.get("/v1/knowledge/database/diagnostics", dependencies=[Depends(require_key)])
def knowledge_database_diagnostics() -> dict[str, Any]:
    diagnostics = getattr(store, "database_diagnostics", None)
    if not callable(diagnostics):
        return {
            "ok": True,
            "version": __version__,
            "backend": "sqlite",
            "storage_engine": store.summary().get("storage_engine", "sqlite"),
            "persistent": bool(store.summary().get("storage_persistent", False)),
        }
    return {"version": __version__, **diagnostics()}

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




@app.get("/v1/provider/diagnostics", dependencies=[Depends(require_key)])
def provider_diagnostics_endpoint() -> dict[str, Any]:
    return {"ok": True, "version": __version__, **credential_diagnostics()}


@app.post("/v1/knowledge/embeddings/test", dependencies=[Depends(require_key)])
async def test_embeddings_endpoint() -> dict[str, Any]:
    if not embeddings_configured():
        raise HTTPException(status_code=503, detail="Gemini embeddings are not configured or semantic retrieval is disabled.")
    try:
        vector = await generate_embedding("Research Librarian v7.1.0 embedding connection test", "RETRIEVAL_DOCUMENT")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Gemini embedding test failed: {str(exc)[:900]}") from exc
    return {
        "ok": True,
        "version": __version__,
        "dimensions": len(vector),
        **credential_diagnostics(),
    }


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


@app.get("/v1/platform/capabilities", dependencies=[Depends(require_key)])
def platform_capabilities_endpoint() -> dict[str, Any]:
    capabilities = public_capabilities()
    return {
        "ok": True,
        "version": __version__,
        "schema": "sc-platform-capabilities/1.1",
        "capabilities": capabilities,
        "available": [item["id"] for item in capabilities if item.get("available")],
        "compatibility": compatibility_report(),
        "summary": store.platform_handoff_summary(),
    }


@app.get("/v1/platform/compatibility", dependencies=[Depends(require_key)])
def platform_compatibility_endpoint() -> dict[str, Any]:
    return {"ok": True, "version": __version__, **compatibility_report()}


@app.post("/v1/handoffs/prepare", dependencies=[Depends(require_key)])
async def platform_handoff_prepare(payload: PlatformHandoffPrepareRequest) -> dict[str, Any]:
    request_payload = payload.model_dump()
    event_key, payload_hash, existing = _idempotency_event("handoff-prepare", payload.idempotency_key, request_payload)
    if existing:
        response = dict(existing["response"])
        response["duplicate_event"] = True
        return response
    matches, diagnostics = await _hybrid_retrieve(payload.question, settings.handoff_source_limit)
    if payload.source_ids:
        wanted = set(payload.source_ids)
        matches = [item for item in matches if item.id in wanted]
    evidence = evidence_from_matches(matches)
    try:
        handoff = prepare_handoff(payload.destination, payload.question, payload.research_mode, _session_id(payload.session_id), matches, evidence, payload.assumptions, payload.uncertainties, payload.route_hint, payload.idempotency_key)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if payload.persist:
        store.save_platform_handoff(handoff)
    response = {"ok": bool(handoff.get("validation", {}).get("ok")), "version": __version__, "handoff": handoff, "retrieval_diagnostics": diagnostics, "duplicate_event": False}
    if event_key:
        store.save_cross_product_event(event_key, "handoff-prepare", payload_hash, response, settings.handoff_event_ttl_seconds)
    return response


@app.post("/v1/handoffs/validate", dependencies=[Depends(require_key)])
def platform_handoff_validate(payload: PlatformHandoffValidateRequest) -> dict[str, Any]:
    return {"version": __version__, **validate_handoff(payload.payload)}


@app.post("/v1/handoffs/retry", dependencies=[Depends(require_key)])
def platform_handoff_retry(payload: HandoffRetryRequest) -> dict[str, Any]:
    request_payload = payload.model_dump()
    event_key, payload_hash, existing = _idempotency_event("handoff-retry", payload.idempotency_key, request_payload)
    if existing:
        response = dict(existing["response"])
        response["duplicate_event"] = True
        return response
    original = store.platform_handoff(payload.handoff_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Original handoff was not found.")
    try:
        refreshed = refresh_handoff_delivery(original, payload.reason, increment_attempt=True)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    attempt = int((refreshed.get("delivery") or {}).get("attempt") or 0)
    delay = min(3600, settings.handoff_retry_base_seconds * (2 ** max(0, attempt - 1)))
    refreshed.setdefault("delivery", {})["next_retry_utc"] = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
    refreshed["delivery"]["last_error"] = payload.reason
    refreshed.pop("validation", None)
    copy = json.loads(json.dumps(refreshed))
    copy.setdefault("provenance", {}).pop("payload_fingerprint", None)
    refreshed.setdefault("provenance", {})["payload_fingerprint"] = fingerprint(copy)
    refreshed["validation"] = validate_handoff(refreshed)
    store.save_platform_handoff(refreshed)
    response = {"ok": True, "version": __version__, "handoff": refreshed, "retry": {"attempt": attempt, "delay_seconds": delay, "next_retry_utc": refreshed["delivery"]["next_retry_utc"]}, "duplicate_event": False}
    if event_key:
        store.save_cross_product_event(event_key, "handoff-retry", payload_hash, response, settings.handoff_event_ttl_seconds)
    return response


@app.post("/v1/handoffs/token/refresh", dependencies=[Depends(require_key)])
def platform_handoff_token_refresh(payload: HandoffTokenRefreshRequest) -> dict[str, Any]:
    original = store.platform_handoff(payload.handoff_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Original handoff was not found.")
    try:
        refreshed = refresh_handoff_delivery(original, payload.reason, increment_attempt=False)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    store.save_platform_handoff(refreshed)
    return {"ok": True, "version": __version__, "handoff": refreshed, "token": refreshed.get("delivery", {})}


@app.post("/v1/handoffs/receipts", dependencies=[Depends(require_key)])
def platform_handoff_receipt(payload: HandoffReceiptRequest) -> dict[str, Any]:
    receipt = payload.model_dump(by_alias=True)
    event_key, payload_hash, existing = _idempotency_event("handoff-receipt", payload.idempotency_key or payload.receipt_id, receipt)
    if existing:
        response = dict(existing["response"])
        response["duplicate_event"] = True
        return response
    original = store.platform_handoff(payload.handoff_id)
    validation = validate_receipt(receipt, original)
    if not validation.get("ok"):
        raise HTTPException(status_code=409, detail=validation)
    try:
        stored = store.save_handoff_receipt(receipt)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    response = {"ok": True, "version": __version__, "schema": RECEIPT_SCHEMA, "validation": validation, "receipt": stored, "duplicate_event": bool(stored.get("duplicate_event"))}
    if event_key:
        store.save_cross_product_event(event_key, "handoff-receipt", payload_hash, response, settings.handoff_event_ttl_seconds)
    return response


@app.get("/v1/handoffs/logs", dependencies=[Depends(require_key)])
def platform_handoff_logs(limit: int = 50) -> dict[str, Any]:
    return {"ok": True, "version": __version__, "schema": HANDOFF_SCHEMA, "summary": store.platform_handoff_summary(), "handoffs": store.platform_handoffs(limit), "receipts": store.handoff_receipts(limit)}


@app.post("/v1/handoffs/artifacts/return", dependencies=[Depends(require_key)])
def platform_artifact_return(payload: ArtifactReturnRequest) -> dict[str, Any]:
    artifact = payload.model_dump(by_alias=True)
    event_key, payload_hash, existing = _idempotency_event("artifact-return", payload.idempotency_key or payload.artifact_id, artifact)
    if existing:
        response = dict(existing["response"])
        response["duplicate_event"] = True
        return response
    original = store.platform_handoff(payload.handoff_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Original handoff was not found.")
    validation = validate_artifact_return(artifact, original)
    if not validation.get("ok"):
        raise HTTPException(status_code=409, detail=validation)
    artifact.setdefault("provenance", {})["research_librarian_handoff_fingerprint"] = (original.get("provenance") or {}).get("payload_fingerprint", "")
    artifact["provenance"]["artifact_fingerprint"] = validation["artifact_fingerprint"]
    artifact["provenance"]["chain"] = list((original.get("provenance") or {}).get("chain", [])) + ["destination_artifact", "research_librarian_return"]
    try:
        stored = store.save_artifact_return(artifact, "accepted")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    response = {"ok": True, "version": __version__, "schema": ARTIFACT_SCHEMA, "validation": validation, "artifact": stored, "duplicate_event": bool(stored.get("duplicate_event"))}
    if event_key:
        store.save_cross_product_event(event_key, "artifact-return", payload_hash, response, settings.handoff_event_ttl_seconds)
    return response


@app.get("/v1/handoffs/artifacts", dependencies=[Depends(require_key)])
def platform_artifact_returns(limit: int = 50) -> dict[str, Any]:
    return {"ok": True, "version": __version__, "schema": ARTIFACT_SCHEMA, "summary": store.platform_handoff_summary(), "artifacts": store.artifact_returns(limit)}


@app.get("/v1/governance/policy", dependencies=[Depends(require_key)])
def governance_policy_endpoint() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "policy": store.governance_policy()}


@app.post("/v1/governance/policy", dependencies=[Depends(require_key)])
def governance_policy_update(payload: GovernancePolicyUpdate) -> dict[str, Any]:
    if not payload.reviewer:
        raise HTTPException(status_code=409, detail="A human reviewer is required for governance policy changes.")
    policy = store.save_governance_policy(payload.policy, payload.reviewer, payload.reason)
    return {"ok": True, "version": __version__, "policy": policy}


@app.get("/v1/governance/sources", dependencies=[Depends(require_key)])
def governance_sources(limit: int = 200) -> dict[str, Any]:
    return {"ok": True, "version": __version__, "schema": "sc-research-source-review/1.0", "reviews": store.source_reviews(limit)}


@app.post("/v1/governance/sources", dependencies=[Depends(require_key)])
def governance_source_review(payload: SourceReviewRequest) -> dict[str, Any]:
    if payload.state == "excluded" and not payload.reviewer:
        raise HTTPException(status_code=409, detail="A human reviewer is required to exclude a source.")
    try:
        review = store.save_source_review(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "version": __version__, "review": review}


@app.get("/v1/governance/traces", dependencies=[Depends(require_key)])
def governance_traces(limit: int = 50) -> dict[str, Any]:
    return {"ok": True, "version": __version__, "schema": "sc-research-answer-trace/1.0", "traces": store.answer_traces(limit)}


@app.get("/v1/governance/traces/{trace_id}", dependencies=[Depends(require_key)])
def governance_trace(trace_id: str) -> dict[str, Any]:
    trace = store.answer_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Answer trace not found.")
    return {"ok": True, "version": __version__, "trace": trace}


@app.post("/v1/governance/evaluate", dependencies=[Depends(require_key)])
def governance_evaluate(payload: QualityEvaluationRequest) -> dict[str, Any]:
    evaluation = {
        "schema": "sc-research-quality-evaluation/1.0",
        "trace_id": payload.trace_id,
        "metrics": payload.metrics,
        "quality_score": float(payload.metrics.get("quality_score") or 0),
        "reviewer": payload.reviewer,
        "note": payload.note,
    }
    return {"ok": True, "version": __version__, "evaluation": store.save_quality_evaluation(evaluation)}


@app.get("/v1/governance/metrics", dependencies=[Depends(require_key)])
def governance_metrics() -> dict[str, Any]:
    return {"ok": True, "version": __version__, **store.governance_metrics()}


@app.post("/v1/governance/release-gate", dependencies=[Depends(require_key)])
def governance_release_gate(payload: ReleaseGateRequest) -> dict[str, Any]:
    if payload.override and not payload.reviewer:
        raise HTTPException(status_code=409, detail="A named human reviewer is required for a release-gate override.")
    metrics = payload.metrics or store.governance_metrics().get("metrics", {})
    report = evaluate_release_gate(metrics, store.governance_policy(), payload.release_version or __version__, payload.override, payload.reviewer)
    if payload.persist:
        store.save_release_gate(report)
    return {"ok": report["decision"] in {"pass", "human-override"}, "version": __version__, "report": report}


@app.get("/v1/governance/release-gate/history", dependencies=[Depends(require_key)])
def governance_release_gate_history(limit: int = 20) -> dict[str, Any]:
    return {"ok": True, "version": __version__, "schema": "sc-research-release-gate/1.0", "runs": store.release_gate_history(limit)}


@app.post("/v1/governance/retention/run", dependencies=[Depends(require_key)])
def governance_retention_run(payload: RetentionRunRequest) -> dict[str, Any]:
    return {"version": __version__, **store.governance_retention(payload.dry_run)}


@app.get("/v1/governance/methodology")
def governance_methodology() -> dict[str, Any]:
    return {"ok": True, "version": __version__, "methodology": public_methodology(store.governance_policy())}


@app.get("/v1/governance/export", dependencies=[Depends(require_key)])
def governance_export() -> dict[str, Any]:
    return {
        "ok": True,
        "version": __version__,
        "schema": "sc-research-governance-export/1.0",
        "policy": store.governance_policy(),
        "source_reviews": store.source_reviews(500),
        "recent_traces": store.answer_traces(100),
        "quality_evaluations": store.quality_evaluations(100),
        "quality_metrics": store.governance_metrics(),
        "release_gates": store.release_gate_history(50),
        "events": store.governance_events(100),
        "generated_utc": utc_now(),
    }


@app.get("/v1/platform/api", dependencies=[Depends(require_key)])
def connected_api_manifest() -> dict[str, Any]:
    return {"schema": API_SCHEMA, "version": __version__, "stability": "stable-v7", "resources": ["projects", "investigations", "entities", "workflows", "contradictions", "uncertainties", "backups", "handoffs", "artifacts"], "generation_boundary": adapter_status()}

@app.get("/v1/platform/summary", dependencies=[Depends(require_key)])
def connected_platform_summary() -> dict[str, Any]:
    return store.connected_platform_summary()

@app.get("/v1/projects", dependencies=[Depends(require_key)])
def list_projects(limit: int = 100, owner_ref: str = "") -> dict[str, Any]:
    return {"schema":"sc-research-project-list/1.0","projects":store.research_projects(limit, owner_ref),"summary":store.connected_platform_summary()}

@app.post("/v1/projects", dependencies=[Depends(require_key)])
def save_project(payload: ResearchProjectRequest) -> dict[str, Any]:
    existing=store.research_project(payload.project_id) if payload.project_id else None
    project=normalize_project(payload.model_dump(),existing)
    store.save_research_project(project); store.save_project_event(project["project_id"],"project-saved",{"fingerprint":project["fingerprint"]})
    return project

@app.get("/v1/projects/{project_id}", dependencies=[Depends(require_key)])
def get_project(project_id: str) -> dict[str, Any]:
    try: return {"schema":"sc-research-project-bundle/1.0",**store.project_bundle(project_id)}
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@app.post("/v1/investigations", dependencies=[Depends(require_key)])
def save_investigation(payload: ResearchInvestigationRequest) -> dict[str, Any]:
    existing=next((x for x in store.research_investigations(payload.project_id,500) if x.get("investigation_id")==payload.investigation_id),None) if payload.investigation_id else None
    inv=normalize_investigation(payload.model_dump(),payload.project_id,existing)
    try: store.save_research_investigation(inv)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    store.save_project_event(payload.project_id,"investigation-saved",{"investigation_id":inv["investigation_id"],"fingerprint":inv["fingerprint"]})
    return inv

@app.post("/v1/projects/entities", dependencies=[Depends(require_key)])
def save_project_entity(payload: ProjectEntityRequest) -> dict[str, Any]:
    try: return store.save_project_entity(payload.model_dump())
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@app.get("/v1/projects/{project_id}/entities", dependencies=[Depends(require_key)])
def list_project_entities(project_id: str, entity_type: str = "", limit: int = 500) -> dict[str, Any]:
    return {"schema":"sc-project-entity-list/1.0","project_id":project_id,"entities":store.project_entities(project_id,entity_type,limit)}

@app.post("/v1/workflows/template", dependencies=[Depends(require_key)])
def create_workflow(payload: WorkflowTemplateRequest) -> dict[str, Any]:
    workflow=workflow_template(payload.kind,payload.title)
    workflow.update({"project_id":payload.project_id,"investigation_id":payload.investigation_id})
    if payload.persist and payload.project_id:
        try: workflow=store.save_project_entity({"project_id":payload.project_id,"entity_id":workflow["workflow_id"],"entity_type":"workflow","title":workflow["title"],"payload":workflow})
        except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    return workflow

@app.post("/v1/research/contradictions", dependencies=[Depends(require_key)])
def analyze_contradictions(payload: ContradictionRequest) -> dict[str, Any]:
    report=contradiction_report(payload.items)
    if payload.persist and payload.project_id: store.save_project_entity({"project_id":payload.project_id,"entity_type":"contradiction-report","title":"Contradiction report","payload":report})
    return report

@app.post("/v1/research/uncertainties", dependencies=[Depends(require_key)])
def build_uncertainties(payload: UncertaintyRegisterRequest) -> dict[str, Any]:
    register=uncertainty_register(payload.items)
    if payload.persist and payload.project_id: store.save_project_entity({"project_id":payload.project_id,"entity_type":"uncertainty-register","title":"Uncertainty register","payload":register})
    return register

@app.post("/v1/projects/{project_id}/backup", dependencies=[Depends(require_key)])
def export_project_backup(project_id: str) -> dict[str, Any]:
    try: envelope=backup_envelope(store.project_bundle(project_id))
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    return store.save_connected_backup(envelope)

@app.get("/v1/platform/backups", dependencies=[Depends(require_key)])
def list_platform_backups(limit: int = 20) -> dict[str, Any]:
    return {"schema":"sc-connected-research-backup-list/1.0","backups":store.connected_backups(limit)}

@app.post("/v1/platform/backups/import", dependencies=[Depends(require_key)])
def import_platform_backup(payload: PlatformBackupImportRequest) -> dict[str, Any]:
    verification=verify_backup(payload.envelope)
    if not verification["ok"]: raise HTTPException(status_code=422,detail="Backup checksum validation failed.")
    body=payload.envelope.get("payload") or {}; project=body.get("project") or {}
    result={"ok":True,"dry_run":payload.dry_run,"verification":verification,"counts":{"investigations":len(body.get("investigations") or []),"entities":len(body.get("entities") or [])}}
    if not payload.dry_run:
        saved=normalize_project(project,store.research_project(str(project.get("project_id") or "")))
        store.save_research_project(saved)
        for item in body.get("investigations") or []: store.save_research_investigation(normalize_investigation(item,saved["project_id"],item))
        for item in body.get("entities") or []: store.save_project_entity({**item,"project_id":saved["project_id"]})
        result["project_id"]=saved["project_id"]
    return result

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
    capabilities = public_capabilities()
    typed_handoffs = prepare_preview_handoffs(
        payload.question,
        research_mode,
        session_id,
        matches,
        evidence,
        payload.route_hint,
    )
    summary = store.summary()
    policy = store.governance_policy()
    trace = build_answer_trace(
        query=payload.question,
        answer=answer,
        session_id=session_id,
        policy=policy,
        model=model,
        provider=provider,
        ai_used=ai_used,
        source=source,
        research_mode=research_mode,
        matches=matches,
        citation_verification=citation_verification,
        evidence_gate=gate,
        retrieval_diagnostics=retrieval_diagnostics,
        index_version=int(summary.get("index_version", 0)),
        index_checksum=str(summary.get("checksum", "")),
        retrieval_profile=str(summary.get("retrieval_profile", "")),
    )
    store.save_answer_trace(trace)
    provenance = {
        "schema": "sc-research-provenance/1.1",
        "index_version": int(store.summary().get("index_version", 0)),
        "index_checksum": str(store.summary().get("checksum", "")),
        "source_record_ids": [item.id for item in matches],
        "citation_labels": [item.citation_label for item in matches if item.citation_label],
        "handoff_ids": [item.get("handoff_id", "") for item in typed_handoffs],
        "answer_trace_id": trace["trace_id"],
        "answer_trace_fingerprint": trace["trace_fingerprint"],
        "quality": trace["quality"],
        "governance_policy_profile": policy.get("profile", ""),
        "chain": ["question", "hybrid_retrieval", "governance_evaluation", "verified_answer", "typed_handoff_preview"],
    }

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
        capabilities=capabilities,
        typed_handoffs=typed_handoffs,
        provenance=provenance,
        status=_status().model_dump(),
    )
