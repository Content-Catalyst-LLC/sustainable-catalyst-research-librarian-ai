from __future__ import annotations

import hashlib
import hmac
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ..clients.platform_core import PlatformCoreClient, PlatformCoreError
from ..config import settings
from ..contracts.unified_research_runtime import (
    UnifiedResearchRuntimePlanRequest, UnifiedResearchRuntimeExecutionRequest,
)
from ..contracts.research_workflow import (
    ResearchWorkflowCreateRequest, ResearchWorkflowControlRequest,
    ResearchWorkflowApprovalRequest, ResearchWorkflowAdvanceRequest,
)
from ..contracts.visual_research import (
    VisualResearchPlanRequest, CoreVisualResearchPromotionRequest,
)
from ..contracts.statistical_research import (
    StatisticalAnalysisPlanRequest, CoreStatisticalValidationPromotionRequest,
    CoreCoefficientRequest, CoreIntervalRequest, CoreInterpretationRequest,
)
from ..contracts.argument_synthesis import (
    ArgumentSynthesisPlanRequest,
    CoreArgumentSynthesisPromotionRequest,
)
from ..contracts.evidence_bridge import (
    CORE_EVIDENCE_BRIDGE_SCHEMA,
    CorePassageEvidencePromotionRequest,
    CoreSourceSnapshotPromotionRequest,
)
from ..contracts.research_intelligence_extraction import (
    CoreResearchCandidatePromotionRequest,
    ResearchIntelligenceExtractionRequest,
)
from ..contracts.research_sync import (
    CoreProjectSynchronizationPlanRequest,
    CoreProjectSynchronizationRequest,
)
from ..contracts.platform_core import (
    CORE_INTEGRATION_SCHEMA,
    CoreExchangePackageRequest,
    CoreResearchObjectPromotionRequest,
    CoreUnifiedProjectSyncRequest,
)
from ..services.unified_research_runtime import (
    capabilities as unified_research_capabilities, build_runtime_plan, readiness as unified_research_readiness, execute_safe_runtime,
)
from ..services.research_workflow import (
    get_research_workflow_store, capabilities as research_workflow_capabilities,
)
from ..services.visual_research import (
    capabilities as visual_research_capabilities, build_plan as build_visual_research_plan,
    readiness as visual_research_readiness, promote_plan as promote_visual_research_plan,
)
from ..services.statistical_research import (
    capabilities as statistical_research_capabilities, build_plan as build_statistical_analysis_plan,
    readiness as statistical_research_readiness, promote_validation as promote_statistical_validation,
    add_coefficient as add_statistical_coefficient, add_interval as add_statistical_interval,
    add_interpretation as add_statistical_interpretation,
)
from ..services.argument_synthesis import (
    build_plan as build_argument_synthesis_plan,
    capabilities as argument_synthesis_capabilities,
    contradiction_candidates as argument_contradiction_candidates,
    promote_plan as promote_argument_synthesis_plan,
)
from ..services.core_evidence_bridge import (
    evidence_bridge_capabilities,
    promote_passage_evidence,
    promote_source_snapshot,
)
from ..services.research_intelligence_extraction import (
    capabilities as research_intelligence_extraction_capabilities,
    extract_candidates,
    promote_candidate,
)
from ..services.core_research_sync import (
    build_project_sync_plan,
    capabilities as research_sync_capabilities,
    synchronize_project_research_objects,
)
from ..services.platform_core_integration import (
    CoreBindingConflict,
    create_exchange_package,
    integration_readiness,
    promote_research_object,
    synchronize_unified_project,
)
from ..store import store

router = APIRouter(prefix="/v1/core", tags=["Platform Core Integration"])


def require_backend_key(x_sc_rl_key: str = Header(default="", alias="X-SC-RL-Key")) -> None:
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SC_RL_BACKEND_API_KEY is not configured on the backend.",
        )
    supplied = hashlib.sha256((x_sc_rl_key or "").encode()).digest()
    expected = hashlib.sha256(settings.api_key.encode()).digest()
    if not x_sc_rl_key or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid backend integration key.")


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, CoreBindingConflict):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, PlatformCoreError):
        code = exc.status_code if exc.status_code and 400 <= exc.status_code < 600 else 502
        return HTTPException(
            status_code=code,
            detail={"message": str(exc), "core_detail": exc.detail},
        )
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/architecture", dependencies=[Depends(require_backend_key)])
def architecture() -> dict[str, Any]:
    return {
        "schema": CORE_INTEGRATION_SCHEMA,
        "release": settings.release_version,
        "python_runtime_owns": [
            "source-ingestion",
            "parsing",
            "chunking",
            "indexing",
            "retrieval",
            "connectors",
            "document-intelligence",
            "core-client-orchestration",
            "canonical-source-identity",
            "evidence-promotion-orchestration",
            "project-state-synchronization-orchestration",
            "candidate-finding-claim-extraction",
            "human-reviewed-core-research-intelligence-promotion",
            "reviewed-argument-synthesis-planning",
            "statistical-analysis-planning-and-runtime-handoffs",
            "visual-research-intelligence-planning-and-core-orchestration",
            "unified-research-intelligence-runtime-orchestration",
        ],
        "platform_core_owns": [
            "governed-research-objects",
            "governed-source-snapshots-and-evidence-records",
            "provenance-and-lineage",
            "claims-findings-arguments",
            "cross-study-synthesis",
            "reproducibility-packages",
            "visual-reasoning",
            "statistical-reasoning-objects",
            "cross-product-exchange",
            "immutable-project-state-versions",
            "versioned-cross-product-object-bindings",
            "declared-project-lineage",
            "governed-finding-claim-evidence-registry",
            "research-intelligence-version-history",
            "governed-argument-graphs-and-evidentiary-syntheses",
            "governed-statistical-reasoning-objects",
            "governed-visual-reasoning-objects-and-scene-semantics",
            "unified-visual-research-session-bindings",
            "governed-unified-research-runtime-state",
        ],
        "automatic_truth_promotion": False,
        "core_executes_arbitrary_research_code": False,
        "write_boundary": "All Core writes require the private Core write key and a Librarian binding record.",
    }


@router.get("/readiness", dependencies=[Depends(require_backend_key)])
async def readiness() -> dict[str, Any]:
    return await integration_readiness()


@router.get("/bindings", dependencies=[Depends(require_backend_key)])
def bindings(
    limit: int = Query(default=100, ge=1, le=1000),
    sync_state: str = Query(default=""),
) -> dict[str, Any]:
    items = store.platform_core_bindings(limit=limit, sync_state=sync_state)
    return {
        "schema": CORE_INTEGRATION_SCHEMA,
        "items": items,
        "count": len(items),
        "summary": store.platform_core_integration_summary(),
    }


@router.get("/bindings/{local_kind}/{local_id:path}", dependencies=[Depends(require_backend_key)])
def binding(local_kind: str, local_id: str) -> dict[str, Any]:
    item = store.platform_core_binding(local_kind, local_id)
    if not item:
        raise HTTPException(status_code=404, detail="Platform Core binding not found.")
    return {"schema": CORE_INTEGRATION_SCHEMA, "binding": item}


@router.post("/research-objects/promote", dependencies=[Depends(require_backend_key)])
async def research_object_promote(payload: CoreResearchObjectPromotionRequest) -> dict[str, Any]:
    try:
        return await promote_research_object(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/research-projects/synchronize", dependencies=[Depends(require_backend_key)])
async def research_project_synchronize(payload: CoreUnifiedProjectSyncRequest) -> dict[str, Any]:
    try:
        return await synchronize_unified_project(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/research-projects/{core_project_id:path}/bundle", dependencies=[Depends(require_backend_key)])
async def research_project_bundle(core_project_id: str) -> dict[str, Any]:
    try:
        result = await PlatformCoreClient().research_project_bundle(core_project_id)
        return {"schema": CORE_INTEGRATION_SCHEMA, "core": result}
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/exchange/packages", dependencies=[Depends(require_backend_key)])
async def exchange_package(payload: CoreExchangePackageRequest) -> dict[str, Any]:
    try:
        return await create_exchange_package(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/evidence/capabilities", dependencies=[Depends(require_backend_key)])
def evidence_capabilities() -> dict[str, Any]:
    return evidence_bridge_capabilities()


@router.post("/evidence/source-snapshots/promote", dependencies=[Depends(require_backend_key)])
async def evidence_source_snapshot_promote(payload: CoreSourceSnapshotPromotionRequest) -> dict[str, Any]:
    try:
        return await promote_source_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/evidence/passages/promote", dependencies=[Depends(require_backend_key)])
async def evidence_passage_promote(payload: CorePassageEvidencePromotionRequest) -> dict[str, Any]:
    try:
        return await promote_passage_evidence(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/research-sync/capabilities", dependencies=[Depends(require_backend_key)])
def research_sync_capability_report() -> dict[str, Any]:
    return research_sync_capabilities()


@router.post("/research-sync/plan", dependencies=[Depends(require_backend_key)])
def research_sync_plan(payload: CoreProjectSynchronizationPlanRequest) -> dict[str, Any]:
    try:
        return {"schema": research_sync_capabilities()["schema"], "plan": build_project_sync_plan(payload)}
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/research-sync/synchronize", dependencies=[Depends(require_backend_key)])
async def research_sync_synchronize(payload: CoreProjectSynchronizationRequest) -> dict[str, Any]:
    try:
        return await synchronize_project_research_objects(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/research-intelligence/capabilities", dependencies=[Depends(require_backend_key)])
def research_intelligence_extraction_capability_report() -> dict[str, Any]:
    return research_intelligence_extraction_capabilities()


@router.post("/research-intelligence/extract", dependencies=[Depends(require_backend_key)])
def research_intelligence_extract(payload: ResearchIntelligenceExtractionRequest) -> dict[str, Any]:
    try:
        return extract_candidates(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/research-intelligence/promote", dependencies=[Depends(require_backend_key)])
async def research_intelligence_promote(payload: CoreResearchCandidatePromotionRequest) -> dict[str, Any]:
    try:
        return await promote_candidate(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/argument-synthesis/capabilities", dependencies=[Depends(require_backend_key)])
def argument_synthesis_capability_report() -> dict[str, Any]:
    return argument_synthesis_capabilities()


@router.post("/argument-synthesis/plan", dependencies=[Depends(require_backend_key)])
def argument_synthesis_plan(payload: ArgumentSynthesisPlanRequest) -> dict[str, Any]:
    try:
        return build_argument_synthesis_plan(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/argument-synthesis/contradictions/{core_project_id:path}", dependencies=[Depends(require_backend_key)])
async def argument_synthesis_contradictions(core_project_id: str) -> dict[str, Any]:
    try:
        return await argument_contradiction_candidates(core_project_id)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/argument-synthesis/promote", dependencies=[Depends(require_backend_key)])
async def argument_synthesis_promote(payload: CoreArgumentSynthesisPromotionRequest) -> dict[str, Any]:
    try:
        return await promote_argument_synthesis_plan(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/statistical-research/capabilities", dependencies=[Depends(require_backend_key)])
def statistical_research_capability_report() -> dict[str, Any]:
    return statistical_research_capabilities()

@router.get("/statistical-research/readiness", dependencies=[Depends(require_backend_key)])
async def statistical_research_core_readiness() -> dict[str, Any]:
    try: return await statistical_research_readiness()
    except Exception as exc: raise _translate(exc) from exc

@router.post("/statistical-research/plan", dependencies=[Depends(require_backend_key)])
def statistical_research_plan(payload: StatisticalAnalysisPlanRequest) -> dict[str, Any]:
    try: return build_statistical_analysis_plan(payload)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/statistical-research/promote-validation", dependencies=[Depends(require_backend_key)])
async def statistical_research_promote_validation(payload: CoreStatisticalValidationPromotionRequest) -> dict[str, Any]:
    try: return await promote_statistical_validation(payload)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/statistical-research/coefficients", dependencies=[Depends(require_backend_key)])
async def statistical_research_coefficient(payload: CoreCoefficientRequest) -> dict[str, Any]:
    try: return await add_statistical_coefficient(payload)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/statistical-research/intervals", dependencies=[Depends(require_backend_key)])
async def statistical_research_interval(payload: CoreIntervalRequest) -> dict[str, Any]:
    try: return await add_statistical_interval(payload)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/statistical-research/interpretations", dependencies=[Depends(require_backend_key)])
async def statistical_research_interpretation(payload: CoreInterpretationRequest) -> dict[str, Any]:
    try: return await add_statistical_interpretation(payload)
    except Exception as exc: raise _translate(exc) from exc

@router.get("/visual-research/capabilities", dependencies=[Depends(require_backend_key)])
def visual_research_capability_report() -> dict[str, Any]:
    return visual_research_capabilities()

@router.get("/visual-research/readiness", dependencies=[Depends(require_backend_key)])
async def visual_research_core_readiness() -> dict[str, Any]:
    try: return await visual_research_readiness()
    except Exception as exc: raise _translate(exc) from exc

@router.post("/visual-research/plan", dependencies=[Depends(require_backend_key)])
def visual_research_plan(payload: VisualResearchPlanRequest) -> dict[str, Any]:
    try: return build_visual_research_plan(payload)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/visual-research/promote", dependencies=[Depends(require_backend_key)])
async def visual_research_promote(payload: CoreVisualResearchPromotionRequest) -> dict[str, Any]:
    try: return await promote_visual_research_plan(payload)
    except Exception as exc: raise _translate(exc) from exc

@router.get("/unified-research/capabilities", dependencies=[Depends(require_backend_key)])
def unified_research_capability_report() -> dict[str, Any]:
    return unified_research_capabilities()


@router.get("/unified-research/readiness", dependencies=[Depends(require_backend_key)])
async def unified_research_core_readiness() -> dict[str, Any]:
    try:
        return await unified_research_readiness()
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/unified-research/plan", dependencies=[Depends(require_backend_key)])
def unified_research_plan(payload: UnifiedResearchRuntimePlanRequest) -> dict[str, Any]:
    try:
        return build_runtime_plan(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/unified-research/execute", dependencies=[Depends(require_backend_key)])
def unified_research_execute(payload: UnifiedResearchRuntimeExecutionRequest) -> dict[str, Any]:
    try:
        return execute_safe_runtime(payload)
    except Exception as exc:
        raise _translate(exc) from exc



@router.get("/research-workflows/capabilities", dependencies=[Depends(require_backend_key)])
def research_workflow_capability_report() -> dict[str, Any]:
    return research_workflow_capabilities()

@router.post("/research-workflows", dependencies=[Depends(require_backend_key)])
def research_workflow_create(payload: ResearchWorkflowCreateRequest) -> dict[str, Any]:
    try:
        workflow, replayed = get_research_workflow_store().create(payload)
        return {"workflow": workflow, "idempotent_replay": replayed}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-workflows", dependencies=[Depends(require_backend_key)])
def research_workflow_list(state: str = "", limit: int = 100) -> dict[str, Any]:
    try:
        return {"workflows": get_research_workflow_store().list(state=state, limit=limit)}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-workflows/{workflow_id}", dependencies=[Depends(require_backend_key)])
def research_workflow_get(workflow_id: str) -> dict[str, Any]:
    try:
        return get_research_workflow_store().get(workflow_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-workflows/{workflow_id}/control", dependencies=[Depends(require_backend_key)])
def research_workflow_control(workflow_id: str, payload: ResearchWorkflowControlRequest) -> dict[str, Any]:
    try:
        return get_research_workflow_store().control(workflow_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-workflows/{workflow_id}/approvals", dependencies=[Depends(require_backend_key)])
def research_workflow_approve(workflow_id: str, payload: ResearchWorkflowApprovalRequest) -> dict[str, Any]:
    try:
        return get_research_workflow_store().approve(workflow_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-workflows/{workflow_id}/advance", dependencies=[Depends(require_backend_key)])
def research_workflow_advance(workflow_id: str, payload: ResearchWorkflowAdvanceRequest) -> dict[str, Any]:
    try:
        return get_research_workflow_store().advance(workflow_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-workflows/{workflow_id}/events", dependencies=[Depends(require_backend_key)])
def research_workflow_events(workflow_id: str, limit: int = 200) -> dict[str, Any]:
    try:
        return {"events": get_research_workflow_store().events(workflow_id, limit)}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-workflows/{workflow_id}/checkpoints", dependencies=[Depends(require_backend_key)])
def research_workflow_checkpoints(workflow_id: str, limit: int = 100) -> dict[str, Any]:
    try:
        return {"checkpoints": get_research_workflow_store().checkpoints(workflow_id, limit)}
    except Exception as exc:
        raise _translate(exc) from exc
