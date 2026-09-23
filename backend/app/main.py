from __future__ import annotations

from collections import defaultdict
from contextlib import asynccontextmanager
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
    ResearchProjectRequest, ResearchInvestigationRequest, ProjectEntityRequest, LibraryObjectRequest, ResearchContextRequest, ResearchRoomRequest, ResearchRoomMemberRequest, ResearchRoomEvidenceStateRequest, ResearchRoomQuestionRequest, ResearchRoomDisagreementRequest, ResearchRoomActivityRequest, SourceEvaluationRequest, EvidenceComparisonRequest, EvidenceGapRequest, ResearchActivityRequest, ResearchObjectStateRequest, ResearchOpenQuestionRequest, FederatedSearchRequest, FederatedResultSaveRequest, WorkspacePromotionPrepareRequest, WorkspacePromotionReceiptRequest, ResearchLifecycleRequest, ResearchLifecycleTransitionRequest, ResearchLifecycleCheckpointRequest, WorkflowTemplateRequest, ContradictionRequest, UncertaintyRegisterRequest, PlatformBackupImportRequest,
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
from .advanced_retrieval import ADVANCED_RETRIEVAL_SCHEMA, build_query_plan, advanced_retrieve_with_diagnostics
from .governance import build_answer_trace, evaluate_release_gate, public_methodology, sanitize_governance_policy, source_governance
from .store import store
from .platform_v7 import API_SCHEMA, BACKUP_SCHEMA, backup_envelope, contradiction_report, normalize_investigation, normalize_project, uncertainty_register, verify_backup, workflow_template
from .library_context import (
    LIBRARY_OBJECT_MODEL_SCHEMA,
    object_model_manifest,
    normalize_library_object,
    normalize_research_context,
    resolve_research_context,
    sanitize_inline_context,
)
from .evidence_quality import (
    SOURCE_EVALUATION_SCHEMA,
    EVIDENCE_COMPARISON_SCHEMA,
    EVIDENCE_GAP_SCHEMA,
    QUALITY_SIGNALS_SCHEMA,
    evaluate_source,
    compare_sources,
    evidence_gaps,
    quality_summary,
)
from .research_state import (
    RESEARCH_ACTIVITY_SCHEMA,
    RESEARCH_OBJECT_STATE_SCHEMA,
    OPEN_QUESTION_SCHEMA,
    RESEARCH_STATE_SUMMARY_SCHEMA,
    normalize_activity,
    normalize_object_state,
    normalize_open_question,
    summarize_research_state,
    prompt_research_state,
)
from .collaboration import (
    ROOM_SCHEMA,
    ROOM_MEMBER_SCHEMA,
    ROOM_EVIDENCE_STATE_SCHEMA,
    ROOM_QUESTION_SCHEMA,
    ROOM_DISAGREEMENT_SCHEMA,
    ROOM_ACTIVITY_SCHEMA,
    ROOM_SYNTHESIS_SCHEMA,
    ROOM_PROMPT_SCHEMA,
    normalize_room,
    normalize_member,
    normalize_room_evidence_state,
    normalize_room_question,
    normalize_room_disagreement,
    normalize_room_activity,
    build_room_synthesis,
    prompt_room_synthesis,
)

from .federated_discovery import (
    FEDERATED_PROVIDER_CATALOG_SCHEMA,
    FEDERATED_SEARCH_SCHEMA,
    FEDERATED_RESULT_SCHEMA,
    FEDERATED_IMPORT_SCHEMA,
    FEDERATED_SEARCH_SUMMARY_SCHEMA,
    provider_catalog,
    run_federated_search,
    normalize_search_record,
    search_summary,
    result_to_library_payload,
)

from .workspace_promotion import (
    PROMOTION_SCHEMA,
    PROMOTION_PACKET_SCHEMA,
    PROMOTION_SUMMARY_SCHEMA,
    PROMOTION_RECEIPT_SCHEMA,
    WORKSPACE_IMPORT_CONTRACT,
    artifact_catalog,
    build_workspace_packet,
    normalize_promotion,
    apply_promotion_receipt,
    promotion_summary,
)

from .research_lifecycle import (
    LIFECYCLE_SCHEMA,
    LIFECYCLE_CATALOG_SCHEMA,
    LIFECYCLE_SUMMARY_SCHEMA,
    LIFECYCLE_EVENT_SCHEMA,
    LIFECYCLE_CHECKPOINT_SCHEMA,
    lifecycle_catalog,
    normalize_lifecycle,
    normalize_lifecycle_event,
    transition_lifecycle,
    build_checkpoint,
    evaluate_lifecycle,
)


from .api.core import router as platform_core_router
from .api.jobs import router as async_jobs_router, register_authenticated_routes as register_async_job_routes
from .api.documents import router as documents_router, register_authenticated_routes as register_document_routes
from .api.sources import router as sources_router, register_authenticated_routes as register_source_routes
from .workers.document_worker import worker as document_worker


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    document_worker.start()
    try:
        yield
    finally:
        document_worker.stop()


app = FastAPI(
    title="Sustainable Catalyst Research Librarian AI",
    version=__version__,
    description="Python knowledge intelligence, title-aware retrieval, and grounded AI guidance for Sustainable Catalyst.",
    lifespan=_lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=900)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-SC-RL-Key"],
)
app.include_router(platform_core_router)

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


def _prioritize_context_matches(matches: list[RetrievedSource], context: dict[str, Any], limit: int) -> tuple[list[RetrievedSource], dict[str, Any]]:
    source_ids = []
    for item in context.get("objects", []) if isinstance(context, dict) else []:
        if not isinstance(item, dict):
            continue
        record_id = str(item.get("source_record_id") or "")
        if record_id and record_id not in source_ids:
            source_ids.append(record_id)
    source_set = set(source_ids)
    if not source_set:
        return matches[:limit], {"enabled": bool(context), "source_record_ids": 0, "prioritized_matches": 0}
    prioritized = [item for item in matches if item.id in source_set]
    remaining = [item for item in matches if item.id not in source_set]
    return (prioritized + remaining)[:limit], {
        "enabled": True,
        "source_record_ids": len(source_ids),
        "prioritized_matches": len(prioritized),
        "candidate_matches": len(matches),
    }


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
        "schema": "sc-research-librarian-public-workspace/3.0",
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
        "governance_profile": store.governance_policy().get("profile", "public-trust-v7.1.2"),
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


# v8.3 registers the durable async job API only after the shared backend-key
# dependency exists, keeping the same trust boundary as knowledge sync and Core writes.
register_async_job_routes(require_key)
app.include_router(async_jobs_router)
register_document_routes(require_key)
app.include_router(documents_router)
register_source_routes(require_key)
app.include_router(sources_router)


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
        semantic_retrieval=("advanced-multi-query+bm25+semantic+rrf+rerank" if float(summary.get("semantic_coverage", 0)) > 0 else "advanced-multi-query+bm25+rrf+rerank"),
        last_sync_utc=str(summary.get("last_sync_utc", "")),
        source_site=str(summary.get("source_site", "")),
        storage_engine=str(summary.get("storage_engine", "sqlite")),
        database_backend=str(summary.get("database_backend", settings.database_backend)),
        database_ready=bool(summary.get("database_ready", True)),
        database_identity_match=bool(summary.get("database_identity_match", True)),
        database_fingerprint=str(summary.get("database_fingerprint", "")),
        active_generation_id=str(summary.get("active_generation_id", "")),
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
    *,
    filters: dict[str, Any] | None = None,
    advanced_enabled: bool = True,
    max_queries: int | None = None,
    candidate_pool: int | None = None,
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

    if advanced_enabled:
        matches, diagnostics = advanced_retrieve_with_diagnostics(
            query, records, chunks, limit, query_embedding, config, filters,
            advanced_enabled=True,
            max_queries_override=max_queries,
            candidate_pool_override=candidate_pool,
        )
    else:
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
    summary = store.summary()
    database_ready = bool(summary.get("database_ready", True))
    identity_match = bool(summary.get("database_identity_match", True))
    return {
        "ok": database_ready and identity_match,
        "version": __version__,
        "environment": settings.environment,
        "database_backend": str(summary.get("database_backend", settings.database_backend)),
        "database_ready": database_ready,
        "database_identity_match": identity_match,
        "database_fingerprint": str(summary.get("database_fingerprint", "")),
        **_startup_snapshot(summary),
    }


@app.get("/startup")
def startup() -> dict[str, Any]:
    summary = store.summary()
    return {
        "ok": bool(summary.get("database_ready", True)) and bool(summary.get("database_identity_match", True)),
        "version": __version__,
        "database_backend": str(summary.get("database_backend", settings.database_backend)),
        "database_ready": bool(summary.get("database_ready", True)),
        "database_identity_match": bool(summary.get("database_identity_match", True)),
        **_startup_snapshot(summary),
    }


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
        queued = store.queue_sync_commit(job_id, "wordpress-postgres-generation-v7.1.2")
    except ValueError as exc:
        message = str(exc)
        code = status.HTTP_404_NOT_FOUND if "does not exist" in message else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=message) from exc
    return {"ok": True, "version": __version__, **queued}


@app.post("/v1/knowledge/sync/jobs/{job_id}/commit/step", dependencies=[Depends(require_key)])
def advance_sync_job_commit(job_id: str) -> dict[str, Any]:
    """Advance one bounded activation step and persist its cursor before returning."""
    try:
        advanced = store.advance_sync_commit(job_id, "wordpress-postgres-generation-v7.1.2")
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


@app.get("/v1/knowledge/database/identity", dependencies=[Depends(require_key)])
def knowledge_database_identity() -> dict[str, Any]:
    identity = getattr(store, "database_identity", None)
    if not callable(identity):
        summary = store.summary()
        return {
            "ok": True,
            "version": __version__,
            "backend": "sqlite",
            "effective_backend": "sqlite",
            "database_ready": True,
            "identity_match": True,
            "storage_engine": summary.get("storage_engine", "sqlite"),
        }
    return {"version": __version__, **identity()}


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
        vector = await generate_embedding("Research Librarian v7.1.2 embedding connection test", "RETRIEVAL_DOCUMENT")
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



def _resolve_quality_objects(object_ids: list[str], inline_objects: list[dict[str, Any]], limit: int = 200) -> list[dict[str, Any]]:
    """Resolve persisted Library objects plus bounded inline objects for quality analysis."""
    objects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for object_id in object_ids[:limit]:
        clean_id = str(object_id or "").strip()[:220]
        if not clean_id or clean_id in seen:
            continue
        item = store.library_object(clean_id)
        if item:
            objects.append(item)
            seen.add(clean_id)
    for item in inline_objects[:limit]:
        if not isinstance(item, dict):
            continue
        clean = normalize_library_object(item, item) if item.get("object_id") else normalize_library_object(item)
        object_id = str(clean.get("object_id") or "")
        if object_id in seen:
            continue
        objects.append(clean)
        seen.add(object_id)
        if len(objects) >= limit:
            break
    return objects[:limit]


def _persist_quality_report(project_id: str, entity_type: str, title: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    clean_project_id = str(project_id or "").strip()[:220]
    if not clean_project_id:
        return None
    if not store.research_project(clean_project_id):
        raise HTTPException(status_code=404, detail="Unknown research project.")
    snapshot = json.loads(json.dumps(payload, ensure_ascii=False, default=str))
    return store.save_project_entity({
        "project_id": clean_project_id,
        "entity_type": entity_type,
        "title": title,
        "payload": snapshot,
    })

def _research_state_scope(owner_ref: str = "", project_id: str = "", context_id: str = "") -> tuple[str, str, str]:
    owner = str(owner_ref or "")[:220]
    project = str(project_id or "")[:220]
    context = str(context_id or "")[:220]
    if context:
        saved = store.research_context(context)
        if saved:
            owner = owner or str(saved.get("owner_ref") or "")[:220]
            project = project or str(saved.get("project_id") or "")[:220]
    if project and not owner:
        saved_project = store.research_project(project)
        if saved_project:
            owner = str(saved_project.get("owner_ref") or "")[:220]
    return owner, project, context


def _research_state_summary(owner_ref: str = "", project_id: str = "", context_id: str = "") -> dict[str, Any]:
    owner, project, context = _research_state_scope(owner_ref, project_id, context_id)
    activities = store.research_activities(1000, owner, project, context)
    object_states = store.research_object_states(1000, owner, project, context)
    enriched_states = []
    tracked_object_ids: set[str] = set()
    for state in object_states:
        item = dict(state)
        object_id = str(item.get("object_id") or "")
        if object_id:
            tracked_object_ids.add(object_id)
        library_object = store.library_object(object_id) if object_id else None
        if library_object:
            item["object_title"] = str(library_object.get("title") or "")[:500]
            item["object_type"] = str(library_object.get("object_type") or "")[:80]
            item["source_scope"] = str(library_object.get("source_scope") or "")[:80]
        enriched_states.append(item)
    # A context object with no explicit ledger row is visibly unread rather than disappearing
    # from the review queue. This is a derived display state; it is not persisted until the
    # researcher takes an explicit reading/review action.
    if context:
        try:
            resolution = resolve_saved_research_context(context)
            for library_object in list(resolution.get("objects") or [])[:200]:
                object_id = str(library_object.get("object_id") or "")
                if not object_id or object_id in tracked_object_ids:
                    continue
                enriched_states.append({
                    "schema": RESEARCH_OBJECT_STATE_SCHEMA,
                    "state_id": "",
                    "owner_ref": owner,
                    "project_id": project,
                    "context_id": context,
                    "object_id": object_id,
                    "object_title": str(library_object.get("title") or "")[:500],
                    "object_type": str(library_object.get("object_type") or "")[:80],
                    "source_scope": str(library_object.get("source_scope") or "")[:80],
                    "reading_state": "unread",
                    "contradiction_state": "none",
                    "derived_unread": True,
                    "governance": {"derived_display_state": True, "not_evidence": True},
                })
        except HTTPException:
            pass
    questions = store.research_open_questions(1000, owner, project, context)
    return summarize_research_state(activities, enriched_states, questions, owner_ref=owner, project_id=project, context_id=context)


@app.get("/v1/platform/api", dependencies=[Depends(require_key)])
def connected_api_manifest() -> dict[str, Any]:
    return {"schema": API_SCHEMA, "version": __version__, "stability": "stable-v8", "resources": ["projects", "investigations", "entities", "library-objects", "research-contexts", "research-rooms", "room-members", "room-evidence", "room-questions", "room-disagreements", "room-synthesis", "source-evaluations", "evidence-comparisons", "evidence-gaps", "research-state", "research-activity", "object-review-state", "open-questions", "workflows", "contradictions", "uncertainties", "backups", "handoffs", "artifacts", "federated-providers", "federated-search", "federated-history", "federated-library-import", "workspace-promotions", "research-lifecycles", "lifecycle-transitions", "lifecycle-checkpoints", "async-jobs", "document-processing-jobs", "advanced-retrieval", "document-intelligence", "source-identity", "core-evidence-bridge"], "object_model": object_model_manifest(), "evidence_quality": {"source_evaluation_schema": SOURCE_EVALUATION_SCHEMA, "comparison_schema": EVIDENCE_COMPARISON_SCHEMA, "gap_schema": EVIDENCE_GAP_SCHEMA, "quality_signals_schema": QUALITY_SIGNALS_SCHEMA, "truth_score": False}, "research_state": {"summary_schema": RESEARCH_STATE_SUMMARY_SCHEMA, "activity_schema": RESEARCH_ACTIVITY_SCHEMA, "object_state_schema": RESEARCH_OBJECT_STATE_SCHEMA, "open_question_schema": OPEN_QUESTION_SCHEMA, "workflow_memory_only": True, "not_evidence": True}, "research_rooms": {"room_schema": ROOM_SCHEMA, "member_schema": ROOM_MEMBER_SCHEMA, "evidence_state_schema": ROOM_EVIDENCE_STATE_SCHEMA, "question_schema": ROOM_QUESTION_SCHEMA, "disagreement_schema": ROOM_DISAGREEMENT_SCHEMA, "activity_schema": ROOM_ACTIVITY_SCHEMA, "synthesis_schema": ROOM_SYNTHESIS_SCHEMA, "prompt_schema": ROOM_PROMPT_SCHEMA, "participant_attribution": True, "individual_shared_state_separate": True, "not_evidence": True}, "federated_discovery": {"provider_catalog_schema": FEDERATED_PROVIDER_CATALOG_SCHEMA, "search_schema": FEDERATED_SEARCH_SCHEMA, "result_schema": FEDERATED_RESULT_SCHEMA, "import_schema": FEDERATED_IMPORT_SCHEMA, "external_discovery_only": True, "explicit_library_save_required": True}, "workspace_promotions": {"promotion_schema": PROMOTION_SCHEMA, "packet_schema": PROMOTION_PACKET_SCHEMA, "receipt_schema": PROMOTION_RECEIPT_SCHEMA, "workspace_import_contract": WORKSPACE_IMPORT_CONTRACT, "artifact_types": artifact_catalog(), "explicit_import_required": True}, "research_lifecycle": {"lifecycle_schema": LIFECYCLE_SCHEMA, "summary_schema": LIFECYCLE_SUMMARY_SCHEMA, "event_schema": LIFECYCLE_EVENT_SCHEMA, "checkpoint_schema": LIFECYCLE_CHECKPOINT_SCHEMA, "catalog": lifecycle_catalog(), "human_confirmed_transitions": True, "automatic_stage_advancement": False, "not_evidence": True}, "generation_boundary": adapter_status()}

@app.get("/v1/platform/summary", dependencies=[Depends(require_key)])
def connected_platform_summary() -> dict[str, Any]:
    return store.connected_platform_summary()


@app.get("/v1/library/object-model", dependencies=[Depends(require_key)])
def library_object_model() -> dict[str, Any]:
    return {"ok": True, "version": __version__, **object_model_manifest()}


@app.get("/v1/library/objects", dependencies=[Depends(require_key)])
def list_library_objects(limit: int = 200, owner_ref: str = "", object_type: str = "", source_scope: str = "") -> dict[str, Any]:
    return {
        "schema": "sc-research-library-object-list/1.0",
        "objects": store.library_objects(limit, owner_ref, object_type, source_scope),
        "object_model_schema": LIBRARY_OBJECT_MODEL_SCHEMA,
    }


@app.post("/v1/library/objects", dependencies=[Depends(require_key)])
def save_library_object(payload: LibraryObjectRequest) -> dict[str, Any]:
    existing = store.library_object(payload.object_id) if payload.object_id else None
    try:
        clean = normalize_library_object(payload.model_dump(), existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return store.save_library_object(clean)


@app.get("/v1/library/objects/{object_id}", dependencies=[Depends(require_key)])
def get_library_object(object_id: str) -> dict[str, Any]:
    item = store.library_object(object_id)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown Library object.")
    return item


@app.post("/v1/library/objects/{object_id}/projects/{project_id}", dependencies=[Depends(require_key)])
def link_library_object_to_project(object_id: str, project_id: str) -> dict[str, Any]:
    item = store.library_object(object_id)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown Library object.")
    if not store.research_project(project_id):
        raise HTTPException(status_code=404, detail="Unknown research project.")
    relationship = store.save_project_entity({
        "project_id": project_id,
        "entity_type": "library-object-ref",
        "title": str(item.get("title") or "Library object"),
        "payload": {
            "library_object_id": object_id,
            "object_type": str(item.get("object_type") or "source"),
            "source_scope": str(item.get("source_scope") or "my-library"),
            "object_fingerprint": str(item.get("fingerprint") or ""),
        },
    })
    return {"ok": True, "version": __version__, "library_object": item, "project_link": relationship}


@app.get("/v1/projects/{project_id}/library-objects", dependencies=[Depends(require_key)])
def project_library_objects(project_id: str) -> dict[str, Any]:
    try:
        bundle = store.project_bundle(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"schema": "sc-project-library-object-list/1.0", "project_id": project_id, "objects": bundle.get("library_objects", [])}



def _require_room_member(room_id: str, member_ref: str, *, write: bool = False, manage: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    room = store.research_room(str(room_id or ""))
    if not room:
        raise HTTPException(status_code=404, detail="Unknown Research Room.")
    member = store.room_member(str(room_id or ""), str(member_ref or ""))
    if not member or str(member.get("status") or "") != "active":
        raise HTTPException(status_code=403, detail="Active Research Room membership is required.")
    role = str(member.get("role") or "viewer")
    if manage and role not in {"owner", "editor"}:
        raise HTTPException(status_code=403, detail="Research Room owner or editor role is required.")
    if write and role not in {"owner", "editor", "researcher"}:
        raise HTTPException(status_code=403, detail="This Research Room role is read-only.")
    return room, member


def _room_synthesis(room_id: str) -> dict[str, Any]:
    room = store.research_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Unknown Research Room.")
    return build_room_synthesis(
        room,
        store.room_members(room_id, 500),
        store.room_evidence_states(room_id, 1000),
        store.room_questions(room_id, 500),
        store.room_disagreements(room_id, 500),
        store.room_activities(room_id, 1000),
        store.library_objects_for_room(room_id, 1000),
    )


@app.get("/v1/research/rooms", dependencies=[Depends(require_key)])
def list_research_rooms(limit: int = 100, member_ref: str = "", owner_ref: str = "") -> dict[str, Any]:
    rooms = store.research_rooms(limit, member_ref, owner_ref)
    return {"schema": "sc-research-room-list/1.0", "rooms": rooms, "count": len(rooms)}


@app.post("/v1/research/rooms", dependencies=[Depends(require_key)])
def save_research_room(payload: ResearchRoomRequest) -> dict[str, Any]:
    existing = store.research_room(payload.room_id) if payload.room_id else None
    actor_ref = payload.actor_ref or payload.owner_ref
    payload_data = payload.model_dump()
    if existing:
        _require_room_member(str(existing.get("room_id") or ""), actor_ref, manage=True)
        # Room ownership is not silently transferable through a generic update.
        payload_data["owner_ref"] = str(existing.get("owner_ref") or payload.owner_ref)
    try:
        room = normalize_room(payload_data, existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_research_room(room)
    if not existing:
        member = normalize_member({"room_id": room["room_id"], "member_ref": room["owner_ref"], "role": "owner", "status": "active", "added_by_ref": room["owner_ref"]})
        store.save_room_member(member)
        store.save_room_activity(normalize_room_activity({"room_id": room["room_id"], "actor_ref": room["owner_ref"], "event_type": "room-created", "metadata": {"room_fingerprint": room["fingerprint"]}}))
    else:
        store.save_room_activity(normalize_room_activity({"room_id": room["room_id"], "actor_ref": actor_ref, "event_type": "room-updated", "metadata": {"room_fingerprint": room["fingerprint"]}}))
    return stored


@app.get("/v1/research/rooms/{room_id}", dependencies=[Depends(require_key)])
def get_research_room(room_id: str, member_ref: str = "") -> dict[str, Any]:
    room = store.research_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Unknown Research Room.")
    if member_ref:
        _require_room_member(room_id, member_ref)
    return {"schema": "sc-research-room-bundle/1.0", "room": room, "members": store.room_members(room_id, 500), "synthesis": _room_synthesis(room_id)}


@app.get("/v1/research/rooms/{room_id}/members", dependencies=[Depends(require_key)])
def list_room_members(room_id: str, member_ref: str = "") -> dict[str, Any]:
    if member_ref:
        _require_room_member(room_id, member_ref)
    elif not store.research_room(room_id):
        raise HTTPException(status_code=404, detail="Unknown Research Room.")
    return {"schema": "sc-research-room-member-list/1.0", "room_id": room_id, "members": store.room_members(room_id, 500)}


@app.post("/v1/research/rooms/{room_id}/members", dependencies=[Depends(require_key)])
def save_room_member(room_id: str, payload: ResearchRoomMemberRequest) -> dict[str, Any]:
    room, actor = _require_room_member(room_id, payload.added_by_ref, manage=True)
    if payload.room_id != room_id:
        raise HTTPException(status_code=422, detail="Research Room path and payload room_id must match.")
    existing = store.room_member(room_id, payload.member_ref)
    requested_role = str(payload.role or "researcher").lower()
    if requested_role == "owner" and str(actor.get("role") or "") != "owner":
        raise HTTPException(status_code=403, detail="Only the Research Room owner can assign the owner role.")
    try:
        member = normalize_member(payload.model_dump(), existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_room_member(member)
    event_type = "member-added" if not existing else ("member-removed" if member["status"] == "removed" else "member-role-changed")
    store.save_room_activity(normalize_room_activity({"room_id": room_id, "actor_ref": payload.added_by_ref, "event_type": event_type, "metadata": {"member_ref": member["member_ref"], "role": member["role"], "status": member["status"]}}))
    return stored


@app.get("/v1/research/rooms/{room_id}/evidence", dependencies=[Depends(require_key)])
def list_room_evidence(room_id: str, member_ref: str = "", state: str = "") -> dict[str, Any]:
    if member_ref:
        _require_room_member(room_id, member_ref)
    states = store.room_evidence_states(room_id, 1000, state)
    objects = {str(item.get("object_id") or ""): item for item in store.library_objects_for_room(room_id, 1000)}
    rows = []
    for shared in states:
        row = dict(shared)
        obj = objects.get(str(row.get("object_id") or ""))
        if obj:
            row["library_object"] = obj
        rows.append(row)
    return {"schema": "sc-research-room-evidence-list/1.0", "room_id": room_id, "evidence": rows}


@app.post("/v1/research/rooms/{room_id}/evidence", dependencies=[Depends(require_key)])
def save_room_evidence(room_id: str, payload: ResearchRoomEvidenceStateRequest) -> dict[str, Any]:
    _require_room_member(room_id, payload.contributed_by_ref, write=True)
    if payload.room_id != room_id:
        raise HTTPException(status_code=422, detail="Research Room path and payload room_id must match.")
    item = store.library_object(payload.object_id)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown Library object.")
    relationships = dict(item.get("relationships") or {})
    room_ids = list(relationships.get("room_ids") or [])
    if room_id not in room_ids:
        room_ids.append(room_id)
    relationships["room_ids"] = room_ids[:100]
    item = normalize_library_object({**item, "relationships": relationships}, item)
    store.save_library_object(item)
    existing = store.room_evidence_state(room_id, payload.object_id)
    try:
        shared = normalize_room_evidence_state(payload.model_dump(), existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_room_evidence_state(shared)
    event_type = "evidence-added" if not existing else "evidence-state-changed"
    store.save_room_activity(normalize_room_activity({"room_id": room_id, "actor_ref": payload.contributed_by_ref, "event_type": event_type, "object_id": payload.object_id, "metadata": {"state": stored["state"], "source_scope": item.get("source_scope", "")}}))
    return {"schema": ROOM_EVIDENCE_STATE_SCHEMA, "evidence_state": stored, "library_object": item}


@app.get("/v1/research/rooms/{room_id}/questions", dependencies=[Depends(require_key)])
def list_room_questions(room_id: str, member_ref: str = "", status: str = "") -> dict[str, Any]:
    if member_ref:
        _require_room_member(room_id, member_ref)
    return {"schema": "sc-research-room-question-list/1.0", "room_id": room_id, "questions": store.room_questions(room_id, 500, status)}


@app.post("/v1/research/rooms/{room_id}/questions", dependencies=[Depends(require_key)])
def save_room_question(room_id: str, payload: ResearchRoomQuestionRequest) -> dict[str, Any]:
    actor_ref = payload.resolved_by_ref or payload.created_by_ref
    actor = _require_room_member(room_id, actor_ref, write=True)
    if payload.room_id != room_id:
        raise HTTPException(status_code=422, detail="Research Room path and payload room_id must match.")
    existing = store.room_question(payload.question_id) if payload.question_id else None
    if existing and str(existing.get("room_id") or "") != room_id:
        raise HTTPException(status_code=404, detail="Room question does not belong to this Research Room.")
    requested_status = str(payload.status or (existing or {}).get("status") or "open").lower()
    prior_status = str((existing or {}).get("status") or "")
    if existing and requested_status != prior_status and requested_status in {"resolved", "deferred", "dismissed"}:
        creator_ref = str(existing.get("created_by_ref") or "")
        if actor_ref != creator_ref and str(actor.get("role") or "") not in {"owner", "editor"}:
            raise HTTPException(status_code=403, detail="Only the question creator or a Research Room owner/editor can change the question disposition.")
    question_payload = payload.model_dump()
    if existing:
        question_payload["created_by_ref"] = str(existing.get("created_by_ref") or payload.created_by_ref)
    try:
        question = normalize_room_question(question_payload, existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_room_question(question)
    prior = str((existing or {}).get("status") or "")
    event_type = "question-opened" if stored["status"] == "open" and prior != "open" else ("question-resolved" if stored["status"] == "resolved" and prior != "resolved" else ("question-deferred" if stored["status"] == "deferred" and prior != "deferred" else "note"))
    store.save_room_activity(normalize_room_activity({"room_id": room_id, "actor_ref": actor_ref, "event_type": event_type, "question_id": stored["question_id"], "note": stored["question"][:1000]}))
    return stored


@app.get("/v1/research/rooms/{room_id}/disagreements", dependencies=[Depends(require_key)])
def list_room_disagreements(room_id: str, member_ref: str = "", status: str = "") -> dict[str, Any]:
    if member_ref:
        _require_room_member(room_id, member_ref)
    return {"schema": "sc-research-room-disagreement-list/1.0", "room_id": room_id, "disagreements": store.room_disagreements(room_id, 500, status)}


@app.post("/v1/research/rooms/{room_id}/disagreements", dependencies=[Depends(require_key)])
def save_room_disagreement(room_id: str, payload: ResearchRoomDisagreementRequest) -> dict[str, Any]:
    actor_ref = payload.resolved_by_ref or payload.created_by_ref
    actor = _require_room_member(room_id, actor_ref, write=True)
    if payload.room_id != room_id:
        raise HTTPException(status_code=422, detail="Research Room path and payload room_id must match.")
    existing = store.room_disagreement(payload.disagreement_id) if payload.disagreement_id else None
    if existing and str(existing.get("room_id") or "") != room_id:
        raise HTTPException(status_code=404, detail="Disagreement does not belong to this Research Room.")
    requested_status = str(payload.status or (existing or {}).get("status") or "open").lower()
    prior_status = str((existing or {}).get("status") or "")
    if existing and requested_status != prior_status and requested_status == "resolved" and str(actor.get("role") or "") not in {"owner", "editor"}:
        raise HTTPException(status_code=403, detail="Only a Research Room owner/editor can resolve a disagreement.")

    incoming_positions = []
    for position in payload.positions:
        participant_ref = str(position.get("participant_ref") or "")
        if participant_ref and participant_ref != actor_ref:
            raise HTTPException(status_code=403, detail="Participants may submit only their own attributed disagreement position.")
        if participant_ref:
            incoming_positions.append(dict(position))

    merged_positions = list((existing or {}).get("positions") or [])
    for position in incoming_positions:
        participant_ref = str(position.get("participant_ref") or "")
        merged_positions = [item for item in merged_positions if str(item.get("participant_ref") or "") != participant_ref]
        merged_positions.append(position)

    payload_data = payload.model_dump()
    if existing:
        payload_data["created_by_ref"] = str(existing.get("created_by_ref") or payload.created_by_ref)
    if existing or incoming_positions:
        payload_data["positions"] = merged_positions
    try:
        disagreement = normalize_room_disagreement(payload_data, existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_room_disagreement(disagreement)
    prior = str((existing or {}).get("status") or "")
    event_type = "disagreement-resolved" if stored["status"] == "resolved" and prior != "resolved" else ("disagreement-raised" if not existing else "disagreement-position-added")
    store.save_room_activity(normalize_room_activity({"room_id": room_id, "actor_ref": actor_ref, "event_type": event_type, "disagreement_id": stored["disagreement_id"], "note": stored["statement"][:1000]}))
    return stored


@app.get("/v1/research/rooms/{room_id}/activity", dependencies=[Depends(require_key)])
def list_room_activity(room_id: str, member_ref: str = "", limit: int = 500) -> dict[str, Any]:
    if member_ref:
        _require_room_member(room_id, member_ref)
    return {"schema": "sc-research-room-activity-list/1.0", "room_id": room_id, "activities": store.room_activities(room_id, limit)}


@app.post("/v1/research/rooms/{room_id}/activity", dependencies=[Depends(require_key)])
def save_room_activity(room_id: str, payload: ResearchRoomActivityRequest) -> dict[str, Any]:
    _require_room_member(room_id, payload.actor_ref, write=True)
    if payload.room_id != room_id:
        raise HTTPException(status_code=422, detail="Research Room path and payload room_id must match.")
    try:
        event = normalize_room_activity(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return store.save_room_activity(event)


@app.get("/v1/research/rooms/{room_id}/synthesis", dependencies=[Depends(require_key)])
def research_room_synthesis(room_id: str, member_ref: str = "") -> dict[str, Any]:
    if member_ref:
        _require_room_member(room_id, member_ref)
    synthesis = _room_synthesis(room_id)
    return {**synthesis, "prompt_context": prompt_room_synthesis(synthesis)}


@app.get("/v1/research/contexts", dependencies=[Depends(require_key)])
def list_research_contexts(limit: int = 100, owner_ref: str = "") -> dict[str, Any]:
    return {
        "schema": "sc-research-context-list/1.0",
        "contexts": store.research_contexts(limit, owner_ref),
        "active": store.active_research_context(owner_ref) if owner_ref else None,
    }


@app.post("/v1/research/contexts", dependencies=[Depends(require_key)])
def save_research_context(payload: ResearchContextRequest) -> dict[str, Any]:
    existing = store.research_context(payload.context_id) if payload.context_id else None
    if payload.room_id:
        _require_room_member(payload.room_id, payload.owner_ref)
    try:
        context = normalize_research_context(payload.model_dump(), existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return store.save_research_context(context)


@app.get("/v1/research/contexts/{context_id}", dependencies=[Depends(require_key)])
def get_research_context(context_id: str) -> dict[str, Any]:
    context = store.research_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Unknown research context.")
    return context


@app.get("/v1/research/contexts/{context_id}/resolve", dependencies=[Depends(require_key)])
def resolve_saved_research_context(context_id: str) -> dict[str, Any]:
    context = store.research_context(context_id)
    if not context:
        raise HTTPException(status_code=404, detail="Unknown research context.")
    owner_ref = str(context.get("owner_ref") or "")
    library_objects = store.library_objects(1000, owner_ref) if owner_ref else store.library_objects(1000)
    room_id = str(context.get("room_id") or "")
    if room_id:
        _require_room_member(room_id, owner_ref)
        room_objects = store.library_objects_for_room(room_id, 1000)
        known = {str(item.get("object_id") or "") for item in library_objects}
        library_objects.extend(item for item in room_objects if str(item.get("object_id") or "") not in known)
    project_id = str(context.get("project_id") or "")
    project = store.research_project(project_id) if project_id else None
    project_entities = store.project_entities(project_id, "", 1000) if project_id and project else []
    resolution = resolve_research_context(context, library_objects, project_entities, project)
    if room_id:
        synthesis = _room_synthesis(room_id)
        room_prompt = prompt_room_synthesis(synthesis)
        resolution["room_collaboration"] = synthesis
        resolution["prompt_context"]["room_collaboration"] = room_prompt
        resolution["fingerprint"] = fingerprint({key: value for key, value in resolution.items() if key not in {"fingerprint", "resolved_utc", "objects"}})
    return resolution


@app.get("/v1/research/contexts/{context_id}/evidence-quality", dependencies=[Depends(require_key)])
def research_context_evidence_quality(context_id: str) -> dict[str, Any]:
    resolution = resolve_saved_research_context(context_id)
    sources = list(resolution.get("objects") or [])[:200]
    summary = quality_summary(sources)
    comparison = compare_sources(sources)
    gaps = evidence_gaps(sources)
    return {
        "schema": QUALITY_SIGNALS_SCHEMA,
        "version": __version__,
        "context": resolution.get("context", {}),
        "source_count": len(sources),
        "summary": summary,
        "comparison": comparison,
        "gaps": gaps,
    }


@app.post("/v1/research/sources/evaluate", dependencies=[Depends(require_key)])
def evaluate_research_sources(payload: SourceEvaluationRequest) -> dict[str, Any]:
    sources = _resolve_quality_objects(payload.object_ids, payload.objects, 200)
    evaluations = [evaluate_source(item) for item in sources]
    report = {
        "schema": "sc-source-evaluation-set/1.0",
        "version": __version__,
        "question": payload.question,
        "source_count": len(evaluations),
        "evaluations": evaluations,
        "summary": quality_summary(sources, payload.question),
        "governance": {"descriptive_only": True, "truth_score": False, "human_judgment_required": True},
    }
    if payload.persist and payload.project_id:
        report["project_entity"] = _persist_quality_report(payload.project_id, "source-evaluation-set", "Source evaluation set", report)
    return report


@app.post("/v1/research/evidence/compare", dependencies=[Depends(require_key)])
def compare_research_evidence(payload: EvidenceComparisonRequest) -> dict[str, Any]:
    sources = _resolve_quality_objects(payload.object_ids, payload.objects, 100)
    report = compare_sources(sources, payload.question)
    if payload.persist and payload.project_id:
        report["project_entity"] = _persist_quality_report(payload.project_id, "evidence-comparison", "Evidence comparison", report)
    return report


@app.post("/v1/research/evidence/gaps", dependencies=[Depends(require_key)])
def find_research_evidence_gaps(payload: EvidenceGapRequest) -> dict[str, Any]:
    sources = _resolve_quality_objects(payload.object_ids, payload.objects, 200)
    report = evidence_gaps(sources, payload.question)
    if payload.persist and payload.project_id:
        report["project_entity"] = _persist_quality_report(payload.project_id, "evidence-gap-report", "Evidence gap report", report)
    return report

@app.get("/v1/research/state/summary", dependencies=[Depends(require_key)])
def research_state_summary(owner_ref: str = "", project_id: str = "", context_id: str = "") -> dict[str, Any]:
    return _research_state_summary(owner_ref, project_id, context_id)


@app.get("/v1/research/activity", dependencies=[Depends(require_key)])
def list_research_activity(limit: int = 200, owner_ref: str = "", project_id: str = "", context_id: str = "", event_type: str = "") -> dict[str, Any]:
    owner, project, context = _research_state_scope(owner_ref, project_id, context_id)
    return {"schema": "sc-research-activity-list/1.0", "activities": store.research_activities(limit, owner, project, context, event_type)}


@app.post("/v1/research/activity", dependencies=[Depends(require_key)])
def save_research_activity(payload: ResearchActivityRequest) -> dict[str, Any]:
    owner, project, context = _research_state_scope(payload.owner_ref, payload.project_id, payload.context_id)
    try:
        event = normalize_activity({**payload.model_dump(), "owner_ref": owner, "project_id": project, "context_id": context})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return store.save_research_activity(event)


@app.get("/v1/research/object-states", dependencies=[Depends(require_key)])
def list_research_object_states(limit: int = 500, owner_ref: str = "", project_id: str = "", context_id: str = "", reading_state: str = "") -> dict[str, Any]:
    owner, project, context = _research_state_scope(owner_ref, project_id, context_id)
    return {"schema": "sc-research-object-state-list/1.0", "states": store.research_object_states(limit, owner, project, context, reading_state)}


@app.post("/v1/research/object-states", dependencies=[Depends(require_key)])
def save_research_object_state(payload: ResearchObjectStateRequest) -> dict[str, Any]:
    owner, project, context = _research_state_scope(payload.owner_ref, payload.project_id, payload.context_id)
    existing = store.research_object_state(owner, payload.object_id, project, context)
    try:
        state = normalize_object_state({**payload.model_dump(), "owner_ref": owner, "project_id": project, "context_id": context}, existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_research_object_state(state)
    event_type = "review" if state["reading_state"] == "reviewed" else ("reject" if state["reading_state"] == "rejected" else ("read" if state["reading_state"] == "reading" else "open"))
    store.save_research_activity(normalize_activity({"owner_ref": owner, "project_id": project, "context_id": context, "object_id": state["object_id"], "event_type": event_type, "metadata": {"reading_state": state["reading_state"], "contradiction_state": state["contradiction_state"]}}))
    if state["contradiction_state"] == "flagged":
        store.save_research_activity(normalize_activity({"owner_ref": owner, "project_id": project, "context_id": context, "object_id": state["object_id"], "event_type": "contradiction-flagged"}))
    elif existing and str(existing.get("contradiction_state") or "") == "flagged" and state["contradiction_state"] == "resolved":
        store.save_research_activity(normalize_activity({"owner_ref": owner, "project_id": project, "context_id": context, "object_id": state["object_id"], "event_type": "contradiction-resolved"}))
    return stored


@app.get("/v1/research/questions", dependencies=[Depends(require_key)])
def list_research_questions(limit: int = 200, owner_ref: str = "", project_id: str = "", context_id: str = "", status: str = "") -> dict[str, Any]:
    owner, project, context = _research_state_scope(owner_ref, project_id, context_id)
    return {"schema": "sc-research-open-question-list/1.0", "questions": store.research_open_questions(limit, owner, project, context, status)}


@app.post("/v1/research/questions", dependencies=[Depends(require_key)])
def save_research_question(payload: ResearchOpenQuestionRequest) -> dict[str, Any]:
    owner, project, context = _research_state_scope(payload.owner_ref, payload.project_id, payload.context_id)
    existing = store.research_open_question(payload.question_id) if payload.question_id else None
    try:
        question = normalize_open_question({**payload.model_dump(), "owner_ref": owner, "project_id": project, "context_id": context}, existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_research_open_question(question)
    prior_status = str((existing or {}).get("status") or "")
    event_type = "question-opened" if question["status"] == "open" and prior_status != "open" else ("question-resolved" if question["status"] == "resolved" and prior_status != "resolved" else ("question-deferred" if question["status"] == "deferred" and prior_status != "deferred" else "note"))
    store.save_research_activity(normalize_activity({"owner_ref": owner, "project_id": project, "context_id": context, "event_type": event_type, "note": question["question"], "metadata": {"question_id": question["question_id"], "status": question["status"]}}))
    return stored




@app.get("/v1/federation/providers", dependencies=[Depends(require_key)])
def federated_provider_catalog() -> dict[str, Any]:
    return {"ok": True, "version": __version__, **provider_catalog()}


@app.get("/v1/federation/searches", dependencies=[Depends(require_key)])
def list_federated_searches(limit: int = 100, owner_ref: str = "", project_id: str = "", context_id: str = "") -> dict[str, Any]:
    searches = store.federated_searches(limit, owner_ref, project_id, context_id)
    return {"schema": FEDERATED_SEARCH_SUMMARY_SCHEMA, "version": __version__, "summary": search_summary(searches), "searches": searches}


@app.get("/v1/federation/searches/{search_id}", dependencies=[Depends(require_key)])
def get_federated_search(search_id: str, owner_ref: str = "") -> dict[str, Any]:
    search = store.federated_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Unknown federated search.")
    if owner_ref and str(search.get("owner_ref") or "") != owner_ref:
        raise HTTPException(status_code=403, detail="Federated search does not belong to this owner.")
    return search


@app.post("/v1/federation/search", dependencies=[Depends(require_key)])
async def search_federated_research(payload: FederatedSearchRequest) -> dict[str, Any]:
    if not settings.federated_discovery_enabled:
        raise HTTPException(status_code=503, detail="Federated research discovery is disabled.")
    if payload.project_id:
        project = store.research_project(payload.project_id)
        if not project or str(project.get("owner_ref") or "") != payload.owner_ref:
            raise HTTPException(status_code=403, detail="Federated search owner does not own this research project.")
    resolved_project_id = payload.project_id
    if payload.context_id:
        context = store.research_context(payload.context_id)
        if not context or str(context.get("owner_ref") or "") != payload.owner_ref:
            raise HTTPException(status_code=403, detail="Federated search owner does not own this research context.")
        if not resolved_project_id:
            resolved_project_id = str(context.get("project_id") or "")
    if resolved_project_id and resolved_project_id != payload.project_id:
        project = store.research_project(resolved_project_id)
        if not project or str(project.get("owner_ref") or "") != payload.owner_ref:
            raise HTTPException(status_code=403, detail="Federated search context references a project this owner cannot use.")
    try:
        result = await run_federated_search(
            query=payload.query,
            provider_ids=payload.providers or None,
            limit_per_provider=min(payload.limit_per_provider, settings.federated_provider_result_limit),
            result_limit=min(payload.result_limit, settings.federated_result_limit),
            timeout_seconds=settings.federated_timeout_seconds,
            openalex_api_key=settings.openalex_api_key,
            contact_email=settings.federated_contact_email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_federated_search(normalize_search_record(result, owner_ref=payload.owner_ref, project_id=resolved_project_id, context_id=payload.context_id))
    store.save_research_activity(normalize_activity({"owner_ref": payload.owner_ref, "project_id": resolved_project_id, "context_id": payload.context_id, "event_type": "federated-search", "query": payload.query, "note": f"Federated discovery across {len(stored.get('providers') or [])} provider(s)", "metadata": {"search_id": stored["search_id"], "status": stored.get("status"), "result_count": stored.get("result_count"), "providers": stored.get("providers")}}))
    if resolved_project_id:
        store.save_project_event(resolved_project_id, "federated-search", {"search_id": stored["search_id"], "query": payload.query, "result_count": stored.get("result_count"), "providers": stored.get("providers")}, payload.owner_ref)
    return stored


@app.post("/v1/federation/searches/{search_id}/results/{result_id}/save", dependencies=[Depends(require_key)])
def save_federated_result(search_id: str, result_id: str, payload: FederatedResultSaveRequest) -> dict[str, Any]:
    search = store.federated_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Unknown federated search.")
    if str(search.get("owner_ref") or "") != payload.owner_ref:
        raise HTTPException(status_code=403, detail="Federated search does not belong to this owner.")
    resolved_project_id = payload.project_id
    if payload.context_id:
        context = store.research_context(payload.context_id)
        if not context or str(context.get("owner_ref") or "") != payload.owner_ref:
            raise HTTPException(status_code=403, detail="Federated import owner does not own this research context.")
        if not resolved_project_id:
            resolved_project_id = str(context.get("project_id") or "")
    if resolved_project_id:
        project = store.research_project(resolved_project_id)
        if not project or str(project.get("owner_ref") or "") != payload.owner_ref:
            raise HTTPException(status_code=403, detail="Federated import owner does not own this research project.")
    result = next((item for item in list(search.get("results") or []) if isinstance(item, dict) and str(item.get("result_id") or "") == result_id), None)
    if not result:
        raise HTTPException(status_code=404, detail="Federated result is not present in this saved search snapshot.")
    try:
        library_object = normalize_library_object(result_to_library_payload(result, owner_ref=payload.owner_ref, project_id=resolved_project_id, tags=payload.tags))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_library_object(library_object)
    relationship = None
    if resolved_project_id:
        relationship = store.save_project_entity({"project_id": resolved_project_id, "entity_type": "library-object-ref", "title": stored["title"], "payload": {"library_object_id": stored["object_id"], "object_type": stored["object_type"], "source_scope": stored["source_scope"], "source": "federated-discovery", "federated_search_id": search_id, "federated_result_id": result_id}})
    store.save_research_activity(normalize_activity({"owner_ref": payload.owner_ref, "project_id": resolved_project_id, "context_id": payload.context_id, "object_id": stored["object_id"], "event_type": "federated-result-saved", "note": stored["title"], "metadata": {"search_id": search_id, "result_id": result_id, "providers": result.get("providers"), "source_scope": "external-reference"}}))
    return {"schema": FEDERATED_IMPORT_SCHEMA, "version": __version__, "library_object": stored, "project_link": relationship, "governance": {"source_scope": "external-reference", "not_editorial_approval": True, "not_truth_judgment": True, "provider_identity_preserved": True}}


def _workspace_promotion_scope(payload: WorkspacePromotionPrepareRequest) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Resolve only research material the promotion owner can legitimately export."""
    owner_ref = str(payload.owner_ref or "")[:220]
    project = store.research_project(payload.project_id) if payload.project_id else None
    if payload.project_id and not project:
        raise HTTPException(status_code=404, detail="Unknown research project.")
    if project and str(project.get("owner_ref") or "") != owner_ref:
        raise HTTPException(status_code=403, detail="Workspace promotion owner does not own this research project.")

    context = store.research_context(payload.context_id) if payload.context_id else None
    if payload.context_id and not context:
        raise HTTPException(status_code=404, detail="Unknown research context.")
    if context and str(context.get("owner_ref") or "") != owner_ref:
        raise HTTPException(status_code=403, detail="Workspace promotion owner does not own this research context.")

    room_id = str(payload.room_id or (context or {}).get("room_id") or "")[:220]
    room = None
    if room_id:
        room, _ = _require_room_member(room_id, owner_ref)

    project_id = str(payload.project_id or (context or {}).get("project_id") or (room or {}).get("project_id") or "")[:220]
    if project_id and not project:
        project = store.research_project(project_id)
        if project and str(project.get("owner_ref") or "") != owner_ref and not room_id:
            raise HTTPException(status_code=403, detail="Workspace promotion owner does not own this research project.")

    if context:
        resolution = resolve_saved_research_context(str(context.get("context_id") or ""))
        sources = list(resolution.get("objects") or [])[:500]
    elif room_id:
        sources = store.library_objects_for_room(room_id, 1000)[:500]
    elif project_id:
        try:
            sources = list(store.project_bundle(project_id).get("library_objects") or [])[:500]
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    else:
        sources = store.library_objects(500, owner_ref)

    research_state = _research_state_summary(owner_ref, project_id, str((context or {}).get("context_id") or ""))
    quality = {
        "schema": QUALITY_SIGNALS_SCHEMA,
        "summary": quality_summary(sources),
        "comparison": compare_sources(sources),
        "gaps": evidence_gaps(sources),
        "governance": {"descriptive_only": True, "truth_score": False},
    }
    room_synthesis = _room_synthesis(room_id) if room_id else {}
    return project, context, room, sources, research_state, quality, room_synthesis


@app.get("/v1/workspace/promotions/catalog", dependencies=[Depends(require_key)])
def workspace_promotion_catalog() -> dict[str, Any]:
    return {"schema": "sc-workspace-artifact-catalog/1.0", "version": __version__, "workspace_import_contract": WORKSPACE_IMPORT_CONTRACT, "artifact_types": artifact_catalog(), "governance": {"explicit_import_required": True, "promotion_is_not_publication": True}}


@app.get("/v1/workspace/promotions", dependencies=[Depends(require_key)])
def list_workspace_promotions(limit: int = 200, owner_ref: str = "", project_id: str = "", context_id: str = "", room_id: str = "", status: str = "") -> dict[str, Any]:
    promotions = store.workspace_promotions(limit, owner_ref, project_id, context_id, room_id, status)
    return {"schema": PROMOTION_SUMMARY_SCHEMA, "version": __version__, "summary": promotion_summary(promotions), "promotions": promotions}


@app.get("/v1/workspace/promotions/{promotion_id}", dependencies=[Depends(require_key)])
def get_workspace_promotion(promotion_id: str, owner_ref: str = "") -> dict[str, Any]:
    promotion = store.workspace_promotion(promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Unknown Workspace promotion.")
    if owner_ref and str(promotion.get("owner_ref") or "") != owner_ref:
        raise HTTPException(status_code=403, detail="Workspace promotion does not belong to this owner.")
    return promotion


@app.post("/v1/workspace/promotions/prepare", dependencies=[Depends(require_key)])
def prepare_workspace_promotion(payload: WorkspacePromotionPrepareRequest) -> dict[str, Any]:
    project, context, room, sources, research_state, quality, room_synthesis = _workspace_promotion_scope(payload)
    promotion_id = str(payload.promotion_id or "")[:220]
    existing = store.workspace_promotion(promotion_id) if promotion_id else None
    if existing and str(existing.get("owner_ref") or "") != payload.owner_ref:
        raise HTTPException(status_code=403, detail="Workspace promotion does not belong to this owner.")
    try:
        packet = build_workspace_packet(
            artifact_type=payload.artifact_type,
            title=payload.title,
            owner_ref=payload.owner_ref,
            project=project,
            context=context or {"context_id": "", "title": "Research Room handoff" if room else "Project handoff", "scopes": ["current-research-room"] if room else (["current-project"] if project else ["my-library"]), "project_id": str((project or {}).get("project_id") or ""), "room_id": str((room or {}).get("room_id") or "")},
            sources=sources,
            research_state=research_state,
            evidence_quality=quality,
            room_synthesis=room_synthesis,
            selected_object_ids=payload.selected_object_ids,
            include_rejected=payload.include_rejected,
            notes=payload.notes,
            promotion_id=promotion_id,
        )
        promotion = normalize_promotion({**payload.model_dump(), "project_id": str((project or {}).get("project_id") or payload.project_id), "context_id": str((context or {}).get("context_id") or payload.context_id), "room_id": str((room or {}).get("room_id") or payload.room_id)}, packet, existing)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_workspace_promotion(promotion)
    project_id = str(stored.get("project_id") or "")
    if project_id:
        store.save_project_event(project_id, "workspace-promotion-prepared", {"promotion_id": stored["promotion_id"], "artifact_type": stored["artifact_type"], "packet_fingerprint": stored["packet_fingerprint"]}, payload.owner_ref)
    store.save_research_activity(normalize_activity({"owner_ref": payload.owner_ref, "project_id": project_id, "context_id": str(stored.get("context_id") or ""), "event_type": "workspace-promotion-prepared", "note": stored["title"], "metadata": {"promotion_id": stored["promotion_id"], "artifact_type": stored["artifact_type"], "packet_fingerprint": stored["packet_fingerprint"]}}))
    if stored.get("room_id"):
        store.save_room_activity(normalize_room_activity({"room_id": stored["room_id"], "actor_ref": payload.owner_ref, "event_type": "workspace-promotion-prepared", "note": stored["title"], "metadata": {"promotion_id": stored["promotion_id"], "artifact_type": stored["artifact_type"]}}))
    return stored


@app.post("/v1/workspace/promotions/{promotion_id}/receipt", dependencies=[Depends(require_key)])
def receive_workspace_promotion_receipt(promotion_id: str, payload: WorkspacePromotionReceiptRequest) -> dict[str, Any]:
    if promotion_id != payload.promotion_id:
        raise HTTPException(status_code=422, detail="Workspace promotion path and payload promotion_id must match.")
    promotion = store.workspace_promotion(promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Unknown Workspace promotion.")
    if str(promotion.get("owner_ref") or "") != payload.owner_ref:
        raise HTTPException(status_code=403, detail="Workspace promotion does not belong to this owner.")
    try:
        updated = apply_promotion_receipt(promotion, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    stored = store.save_workspace_promotion(updated)
    if stored.get("project_id"):
        store.save_project_event(str(stored["project_id"]), "workspace-promotion-imported", {"promotion_id": promotion_id, "workspace_artifact_id": str((stored.get("receipt") or {}).get("workspace_artifact_id") or ""), "packet_fingerprint": stored["packet_fingerprint"]}, payload.owner_ref)
    store.save_research_activity(normalize_activity({"owner_ref": payload.owner_ref, "project_id": str(stored.get("project_id") or ""), "context_id": str(stored.get("context_id") or ""), "event_type": "workspace-promotion-imported", "note": stored["title"], "metadata": {"promotion_id": promotion_id, "workspace_artifact_id": str((stored.get("receipt") or {}).get("workspace_artifact_id") or "")}}))
    if stored.get("room_id"):
        store.save_room_activity(normalize_room_activity({"room_id": str(stored["room_id"]), "actor_ref": payload.owner_ref, "event_type": "workspace-promotion-imported", "note": stored["title"], "metadata": {"promotion_id": promotion_id}}))
    return stored


def _lifecycle_scope(lifecycle: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]], dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    owner_ref = str(lifecycle.get("owner_ref") or "")[:220]
    project_id = str(lifecycle.get("project_id") or "")[:220]
    context_id = str(lifecycle.get("context_id") or "")[:220]
    room_id = str(lifecycle.get("room_id") or "")[:220]
    project = store.research_project(project_id) if project_id else None
    if project_id and not project:
        raise HTTPException(status_code=404, detail="Unknown research project.")
    if project and str(project.get("owner_ref") or "") != owner_ref:
        raise HTTPException(status_code=403, detail="Research lifecycle owner does not own this project.")
    context = store.research_context(context_id) if context_id else None
    if context_id and not context:
        raise HTTPException(status_code=404, detail="Unknown research context.")
    if context and str(context.get("owner_ref") or "") != owner_ref:
        raise HTTPException(status_code=403, detail="Research lifecycle owner does not own this context.")
    room = None
    if room_id:
        room, _ = _require_room_member(room_id, owner_ref)
    if context:
        resolution = resolve_saved_research_context(context_id)
        sources = list(resolution.get("objects") or [])[:500]
        project_id = project_id or str(context.get("project_id") or "")[:220]
        room_id = room_id or str(context.get("room_id") or "")[:220]
        if project_id and not project:
            project = store.research_project(project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Unknown research project.")
            if str(project.get("owner_ref") or "") != owner_ref:
                raise HTTPException(status_code=403, detail="Research lifecycle owner does not own this project.")
        if room_id and not room:
            room, _ = _require_room_member(room_id, owner_ref)
    elif room_id:
        sources = store.library_objects_for_room(room_id, 1000)[:500]
        project_id = project_id or str((room or {}).get("project_id") or "")[:220]
        if project_id and not project:
            project = store.research_project(project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Unknown research project.")
            if str(project.get("owner_ref") or "") != owner_ref:
                raise HTTPException(status_code=403, detail="Research lifecycle owner does not own this project.")
    elif project_id:
        sources = list(store.project_bundle(project_id).get("library_objects") or [])[:500]
    else:
        sources = store.library_objects(500, owner_ref)
    research_state = _research_state_summary(owner_ref, project_id, context_id)
    quality = {
        "schema": QUALITY_SIGNALS_SCHEMA,
        "summary": quality_summary(sources),
        "comparison": compare_sources(sources),
        "gaps": evidence_gaps(sources),
        "governance": {"descriptive_only": True, "truth_score": False},
    }
    searches = store.federated_searches(500, owner_ref=owner_ref, project_id=project_id, context_id=context_id)
    promotions = store.workspace_promotions(500, owner_ref=owner_ref, project_id=project_id, context_id=context_id, room_id=room_id)
    room_activity = store.room_activities(room_id, 500) if room_id else []
    return project, context, room, sources, research_state, quality, searches, promotions, room_activity


def _lifecycle_summary(lifecycle: dict[str, Any]) -> dict[str, Any]:
    project, context, room, sources, research_state, quality, searches, promotions, room_activity = _lifecycle_scope(lifecycle)
    checkpoints = store.lifecycle_checkpoints(str(lifecycle.get("lifecycle_id") or ""), 500)
    return evaluate_lifecycle(
        lifecycle,
        project=project,
        context=context,
        room=room,
        sources=sources,
        research_state=research_state,
        quality=quality,
        federated_searches=searches,
        promotions=promotions,
        checkpoints=checkpoints,
        room_activity=room_activity,
    )


@app.get("/v1/research/lifecycle/catalog", dependencies=[Depends(require_key)])
def research_lifecycle_catalog() -> dict[str, Any]:
    return {"version": __version__, **lifecycle_catalog()}


@app.get("/v1/research/lifecycles", dependencies=[Depends(require_key)])
def list_research_lifecycles(limit: int = 200, owner_ref: str = "", project_id: str = "", context_id: str = "", room_id: str = "", status: str = "") -> dict[str, Any]:
    rows = store.research_lifecycles(limit, owner_ref, project_id, context_id, room_id, status)
    return {"schema": "sc-research-lifecycle-list/1.0", "version": __version__, "lifecycles": rows, "count": len(rows)}


@app.post("/v1/research/lifecycles", dependencies=[Depends(require_key)])
def save_research_lifecycle(payload: ResearchLifecycleRequest) -> dict[str, Any]:
    existing = store.research_lifecycle(payload.lifecycle_id) if payload.lifecycle_id else None
    if existing and str(existing.get("owner_ref") or "") != payload.owner_ref:
        raise HTTPException(status_code=403, detail="Research lifecycle does not belong to this owner.")
    try:
        lifecycle = normalize_lifecycle(payload.model_dump(), existing)
        _lifecycle_scope(lifecycle)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_research_lifecycle(lifecycle)
    if not existing:
        store.save_lifecycle_event(normalize_lifecycle_event({"lifecycle_id": stored["lifecycle_id"], "owner_ref": stored["owner_ref"], "actor_ref": stored["owner_ref"], "event_type": "created", "to_stage": stored["current_stage"], "note": stored["title"]}))
    return {**stored, "summary": _lifecycle_summary(stored)}


@app.get("/v1/research/lifecycles/{lifecycle_id}", dependencies=[Depends(require_key)])
def get_research_lifecycle(lifecycle_id: str, owner_ref: str = "") -> dict[str, Any]:
    lifecycle = store.research_lifecycle(lifecycle_id)
    if not lifecycle:
        raise HTTPException(status_code=404, detail="Unknown research lifecycle.")
    if owner_ref and str(lifecycle.get("owner_ref") or "") != owner_ref:
        raise HTTPException(status_code=403, detail="Research lifecycle does not belong to this owner.")
    return {**lifecycle, "summary": _lifecycle_summary(lifecycle), "events": store.lifecycle_events(lifecycle_id, 200), "checkpoints": store.lifecycle_checkpoints(lifecycle_id, 100)}


@app.get("/v1/research/lifecycles/{lifecycle_id}/summary", dependencies=[Depends(require_key)])
def get_research_lifecycle_summary(lifecycle_id: str, owner_ref: str = "") -> dict[str, Any]:
    lifecycle = store.research_lifecycle(lifecycle_id)
    if not lifecycle:
        raise HTTPException(status_code=404, detail="Unknown research lifecycle.")
    if owner_ref and str(lifecycle.get("owner_ref") or "") != owner_ref:
        raise HTTPException(status_code=403, detail="Research lifecycle does not belong to this owner.")
    return _lifecycle_summary(lifecycle)


@app.post("/v1/research/lifecycles/{lifecycle_id}/transition", dependencies=[Depends(require_key)])
def transition_research_lifecycle(lifecycle_id: str, payload: ResearchLifecycleTransitionRequest) -> dict[str, Any]:
    lifecycle = store.research_lifecycle(lifecycle_id)
    if not lifecycle:
        raise HTTPException(status_code=404, detail="Unknown research lifecycle.")
    if str(lifecycle.get("owner_ref") or "") != payload.owner_ref:
        raise HTTPException(status_code=403, detail="Research lifecycle does not belong to this owner.")
    actor_ref = str(payload.actor_ref or payload.owner_ref)[:220]
    if actor_ref != payload.owner_ref:
        raise HTTPException(status_code=403, detail="Lifecycle transition actor must match the authenticated lifecycle owner at this API boundary.")
    summary_before = _lifecycle_summary(lifecycle)
    blockers = list(summary_before.get("current_stage_blockers") or [])
    try:
        updated, event = transition_lifecycle(lifecycle, target_stage=payload.target_stage, actor_ref=actor_ref, reason=payload.reason, confirmed=payload.confirmed, blockers_acknowledged=payload.blockers_acknowledged)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stored = store.save_research_lifecycle(updated)
    store.save_lifecycle_event(event)
    store.save_research_activity(normalize_activity({"owner_ref": stored["owner_ref"], "project_id": stored.get("project_id", ""), "context_id": stored.get("context_id", ""), "event_type": "lifecycle-stage-transition", "note": f"{event.get('from_stage','')} → {event.get('to_stage','')}", "metadata": {"lifecycle_id": lifecycle_id, "blockers_before_transition": blockers, "explicit_confirmation": True}}))
    return {**stored, "transition": event, "summary": _lifecycle_summary(stored)}


@app.post("/v1/research/lifecycles/{lifecycle_id}/checkpoint", dependencies=[Depends(require_key)])
def checkpoint_research_lifecycle(lifecycle_id: str, payload: ResearchLifecycleCheckpointRequest) -> dict[str, Any]:
    lifecycle = store.research_lifecycle(lifecycle_id)
    if not lifecycle:
        raise HTTPException(status_code=404, detail="Unknown research lifecycle.")
    if str(lifecycle.get("owner_ref") or "") != payload.owner_ref:
        raise HTTPException(status_code=403, detail="Research lifecycle does not belong to this owner.")
    actor_ref = str(payload.actor_ref or payload.owner_ref)[:220]
    if actor_ref != payload.owner_ref:
        raise HTTPException(status_code=403, detail="Lifecycle checkpoint actor must match the authenticated lifecycle owner at this API boundary.")
    summary = _lifecycle_summary(lifecycle)
    checkpoint = build_checkpoint(lifecycle, summary, actor_ref=actor_ref, note=payload.note)
    store.save_lifecycle_checkpoint(checkpoint)
    store.save_lifecycle_event(normalize_lifecycle_event({"lifecycle_id": lifecycle_id, "owner_ref": payload.owner_ref, "actor_ref": actor_ref, "event_type": "checkpoint", "from_stage": lifecycle.get("current_stage", "frame"), "to_stage": lifecycle.get("current_stage", "frame"), "note": payload.note, "metadata": {"checkpoint_id": checkpoint["checkpoint_id"], "checkpoint_fingerprint": checkpoint["fingerprint"]}}))
    store.save_research_activity(normalize_activity({"owner_ref": payload.owner_ref, "project_id": lifecycle.get("project_id", ""), "context_id": lifecycle.get("context_id", ""), "event_type": "lifecycle-checkpoint", "note": payload.note, "metadata": {"lifecycle_id": lifecycle_id, "checkpoint_id": checkpoint["checkpoint_id"], "checkpoint_fingerprint": checkpoint["fingerprint"]}}))
    return {"schema": LIFECYCLE_CHECKPOINT_SCHEMA, "version": __version__, "checkpoint": checkpoint, "summary": _lifecycle_summary(lifecycle)}


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
    result={"ok":True,"dry_run":payload.dry_run,"verification":verification,"counts":{"investigations":len(body.get("investigations") or []),"entities":len(body.get("entities") or []),"library_objects":len(body.get("library_objects") or []),"research_activity":len(body.get("research_activity") or []),"object_states":len(body.get("object_states") or []),"open_questions":len(body.get("open_questions") or []),"research_rooms":len(body.get("research_rooms") or []),"federated_searches":len(body.get("federated_searches") or []),"workspace_promotions":len(body.get("workspace_promotions") or []),"research_lifecycles":len(body.get("research_lifecycles") or [])}}
    if not payload.dry_run:
        saved=normalize_project(project,store.research_project(str(project.get("project_id") or "")))
        store.save_research_project(saved)
        for item in body.get("library_objects") or []:
            if isinstance(item, dict):
                store.save_library_object(normalize_library_object(item, store.library_object(str(item.get("object_id") or ""))))
        for item in body.get("investigations") or []: store.save_research_investigation(normalize_investigation(item,saved["project_id"],item))
        for item in body.get("entities") or []: store.save_project_entity({**item,"project_id":saved["project_id"]})
        for item in body.get("research_activity") or []:
            if isinstance(item, dict): store.save_research_activity(normalize_activity({**item,"owner_ref":saved.get("owner_ref", ""),"project_id":saved["project_id"]}))
        for item in body.get("object_states") or []:
            if isinstance(item, dict):
                existing_state=store.research_object_state(str(saved.get("owner_ref") or ""),str(item.get("object_id") or ""),saved["project_id"],str(item.get("context_id") or ""))
                store.save_research_object_state(normalize_object_state({**item,"owner_ref":saved.get("owner_ref", ""),"project_id":saved["project_id"]},existing_state))
        for item in body.get("open_questions") or []:
            if isinstance(item, dict): store.save_research_open_question(normalize_open_question({**item,"owner_ref":saved.get("owner_ref", ""),"project_id":saved["project_id"]},store.research_open_question(str(item.get("question_id") or ""))))
        for room_bundle in body.get("research_rooms") or []:
            if not isinstance(room_bundle, dict):
                continue
            room_payload=room_bundle.get("room") if isinstance(room_bundle.get("room"),dict) else {}
            if not room_payload:
                continue
            room=normalize_room({**room_payload,"project_id":saved["project_id"]},store.research_room(str(room_payload.get("room_id") or "")))
            store.save_research_room(room)
            for member_payload in room_bundle.get("members") or []:
                if isinstance(member_payload,dict):
                    store.save_room_member(normalize_member({**member_payload,"room_id":room["room_id"]},store.room_member(room["room_id"],str(member_payload.get("member_ref") or ""))))
            for evidence_payload in room_bundle.get("evidence_states") or []:
                if isinstance(evidence_payload,dict):
                    store.save_room_evidence_state(normalize_room_evidence_state({**evidence_payload,"room_id":room["room_id"]},store.room_evidence_state(room["room_id"],str(evidence_payload.get("object_id") or ""))))
            for question_payload in room_bundle.get("questions") or []:
                if isinstance(question_payload,dict):
                    store.save_room_question(normalize_room_question({**question_payload,"room_id":room["room_id"]},store.room_question(str(question_payload.get("question_id") or ""))))
            for disagreement_payload in room_bundle.get("disagreements") or []:
                if isinstance(disagreement_payload,dict):
                    store.save_room_disagreement(normalize_room_disagreement({**disagreement_payload,"room_id":room["room_id"]},store.room_disagreement(str(disagreement_payload.get("disagreement_id") or ""))))
            for activity_payload in room_bundle.get("activity") or []:
                if isinstance(activity_payload,dict):
                    store.save_room_activity(normalize_room_activity({**activity_payload,"room_id":room["room_id"]}))
        for search_payload in body.get("federated_searches") or []:
            if isinstance(search_payload,dict):
                restored = normalize_search_record({**search_payload,"project_id":saved["project_id"]}, owner_ref=str(saved.get("owner_ref") or ""), project_id=saved["project_id"], context_id=str(search_payload.get("context_id") or ""))
                store.save_federated_search(restored)
        for promotion_payload in body.get("workspace_promotions") or []:
            if isinstance(promotion_payload,dict):
                packet=promotion_payload.get("packet") if isinstance(promotion_payload.get("packet"),dict) else {}
                if packet:
                    try:
                        store.save_workspace_promotion(normalize_promotion({**promotion_payload,"owner_ref":saved.get("owner_ref", ""),"project_id":saved["project_id"]},packet,store.workspace_promotion(str(promotion_payload.get("promotion_id") or ""))))
                    except ValueError:
                        continue
        for lifecycle_bundle in body.get("research_lifecycles") or []:
            if not isinstance(lifecycle_bundle,dict):
                continue
            lifecycle_payload=lifecycle_bundle.get("lifecycle") if isinstance(lifecycle_bundle.get("lifecycle"),dict) else {}
            if not lifecycle_payload:
                continue
            try:
                lifecycle=normalize_lifecycle({**lifecycle_payload,"owner_ref":saved.get("owner_ref", ""),"project_id":saved["project_id"]},store.research_lifecycle(str(lifecycle_payload.get("lifecycle_id") or "")))
                store.save_research_lifecycle(lifecycle)
            except ValueError:
                continue
            for event_payload in lifecycle_bundle.get("events") or []:
                if isinstance(event_payload,dict):
                    try: store.save_lifecycle_event(normalize_lifecycle_event({**event_payload,"lifecycle_id":lifecycle["lifecycle_id"],"owner_ref":saved.get("owner_ref", "")}))
                    except ValueError: continue
            for checkpoint_payload in lifecycle_bundle.get("checkpoints") or []:
                if isinstance(checkpoint_payload,dict):
                    checkpoint={**checkpoint_payload,"lifecycle_id":lifecycle["lifecycle_id"],"owner_ref":saved.get("owner_ref", "")}
                    store.save_lifecycle_checkpoint(checkpoint)
        result["project_id"]=saved["project_id"]
    return result

@app.post("/v1/session/reset", dependencies=[Depends(require_key)])
def reset_session(payload: SessionResetRequest) -> dict[str, Any]:
    session_id = _session_id(payload.session_id)
    removed_turns = len(_sessions.pop(session_id, []))
    return {"ok": True, "version": __version__, "session_id": session_id, "removed_turns": removed_turns}


@app.post("/v1/retrieval/plan", dependencies=[Depends(require_key)])
def retrieval_plan_endpoint(payload: RetrievalRequest) -> dict[str, Any]:
    config = sanitize_retrieval_config(store.retrieval_config())
    maximum = payload.max_queries or int(config["advanced"]["max_queries"])
    return {"ok": True, "version": __version__, "plan": build_query_plan(payload.query, maximum)}


@app.post("/v1/retrieve", response_model=list[RetrievedSource], dependencies=[Depends(require_key)])
async def retrieve_endpoint(payload: RetrievalRequest) -> list[RetrievedSource]:
    matches, _ = await _hybrid_retrieve(
        payload.query, payload.limit, include_semantic=payload.include_semantic,
        filters=payload.filters.model_dump(), advanced_enabled=payload.advanced,
        max_queries=payload.max_queries, candidate_pool=payload.candidate_pool,
    )
    return matches


@app.post("/v1/retrieve/explain", dependencies=[Depends(require_key)])
async def retrieve_explain_endpoint(payload: RetrievalRequest) -> dict[str, Any]:
    matches, diagnostics = await _hybrid_retrieve(
        payload.query, payload.limit, include_semantic=payload.include_semantic,
        filters=payload.filters.model_dump(), advanced_enabled=payload.advanced,
        max_queries=payload.max_queries, candidate_pool=payload.candidate_pool,
    )
    return {
        "ok": True,
        "version": __version__,
        "schema": diagnostics.get("schema", ADVANCED_RETRIEVAL_SCHEMA),
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
    inline_context = sanitize_inline_context(payload.research_context)
    state_summary: dict[str, Any] = {}
    state_prompt: dict[str, Any] = {}
    saved_context: dict[str, Any] | None = None
    room_prompt: dict[str, Any] = inline_context.get("room_collaboration") if isinstance(inline_context.get("room_collaboration"), dict) else {}
    if inline_context.get("context_id"):
        saved_context = store.research_context(str(inline_context.get("context_id") or ""))
        if saved_context and str(saved_context.get("owner_ref") or ""):
            state_summary = _research_state_summary(
                str(saved_context.get("owner_ref") or ""),
                str(saved_context.get("project_id") or inline_context.get("project_id") or ""),
                str(saved_context.get("context_id") or inline_context.get("context_id") or ""),
            )
            state_prompt = prompt_research_state(state_summary)
    rejected_object_ids = set(state_prompt.get("rejected_object_ids") or [])
    retrieval_context = dict(inline_context) if inline_context else {}
    if retrieval_context and rejected_object_ids:
        retrieval_context["objects"] = [
            item for item in list(inline_context.get("objects") or [])
            if isinstance(item, dict) and str(item.get("object_id") or "") not in rejected_object_ids
        ]
    records = store.records()
    calibration = store.retrieval_config()
    context_source_ids = {
        str(item.get("source_record_id") or "")
        for item in retrieval_context.get("objects", [])
        if isinstance(item, dict) and str(item.get("source_record_id") or "")
    }
    retrieval_limit = min(30, max(settings.source_limit, settings.source_limit * 3)) if context_source_ids else settings.source_limit
    matches, retrieval_diagnostics = await _hybrid_retrieve(payload.question, retrieval_limit, calibration)
    matches, context_retrieval = _prioritize_context_matches(matches, retrieval_context, settings.source_limit)
    context_retrieval["rejected_context_objects_deprioritized"] = len(rejected_object_ids)
    retrieval_diagnostics["research_context_retrieval"] = context_retrieval
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
        if inline_context:
            route_hint["research_context"] = inline_context
        if state_prompt:
            route_hint["research_state"] = state_prompt
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
    if state_prompt:
        store.save_research_activity(normalize_activity({
            "owner_ref": str(state_summary.get("owner_ref") or ""),
            "project_id": str(state_summary.get("project_id") or ""),
            "context_id": str(state_summary.get("context_id") or ""),
            "event_type": "search",
            "query": payload.question,
            "metadata": {
                "research_mode": research_mode,
                "answer_trace_id": trace["trace_id"],
                "source_record_ids": [item.id for item in matches][:25],
                "citation_verification_ok": bool(citation_verification.get("ok")),
            },
        }))
        state_summary = _research_state_summary(
            str(state_summary.get("owner_ref") or ""),
            str(state_summary.get("project_id") or ""),
            str(state_summary.get("context_id") or ""),
        )
        state_prompt = prompt_research_state(state_summary)
    if saved_context and str(saved_context.get("room_id") or "") and str(saved_context.get("owner_ref") or ""):
        room_id = str(saved_context.get("room_id") or "")
        actor_ref = str(saved_context.get("owner_ref") or "")
        member = store.room_member(room_id, actor_ref)
        if member and str(member.get("status") or "") == "active":
            store.save_room_activity(normalize_room_activity({
                "room_id": room_id,
                "actor_ref": actor_ref,
                "event_type": "search",
                "note": payload.question[:1000],
                "metadata": {
                    "research_mode": research_mode,
                    "answer_trace_id": trace["trace_id"],
                    "source_record_ids": [item.id for item in matches][:25],
                    "citation_verification_ok": bool(citation_verification.get("ok")),
                },
            }))
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
    if inline_context:
        provenance["research_context"] = {
            "context_id": inline_context.get("context_id", ""),
            "fingerprint": inline_context.get("fingerprint", ""),
            "scopes": inline_context.get("scopes", []),
            "object_count": len(inline_context.get("objects", [])),
        }
        retrieval_diagnostics["research_context"] = provenance["research_context"]
    if room_prompt:
        provenance["room_collaboration"] = {
            "schema": room_prompt.get("schema", ""),
            "room_id": room_prompt.get("room_id", ""),
            "fingerprint": room_prompt.get("fingerprint", ""),
            "shared_evidence_count": len(room_prompt.get("shared_evidence", [])),
            "open_question_count": len(room_prompt.get("open_questions", [])),
            "open_disagreement_count": len(room_prompt.get("open_disagreements", [])),
            "participant_attribution": True,
            "not_evidence": True,
        }
        retrieval_diagnostics["room_collaboration"] = provenance["room_collaboration"]
    if state_prompt:
        provenance["research_state"] = {
            "schema": state_prompt.get("schema", ""),
            "fingerprint": state_prompt.get("fingerprint", ""),
            "recent_search_count": len(state_prompt.get("recent_searches", [])),
            "open_question_count": len(state_prompt.get("open_questions", [])),
            "rejected_object_count": len(state_prompt.get("rejected_object_ids", [])),
            "workflow_memory_only": True,
            "not_evidence": True,
        }
        retrieval_diagnostics["research_state"] = provenance["research_state"]

    workspace = _workspace_summary(research_mode, matches, related, ai_used, gate)
    if inline_context:
        workspace["research_context"] = {
            "context_id": inline_context.get("context_id", ""),
            "title": inline_context.get("title", "Research context"),
            "scopes": inline_context.get("scopes", []),
            "object_count": len(inline_context.get("objects", [])),
        }
    if room_prompt:
        workspace["room_collaboration"] = {
            "room_id": room_prompt.get("room_id", ""),
            "title": room_prompt.get("title", "Research Room"),
            "shared_evidence": len(room_prompt.get("shared_evidence", [])),
            "open_questions": len(room_prompt.get("open_questions", [])),
            "open_disagreements": len(room_prompt.get("open_disagreements", [])),
            "participant_attribution": True,
        }
    if state_summary:
        workspace["research_state"] = {
            "activities": int((state_summary.get("counts") or {}).get("activities", 0)),
            "open_questions": len(state_summary.get("open_questions", [])),
            "review_queue": len(state_summary.get("review_queue", [])),
            "rejected_objects": len(state_summary.get("rejected_objects", [])),
            "flagged_contradictions": len(state_summary.get("flagged_contradictions", [])),
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
        workspace=workspace,
        research_context=inline_context,
        research_state=state_prompt,
        session_turns=len(_sessions[session_id]) // 2,
        capabilities=capabilities,
        typed_handoffs=typed_handoffs,
        provenance=provenance,
        status=_status().model_dump(),
    )


# Energy Systems Intelligence v1.2.0 target-side runtime consumer.
from .energy_runtime_consumer import router as energy_runtime_consumer_router
app.include_router(energy_runtime_consumer_router)
