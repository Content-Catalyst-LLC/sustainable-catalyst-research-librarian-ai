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
from ..contracts.scholarly_research import (
    ScholarlyStudyCreateRequest, ScholarlyProtocolFreezeRequest, ScholarlyDeviationRequest,
    ScholarlyResultRequest, ScholarlyInterpretationRequest, ScholarlyManuscriptSectionRequest,
    ScholarlyReviewRequest, ScholarlyPackageFreezeRequest,
)
from ..contracts.peer_review import (
    ReviewRoundCreateRequest, ReviewerAssignmentRequest, StructuredPeerReviewRequest,
    AuthorResponseRequest, RevisionSubmissionRequest, ReplicationAttemptRequest,
    EditorialDecisionRequest, PeerReviewPackageFreezeRequest,
)
from ..contracts.scholarly_publication import (
    ScholarlyPublicationCreateRequest, PublicationVersionRequest, PublicationIdentifierRequest,
    PublicationStateTransitionRequest, PublicationHandoffRequest, PublicationPackageFreezeRequest,
)
from ..contracts.research_knowledge_graph import (
    KnowledgeGraphNodeRequest, KnowledgeGraphEdgeRequest, KnowledgeGraphProposalRequest,
    KnowledgeGraphProposalDecisionRequest, PublicationGraphMaterializationRequest, KnowledgeGraphSnapshotRequest,
)
from ..contracts.ai_research_context import (
    AIResearchContextCreateRequest, AIRetrievalRunCreateRequest, AIContextSnapshotRequest,
)
from ..contracts.rag_evaluation import (
    RAGEvaluationCreateRequest, RAGEvaluationCaseRequest, RAGClaimAssessmentRequest,
    RAGCitationAssessmentRequest, RAGEvaluationComparisonRequest, RAGEvaluationSnapshotRequest,
)
from ..contracts.ai_research_experiment import (
    AIResearchExperimentCreateRequest, AIResearchTrialCreateRequest, AIExperimentExecutionHandoffRequest,
    AIExperimentRunReceiptRequest, AIExperimentEvaluationBindingRequest, AIExperimentStateRequest,
    AIExperimentSnapshotRequest,
)
from ..contracts.model_aware_exchange import (
    ModelAwareResearchRecordRequest, CrossProductExchangeCreateRequest,
    CrossProductExchangeReceiptRequest, ModelAwareSnapshotRequest,
)
from ..contracts.unified_scholarly_ai_environment import (
    UnifiedResearchEnvironmentCreateRequest, UnifiedResearchEnvironmentBindingRequest,
    UnifiedResearchEnvironmentSnapshotRequest,
)
from ..contracts.research_design_methodology import (
    ResearchDesignPlanCreateRequest, MethodologyCandidateAddRequest, ResearchDesignValidityThreatRequest,
    ResearchDesignPreferenceRequest, ResearchDesignReviewStateRequest, ResearchDesignSnapshotRequest,
)
from ..contracts.evidence_search_strategy import (
    EvidenceSearchStrategyCreateRequest, SearchConceptAddRequest, SearchSourceTargetAddRequest,
    SearchQueryAddRequest, SearchEligibilityCriterionRequest, SearchExecutionReceiptRequest,
    EvidenceSearchReviewStateRequest, EvidenceSearchSnapshotRequest,
)
from ..contracts.systematic_review_evidence_synthesis import (
    SystematicReviewCreateRequest, ReviewCandidateAddRequest, ReviewScreeningDecisionRequest,
    ReviewExtractionRequest, ReviewBiasAssessmentRequest, ReviewEvidenceGradeRequest,
    ReviewSynthesisPlanRequest, SystematicReviewStateRequest, SystematicReviewSnapshotRequest,
)
from ..contracts.scholarly_literature_intelligence import (
    LiteratureIntelligenceCreateRequest, LiteratureWorkAddRequest, CitationContextAddRequest,
    LiteratureStrandAddRequest, LiteratureGapAddRequest, SeminalCandidateAddRequest,
    RelatedWorkCandidateAddRequest, RelatedWorkDecisionRequest, LiteratureIntelligenceStateRequest,
    LiteratureIntelligenceSnapshotRequest,
)
from ..contracts.argument_claim_counterclaim_intelligence import (
    ArgumentIntelligenceCreateRequest, ArgumentClaimAddRequest, ClaimEvidenceLinkRequest,
    ClaimRelationAddRequest, ClaimAssumptionAddRequest, ClaimDecisionRequest,
    ArgumentTensionAddRequest, ArgumentIntelligenceStateRequest, ArgumentIntelligenceSnapshotRequest,
)
from ..contracts.research_gap_novelty_intelligence import (
    ResearchGapNoveltyCreateRequest, ResearchGapCandidateAddRequest, ResearchGapDecisionRequest,
    NoveltyCandidateAddRequest, NoveltyDecisionRequest, OriginalResearchOpportunityAddRequest,
    ResearchGapNoveltyStateRequest, ResearchGapNoveltySnapshotRequest,
)
from ..contracts.dataset_discovery_data_fitness import (
    DatasetFitnessCreateRequest, DatasetCandidateAddRequest, DatasetVariableAddRequest, DataRequirementAddRequest, DatasetFitnessAssessmentRequest, DatasetFitnessStateRequest, DatasetFitnessSnapshotRequest,
)
from ..contracts.research_question_hypothesis import (
    ResearchQuestionPlanCreateRequest, ResearchSubquestionAddRequest, ResearchHypothesisAddRequest,
    ResearchEvidenceRequirementRequest, ResearchQuestionReviewStateRequest, ResearchQuestionSnapshotRequest,
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
from ..services.scholarly_research import (
    get_scholarly_research_store, capabilities as scholarly_research_capabilities,
)
from ..services.peer_review import (
    get_peer_review_store, capabilities as peer_review_capabilities,
)
from ..services.scholarly_publication import (
    get_scholarly_publication_store, capabilities as scholarly_publication_capabilities,
)
from ..services.research_knowledge_graph import (
    get_research_knowledge_graph_store, capabilities as research_knowledge_graph_capabilities,
)
from ..services.ai_research_context import (
    get_ai_research_context_store, capabilities as ai_research_context_capabilities,
)
from ..services.rag_evaluation import (
    get_rag_evaluation_store, capabilities as rag_evaluation_capabilities,
)
from ..services.ai_research_experiment import (
    get_ai_research_experiment_store, capabilities as ai_research_experiment_capabilities,
)
from ..services.model_aware_exchange import (
    get_model_aware_research_store, capabilities as model_aware_research_capabilities,
)
from ..services.unified_scholarly_ai_environment import (
    get_unified_scholarly_ai_environment_store, capabilities as unified_scholarly_ai_environment_capabilities,
)
from ..services.research_design_methodology import (
    get_research_design_methodology_store, capabilities as research_design_methodology_capabilities,
)
from ..services.evidence_search_strategy import (
    get_evidence_search_strategy_store, capabilities as evidence_search_strategy_capabilities,
)
from ..services.systematic_review_evidence_synthesis import (
    get_systematic_review_evidence_synthesis_store, capabilities as systematic_review_evidence_synthesis_capabilities,
)
from ..services.scholarly_literature_intelligence import (
    get_scholarly_literature_intelligence_store, capabilities as scholarly_literature_intelligence_capabilities,
)
from ..services.argument_claim_counterclaim_intelligence import (
    get_argument_claim_counterclaim_intelligence_store, capabilities as argument_claim_counterclaim_intelligence_capabilities,
)
from ..services.research_gap_novelty_intelligence import (
    get_research_gap_novelty_intelligence_store, capabilities as research_gap_novelty_intelligence_capabilities,
)
from ..services.dataset_discovery_data_fitness import get_dataset_discovery_data_fitness_store, capabilities as dataset_discovery_data_fitness_capabilities
from ..services.research_question_hypothesis import (
    get_research_question_hypothesis_store, capabilities as research_question_hypothesis_capabilities,
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
            "original-scholarly-research-environment",
            "human-peer-review-replication-and-scholarly-validation-registry",
            "scholarly-publication-citation-and-research-dissemination-registry",
            "research-knowledge-graph-and-publication-intelligence-registry",
            "ai-aware-retrieval-and-research-context-engineering",
            "rag-evaluation-and-evidence-grounding",
            "ai-research-experiment-orchestration",
            "model-aware-research-intelligence-and-cross-product-exchange",
            "unified-scholarly-and-ai-research-intelligence-environment",
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
            "governed-scholarly-research-lineage-and-reproducibility",
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

@router.get("/scholarly-research/capabilities", dependencies=[Depends(require_backend_key)])
def scholarly_research_capability_report() -> dict[str, Any]:
    return scholarly_research_capabilities()

@router.post("/scholarly-research/studies", dependencies=[Depends(require_backend_key)])
def scholarly_research_create(payload: ScholarlyStudyCreateRequest) -> dict[str, Any]:
    try:
        study, replayed = get_scholarly_research_store().create(payload)
        return {"study": study, "idempotent_replay": replayed}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-research/studies", dependencies=[Depends(require_backend_key)])
def scholarly_research_list(state: str = "", core_project_id: str = "", limit: int = 100) -> dict[str, Any]:
    try:
        return {"studies": get_scholarly_research_store().list(state=state, core_project_id=core_project_id, limit=limit)}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-research/studies/{study_id}", dependencies=[Depends(require_backend_key)])
def scholarly_research_get(study_id: str) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().get(study_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-research/studies/{study_id}/protocol/freeze", dependencies=[Depends(require_backend_key)])
def scholarly_research_freeze_protocol(study_id: str, payload: ScholarlyProtocolFreezeRequest) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().freeze_protocol(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-research/studies/{study_id}/deviations", dependencies=[Depends(require_backend_key)])
def scholarly_research_deviation(study_id: str, payload: ScholarlyDeviationRequest) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().add_deviation(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-research/studies/{study_id}/results", dependencies=[Depends(require_backend_key)])
def scholarly_research_result(study_id: str, payload: ScholarlyResultRequest) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().add_result(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-research/studies/{study_id}/interpretations", dependencies=[Depends(require_backend_key)])
def scholarly_research_interpretation(study_id: str, payload: ScholarlyInterpretationRequest) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().add_interpretation(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-research/studies/{study_id}/manuscript-sections", dependencies=[Depends(require_backend_key)])
def scholarly_research_manuscript_section(study_id: str, payload: ScholarlyManuscriptSectionRequest) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().add_manuscript_section(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-research/studies/{study_id}/reviews", dependencies=[Depends(require_backend_key)])
def scholarly_research_review(study_id: str, payload: ScholarlyReviewRequest) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().review(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-research/studies/{study_id}/publication-readiness", dependencies=[Depends(require_backend_key)])
def scholarly_research_publication_readiness(study_id: str) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().readiness(study_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-research/studies/{study_id}/packages/freeze", dependencies=[Depends(require_backend_key)])
def scholarly_research_package_freeze(study_id: str, payload: ScholarlyPackageFreezeRequest) -> dict[str, Any]:
    try:
        return get_scholarly_research_store().freeze_package(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-research/studies/{study_id}/revisions", dependencies=[Depends(require_backend_key)])
def scholarly_research_revisions(study_id: str, limit: int = 200) -> dict[str, Any]:
    try:
        return {"revisions": get_scholarly_research_store().revisions(study_id, limit)}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-research/studies/{study_id}/packages", dependencies=[Depends(require_backend_key)])
def scholarly_research_packages(study_id: str, limit: int = 100) -> dict[str, Any]:
    try:
        return {"packages": get_scholarly_research_store().packages(study_id, limit)}
    except Exception as exc:
        raise _translate(exc) from exc





@router.get("/scholarly-publication/capabilities", dependencies=[Depends(require_backend_key)])
def scholarly_publication_capability_report() -> dict[str, Any]:
    return scholarly_publication_capabilities()

@router.post("/scholarly-publication/studies/{study_id}/publications", dependencies=[Depends(require_backend_key)])
def scholarly_publication_create(study_id: str, payload: ScholarlyPublicationCreateRequest) -> dict[str, Any]:
    try:
        item, replayed = get_scholarly_publication_store().create(study_id, payload)
        return {"publication": item, "idempotent_replay": replayed}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-publication/publications", dependencies=[Depends(require_backend_key)])
def scholarly_publication_list(study_id: str = "", state: str = "", limit: int = 100) -> dict[str, Any]:
    try:
        return {"publications": get_scholarly_publication_store().list(study_id=study_id, state=state, limit=limit)}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-publication/publications/{publication_id}", dependencies=[Depends(require_backend_key)])
def scholarly_publication_get(publication_id: str) -> dict[str, Any]:
    try:
        return get_scholarly_publication_store().get(publication_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-publication/publications/{publication_id}/versions", dependencies=[Depends(require_backend_key)])
def scholarly_publication_version(publication_id: str, payload: PublicationVersionRequest) -> dict[str, Any]:
    try:
        return get_scholarly_publication_store().add_version(publication_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-publication/publications/{publication_id}/identifiers", dependencies=[Depends(require_backend_key)])
def scholarly_publication_identifier(publication_id: str, payload: PublicationIdentifierRequest) -> dict[str, Any]:
    try:
        return get_scholarly_publication_store().add_identifier(publication_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-publication/publications/{publication_id}/state", dependencies=[Depends(require_backend_key)])
def scholarly_publication_state(publication_id: str, payload: PublicationStateTransitionRequest) -> dict[str, Any]:
    try:
        return get_scholarly_publication_store().transition(publication_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-publication/publications/{publication_id}/citation-exports", dependencies=[Depends(require_backend_key)])
def scholarly_publication_citations(publication_id: str) -> dict[str, Any]:
    try:
        return get_scholarly_publication_store().citation_exports(publication_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-publication/publications/{publication_id}/readiness", dependencies=[Depends(require_backend_key)])
def scholarly_publication_readiness(publication_id: str) -> dict[str, Any]:
    try:
        return get_scholarly_publication_store().readiness(publication_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-publication/publications/{publication_id}/knowledge-library-handoffs", dependencies=[Depends(require_backend_key)])
def scholarly_publication_handoff(publication_id: str, payload: PublicationHandoffRequest) -> dict[str, Any]:
    try:
        return get_scholarly_publication_store().knowledge_library_handoff(publication_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-publication/publications/{publication_id}/packages/freeze", dependencies=[Depends(require_backend_key)])
def scholarly_publication_package(publication_id: str, payload: PublicationPackageFreezeRequest) -> dict[str, Any]:
    try:
        return get_scholarly_publication_store().freeze_package(publication_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-publication/publications/{publication_id}/events", dependencies=[Depends(require_backend_key)])
def scholarly_publication_events(publication_id: str, limit: int = 500) -> dict[str, Any]:
    try:
        return {"events": get_scholarly_publication_store().events(publication_id, limit)}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-publication/publications/{publication_id}/packages", dependencies=[Depends(require_backend_key)])
def scholarly_publication_packages(publication_id: str, limit: int = 100) -> dict[str, Any]:
    try:
        return {"packages": get_scholarly_publication_store().packages(publication_id, limit)}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-knowledge-graph/capabilities", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_capability_report() -> dict[str, Any]:
    return research_knowledge_graph_capabilities()

@router.post("/research-knowledge-graph/nodes", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_node(payload: KnowledgeGraphNodeRequest) -> dict[str, Any]:
    try:
        return get_research_knowledge_graph_store().upsert_node(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-knowledge-graph/edges", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_edge(payload: KnowledgeGraphEdgeRequest) -> dict[str, Any]:
    try:
        return get_research_knowledge_graph_store().add_edge(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-knowledge-graph/edge-proposals", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_proposal(payload: KnowledgeGraphProposalRequest) -> dict[str, Any]:
    try:
        return get_research_knowledge_graph_store().propose_edge(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-knowledge-graph/edge-proposals/{proposal_id}/decision", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_proposal_decision(proposal_id: str, payload: KnowledgeGraphProposalDecisionRequest) -> dict[str, Any]:
    try:
        return get_research_knowledge_graph_store().decide_proposal(proposal_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-knowledge-graph/publications/{publication_id}/materialize", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_materialize_publication(publication_id: str, payload: PublicationGraphMaterializationRequest) -> dict[str, Any]:
    try:
        return get_research_knowledge_graph_store().materialize_publication(publication_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-knowledge-graph/nodes/{node_ref:path}/neighborhood", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_neighborhood(node_ref: str, limit: int = 200) -> dict[str, Any]:
    try:
        return get_research_knowledge_graph_store().neighborhood(node_ref, limit)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-knowledge-graph/publications/{publication_id}/intelligence", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_publication_intelligence(publication_id: str) -> dict[str, Any]:
    try:
        return get_research_knowledge_graph_store().publication_intelligence(publication_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-knowledge-graph/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def research_knowledge_graph_snapshot(payload: KnowledgeGraphSnapshotRequest) -> dict[str, Any]:
    try:
        return get_research_knowledge_graph_store().freeze_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/ai-research-context/capabilities", dependencies=[Depends(require_backend_key)])
def ai_research_context_capability_report() -> dict[str, Any]:
    return ai_research_context_capabilities()

@router.post("/ai-research-context/contexts", dependencies=[Depends(require_backend_key)])
def ai_research_context_create(payload: AIResearchContextCreateRequest) -> dict[str, Any]:
    try:
        return get_ai_research_context_store().create_context(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/ai-research-context/contexts/{context_id}", dependencies=[Depends(require_backend_key)])
def ai_research_context_get(context_id: str) -> dict[str, Any]:
    try:
        return get_ai_research_context_store().get_context(context_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/ai-research-context/retrieval-runs", dependencies=[Depends(require_backend_key)])
def ai_research_context_register_run(payload: AIRetrievalRunCreateRequest) -> dict[str, Any]:
    try:
        return get_ai_research_context_store().register_run(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/ai-research-context/contexts/{context_id}/lineage", dependencies=[Depends(require_backend_key)])
def ai_research_context_lineage(context_id: str) -> dict[str, Any]:
    try:
        return get_ai_research_context_store().lineage(context_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/ai-research-context/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def ai_research_context_snapshot(payload: AIContextSnapshotRequest) -> dict[str, Any]:
    try:
        return get_ai_research_context_store().freeze_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/rag-evaluation/capabilities", dependencies=[Depends(require_backend_key)])
def rag_evaluation_capability_report() -> dict[str, Any]:
    return rag_evaluation_capabilities()

@router.post("/rag-evaluation/evaluations", dependencies=[Depends(require_backend_key)])
def rag_evaluation_create(payload: RAGEvaluationCreateRequest) -> dict[str, Any]:
    try:
        return get_rag_evaluation_store().create_evaluation(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/rag-evaluation/evaluations/{evaluation_id}", dependencies=[Depends(require_backend_key)])
def rag_evaluation_get(evaluation_id: str) -> dict[str, Any]:
    try:
        return get_rag_evaluation_store().get_evaluation(evaluation_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/rag-evaluation/evaluations/{evaluation_id}/cases", dependencies=[Depends(require_backend_key)])
def rag_evaluation_add_case(evaluation_id: str, payload: RAGEvaluationCaseRequest) -> dict[str, Any]:
    try:
        return get_rag_evaluation_store().add_case(evaluation_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/rag-evaluation/evaluations/{evaluation_id}/claim-assessments", dependencies=[Depends(require_backend_key)])
def rag_evaluation_add_claim_assessment(evaluation_id: str, payload: RAGClaimAssessmentRequest) -> dict[str, Any]:
    try:
        return get_rag_evaluation_store().add_claim_assessment(evaluation_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/rag-evaluation/evaluations/{evaluation_id}/citation-assessments", dependencies=[Depends(require_backend_key)])
def rag_evaluation_add_citation_assessment(evaluation_id: str, payload: RAGCitationAssessmentRequest) -> dict[str, Any]:
    try:
        return get_rag_evaluation_store().add_citation_assessment(evaluation_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/rag-evaluation/evaluations/{evaluation_id}/summary", dependencies=[Depends(require_backend_key)])
def rag_evaluation_summary(evaluation_id: str) -> dict[str, Any]:
    try:
        return get_rag_evaluation_store().summary(evaluation_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/rag-evaluation/comparisons", dependencies=[Depends(require_backend_key)])
def rag_evaluation_compare(payload: RAGEvaluationComparisonRequest) -> dict[str, Any]:
    try:
        return get_rag_evaluation_store().comparison(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/rag-evaluation/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def rag_evaluation_snapshot(payload: RAGEvaluationSnapshotRequest) -> dict[str, Any]:
    try:
        return get_rag_evaluation_store().freeze_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/ai-research-experiments/capabilities", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_capability_report() -> dict[str, Any]:
    return ai_research_experiment_capabilities()

@router.post("/ai-research-experiments/experiments", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_create(payload: AIResearchExperimentCreateRequest) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().create_experiment(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/ai-research-experiments/experiments/{experiment_id}", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_get(experiment_id: str) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().get_experiment(experiment_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/ai-research-experiments/experiments/{experiment_id}/trials", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_trial(experiment_id: str, payload: AIResearchTrialCreateRequest) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().add_trial(experiment_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/ai-research-experiments/experiments/{experiment_id}/execution-handoffs", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_handoff(experiment_id: str, payload: AIExperimentExecutionHandoffRequest) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().create_handoff(experiment_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/ai-research-experiments/experiments/{experiment_id}/run-receipts", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_receipt(experiment_id: str, payload: AIExperimentRunReceiptRequest) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().add_receipt(experiment_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/ai-research-experiments/experiments/{experiment_id}/evaluation-bindings", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_evaluation_binding(experiment_id: str, payload: AIExperimentEvaluationBindingRequest) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().add_evaluation_binding(experiment_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/ai-research-experiments/experiments/{experiment_id}/summary", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_summary(experiment_id: str) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().summary(experiment_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/ai-research-experiments/experiments/{experiment_id}/state", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_state(experiment_id: str, payload: AIExperimentStateRequest) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().set_state(experiment_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/ai-research-experiments/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def ai_research_experiment_snapshot(payload: AIExperimentSnapshotRequest) -> dict[str, Any]:
    try:
        return get_ai_research_experiment_store().freeze_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/model-aware-research/capabilities", dependencies=[Depends(require_backend_key)])
def model_aware_research_capabilities_route() -> dict[str, Any]:
    return model_aware_research_capabilities()

@router.post("/model-aware-research/records", dependencies=[Depends(require_backend_key)])
def model_aware_research_create(payload: ModelAwareResearchRecordRequest) -> dict[str, Any]:
    try:
        return get_model_aware_research_store().create_record(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/model-aware-research/records/{record_id}", dependencies=[Depends(require_backend_key)])
def model_aware_research_get(record_id: str) -> dict[str, Any]:
    try:
        return get_model_aware_research_store().get_record(record_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/model-aware-research/records/{record_id}/lineage", dependencies=[Depends(require_backend_key)])
def model_aware_research_lineage(record_id: str) -> dict[str, Any]:
    try:
        return get_model_aware_research_store().lineage(record_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/model-aware-research/records/{record_id}/exchange-readiness", dependencies=[Depends(require_backend_key)])
def model_aware_exchange_readiness(record_id: str, destination: str = Query(..., min_length=1)) -> dict[str, Any]:
    try:
        return get_model_aware_research_store().exchange_readiness(record_id, destination)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/cross-product-exchange/exchanges", dependencies=[Depends(require_backend_key)])
def cross_product_exchange_create(payload: CrossProductExchangeCreateRequest) -> dict[str, Any]:
    try:
        return get_model_aware_research_store().create_exchange(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/cross-product-exchange/exchanges/{exchange_id}", dependencies=[Depends(require_backend_key)])
def cross_product_exchange_get(exchange_id: str) -> dict[str, Any]:
    try:
        return get_model_aware_research_store().get_exchange(exchange_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/cross-product-exchange/exchanges/{exchange_id}/receipts", dependencies=[Depends(require_backend_key)])
def cross_product_exchange_receipt(exchange_id: str, payload: CrossProductExchangeReceiptRequest) -> dict[str, Any]:
    try:
        return get_model_aware_research_store().add_receipt(exchange_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/model-aware-research/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def model_aware_research_snapshot(payload: ModelAwareSnapshotRequest) -> dict[str, Any]:
    try:
        return get_model_aware_research_store().freeze_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-question-hypothesis/capabilities", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_capabilities_route() -> dict[str, Any]:
    return research_question_hypothesis_capabilities()

@router.post("/research-question-hypothesis/plans", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_create(payload: ResearchQuestionPlanCreateRequest) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().create(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-question-hypothesis/plans/{plan_id}", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_get(plan_id: str) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().get(plan_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-question-hypothesis/plans/{plan_id}/subquestions", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_add_subquestion(plan_id: str, payload: ResearchSubquestionAddRequest) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().add_subquestion(plan_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-question-hypothesis/plans/{plan_id}/hypotheses", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_add_hypothesis(plan_id: str, payload: ResearchHypothesisAddRequest) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().add_hypothesis(plan_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-question-hypothesis/plans/{plan_id}/evidence-requirements", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_add_evidence_requirement(plan_id: str, payload: ResearchEvidenceRequirementRequest) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().add_evidence_requirement(plan_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-question-hypothesis/plans/{plan_id}/review-state", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_review_state(plan_id: str, payload: ResearchQuestionReviewStateRequest) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().set_review_state(plan_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-question-hypothesis/plans/{plan_id}/readiness", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_readiness(plan_id: str) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().readiness(plan_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-question-hypothesis/plans/{plan_id}/core-candidates", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_core_candidates(plan_id: str) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().core_candidates(plan_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/research-question-hypothesis/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def research_question_hypothesis_snapshot(payload: ResearchQuestionSnapshotRequest) -> dict[str, Any]:
    try:
        return get_research_question_hypothesis_store().freeze_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/research-design-methodology/capabilities", dependencies=[Depends(require_backend_key)])
def research_design_methodology_capabilities_route() -> dict[str, Any]:
    return research_design_methodology_capabilities()

@router.post("/research-design-methodology/plans", dependencies=[Depends(require_backend_key)])
def research_design_methodology_create(payload: ResearchDesignPlanCreateRequest) -> dict[str, Any]:
    try: return get_research_design_methodology_store().create(payload)
    except Exception as exc: raise _translate(exc) from exc

@router.get("/research-design-methodology/plans/{plan_id}", dependencies=[Depends(require_backend_key)])
def research_design_methodology_get(plan_id: str) -> dict[str, Any]:
    try: return get_research_design_methodology_store().get(plan_id)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/research-design-methodology/plans/{plan_id}/candidates", dependencies=[Depends(require_backend_key)])
def research_design_methodology_add_candidate(plan_id: str, payload: MethodologyCandidateAddRequest) -> dict[str, Any]:
    try: return get_research_design_methodology_store().add_candidate(plan_id, payload)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/research-design-methodology/plans/{plan_id}/validity-threats", dependencies=[Depends(require_backend_key)])
def research_design_methodology_add_validity_threat(plan_id: str, payload: ResearchDesignValidityThreatRequest) -> dict[str, Any]:
    try: return get_research_design_methodology_store().add_validity_threat(plan_id, payload)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/research-design-methodology/plans/{plan_id}/preference", dependencies=[Depends(require_backend_key)])
def research_design_methodology_preference(plan_id: str, payload: ResearchDesignPreferenceRequest) -> dict[str, Any]:
    try: return get_research_design_methodology_store().set_preference(plan_id, payload)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/research-design-methodology/plans/{plan_id}/review-state", dependencies=[Depends(require_backend_key)])
def research_design_methodology_review_state(plan_id: str, payload: ResearchDesignReviewStateRequest) -> dict[str, Any]:
    try: return get_research_design_methodology_store().set_review_state(plan_id, payload)
    except Exception as exc: raise _translate(exc) from exc

@router.get("/research-design-methodology/plans/{plan_id}/comparison", dependencies=[Depends(require_backend_key)])
def research_design_methodology_comparison(plan_id: str) -> dict[str, Any]:
    try: return get_research_design_methodology_store().comparison(plan_id)
    except Exception as exc: raise _translate(exc) from exc

@router.get("/research-design-methodology/plans/{plan_id}/readiness", dependencies=[Depends(require_backend_key)])
def research_design_methodology_readiness(plan_id: str) -> dict[str, Any]:
    try: return get_research_design_methodology_store().readiness(plan_id)
    except Exception as exc: raise _translate(exc) from exc

@router.get("/research-design-methodology/plans/{plan_id}/execution-handoffs", dependencies=[Depends(require_backend_key)])
def research_design_methodology_execution_handoffs(plan_id: str) -> dict[str, Any]:
    try: return get_research_design_methodology_store().execution_handoffs(plan_id)
    except Exception as exc: raise _translate(exc) from exc

@router.get("/research-design-methodology/plans/{plan_id}/core-candidate", dependencies=[Depends(require_backend_key)])
def research_design_methodology_core_candidate(plan_id: str) -> dict[str, Any]:
    try: return get_research_design_methodology_store().core_candidate(plan_id)
    except Exception as exc: raise _translate(exc) from exc

@router.post("/research-design-methodology/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def research_design_methodology_snapshot(payload: ResearchDesignSnapshotRequest) -> dict[str, Any]:
    try: return get_research_design_methodology_store().freeze_snapshot(payload)
    except Exception as exc: raise _translate(exc) from exc


@router.get("/evidence-search-strategy/capabilities", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_capabilities_route() -> dict[str, Any]:
    return evidence_search_strategy_capabilities()

@router.post("/evidence-search-strategy/strategies", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_create(payload: EvidenceSearchStrategyCreateRequest) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().create(payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/evidence-search-strategy/strategies/{strategy_id}", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_get(strategy_id: str) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().get(strategy_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/evidence-search-strategy/strategies/{strategy_id}/concepts", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_add_concept(strategy_id: str, payload: SearchConceptAddRequest) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().add_concept(strategy_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/evidence-search-strategy/strategies/{strategy_id}/source-targets", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_add_source_target(strategy_id: str, payload: SearchSourceTargetAddRequest) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().add_source_target(strategy_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/evidence-search-strategy/strategies/{strategy_id}/queries", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_add_query(strategy_id: str, payload: SearchQueryAddRequest) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().add_query(strategy_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/evidence-search-strategy/strategies/{strategy_id}/criteria", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_add_criterion(strategy_id: str, payload: SearchEligibilityCriterionRequest) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().add_criterion(strategy_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/evidence-search-strategy/strategies/{strategy_id}/execution-receipts", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_add_receipt(strategy_id: str, payload: SearchExecutionReceiptRequest) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().add_execution_receipt(strategy_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/evidence-search-strategy/strategies/{strategy_id}/review-state", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_review_state(strategy_id: str, payload: EvidenceSearchReviewStateRequest) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().set_review_state(strategy_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/evidence-search-strategy/strategies/{strategy_id}/coverage", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_coverage(strategy_id: str) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().coverage(strategy_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/evidence-search-strategy/strategies/{strategy_id}/readiness", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_readiness(strategy_id: str) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().readiness(strategy_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/evidence-search-strategy/strategies/{strategy_id}/execution-handoffs", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_handoffs(strategy_id: str) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().execution_handoffs(strategy_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/evidence-search-strategy/strategies/{strategy_id}/core-candidate", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_core_candidate(strategy_id: str) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().core_candidate(strategy_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/evidence-search-strategy/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def evidence_search_strategy_snapshot(payload: EvidenceSearchSnapshotRequest) -> dict[str, Any]:
    try: return get_evidence_search_strategy_store().freeze_snapshot(payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/systematic-review-evidence-synthesis/capabilities", dependencies=[Depends(require_backend_key)])
def systematic_review_evidence_synthesis_capabilities_route() -> dict[str, Any]:
    return systematic_review_evidence_synthesis_capabilities()

@router.post("/systematic-review-evidence-synthesis/reviews", dependencies=[Depends(require_backend_key)])
def systematic_review_create(payload: SystematicReviewCreateRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().create(payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/systematic-review-evidence-synthesis/reviews/{review_id}", dependencies=[Depends(require_backend_key)])
def systematic_review_get(review_id: str) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().get(review_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/systematic-review-evidence-synthesis/reviews/{review_id}/candidates", dependencies=[Depends(require_backend_key)])
def systematic_review_add_candidate(review_id: str, payload: ReviewCandidateAddRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().add_candidate(review_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/systematic-review-evidence-synthesis/reviews/{review_id}/screening-decisions", dependencies=[Depends(require_backend_key)])
def systematic_review_screen(review_id: str, payload: ReviewScreeningDecisionRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().screen(review_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/systematic-review-evidence-synthesis/reviews/{review_id}/extractions", dependencies=[Depends(require_backend_key)])
def systematic_review_extract(review_id: str, payload: ReviewExtractionRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().add_extraction(review_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/systematic-review-evidence-synthesis/reviews/{review_id}/bias-assessments", dependencies=[Depends(require_backend_key)])
def systematic_review_bias(review_id: str, payload: ReviewBiasAssessmentRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().add_bias_assessment(review_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/systematic-review-evidence-synthesis/reviews/{review_id}/evidence-grades", dependencies=[Depends(require_backend_key)])
def systematic_review_grade(review_id: str, payload: ReviewEvidenceGradeRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().add_evidence_grade(review_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/systematic-review-evidence-synthesis/reviews/{review_id}/synthesis-plans", dependencies=[Depends(require_backend_key)])
def systematic_review_synthesis_plan(review_id: str, payload: ReviewSynthesisPlanRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().add_synthesis_plan(review_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/systematic-review-evidence-synthesis/reviews/{review_id}/review-state", dependencies=[Depends(require_backend_key)])
def systematic_review_state(review_id: str, payload: SystematicReviewStateRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().set_review_state(review_id,payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/systematic-review-evidence-synthesis/reviews/{review_id}/flow", dependencies=[Depends(require_backend_key)])
def systematic_review_flow(review_id: str) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().flow(review_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/systematic-review-evidence-synthesis/reviews/{review_id}/extraction-matrix", dependencies=[Depends(require_backend_key)])
def systematic_review_extraction_matrix(review_id: str) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().extraction_matrix(review_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/systematic-review-evidence-synthesis/reviews/{review_id}/readiness", dependencies=[Depends(require_backend_key)])
def systematic_review_readiness(review_id: str) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().readiness(review_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/systematic-review-evidence-synthesis/reviews/{review_id}/synthesis-handoffs", dependencies=[Depends(require_backend_key)])
def systematic_review_handoffs(review_id: str) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().synthesis_handoffs(review_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/systematic-review-evidence-synthesis/reviews/{review_id}/core-candidate", dependencies=[Depends(require_backend_key)])
def systematic_review_core_candidate(review_id: str) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().core_candidate(review_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.post("/systematic-review-evidence-synthesis/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def systematic_review_snapshot(payload: SystematicReviewSnapshotRequest) -> dict[str, Any]:
    try: return get_systematic_review_evidence_synthesis_store().freeze_snapshot(payload)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/unified-research-environment/capabilities", dependencies=[Depends(require_backend_key)])
def unified_research_environment_capabilities_route() -> dict[str, Any]:
    return unified_scholarly_ai_environment_capabilities()

@router.post("/unified-research-environment/environments", dependencies=[Depends(require_backend_key)])
def unified_research_environment_create(payload: UnifiedResearchEnvironmentCreateRequest) -> dict[str, Any]:
    try:
        return get_unified_scholarly_ai_environment_store().create(payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/unified-research-environment/environments/{environment_id}", dependencies=[Depends(require_backend_key)])
def unified_research_environment_get(environment_id: str) -> dict[str, Any]:
    try:
        return get_unified_scholarly_ai_environment_store().get(environment_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/unified-research-environment/environments/{environment_id}/bindings", dependencies=[Depends(require_backend_key)])
def unified_research_environment_bind(environment_id: str, payload: UnifiedResearchEnvironmentBindingRequest) -> dict[str, Any]:
    try:
        return get_unified_scholarly_ai_environment_store().bind(environment_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/unified-research-environment/environments/{environment_id}/lineage", dependencies=[Depends(require_backend_key)])
def unified_research_environment_lineage(environment_id: str) -> dict[str, Any]:
    try:
        return get_unified_scholarly_ai_environment_store().lineage(environment_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/unified-research-environment/environments/{environment_id}/readiness", dependencies=[Depends(require_backend_key)])
def unified_research_environment_readiness(environment_id: str) -> dict[str, Any]:
    try:
        return get_unified_scholarly_ai_environment_store().readiness(environment_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/unified-research-environment/environments/{environment_id}/dossier", dependencies=[Depends(require_backend_key)])
def unified_research_environment_dossier(environment_id: str) -> dict[str, Any]:
    try:
        return get_unified_scholarly_ai_environment_store().dossier(environment_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/unified-research-environment/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def unified_research_environment_snapshot(payload: UnifiedResearchEnvironmentSnapshotRequest) -> dict[str, Any]:
    try:
        return get_unified_scholarly_ai_environment_store().freeze_snapshot(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/scholarly-validation/capabilities", dependencies=[Depends(require_backend_key)])
def scholarly_validation_capabilities() -> dict[str, Any]:
    return peer_review_capabilities()

@router.get("/scholarly-validation/studies/{study_id}", dependencies=[Depends(require_backend_key)])
def scholarly_validation_get(study_id: str) -> dict[str, Any]:
    try:
        return get_peer_review_store().get(study_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-validation/studies/{study_id}/rounds", dependencies=[Depends(require_backend_key)])
def scholarly_validation_round(study_id: str, payload: ReviewRoundCreateRequest) -> dict[str, Any]:
    try:
        item, replayed = get_peer_review_store().create_round(study_id, payload)
        return {"round": item, "idempotent_replay": replayed}
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-validation/studies/{study_id}/rounds/{round_id}/assignments", dependencies=[Depends(require_backend_key)])
def scholarly_validation_assignment(study_id: str, round_id: str, payload: ReviewerAssignmentRequest) -> dict[str, Any]:
    try:
        return get_peer_review_store().assign_reviewer(study_id, round_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-validation/studies/{study_id}/rounds/{round_id}/reviews", dependencies=[Depends(require_backend_key)])
def scholarly_validation_review(study_id: str, round_id: str, payload: StructuredPeerReviewRequest) -> dict[str, Any]:
    try:
        return get_peer_review_store().submit_review(study_id, round_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-validation/studies/{study_id}/responses", dependencies=[Depends(require_backend_key)])
def scholarly_validation_response(study_id: str, payload: AuthorResponseRequest) -> dict[str, Any]:
    try:
        return get_peer_review_store().add_response(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-validation/studies/{study_id}/revisions", dependencies=[Depends(require_backend_key)])
def scholarly_validation_revision(study_id: str, payload: RevisionSubmissionRequest) -> dict[str, Any]:
    try:
        return get_peer_review_store().add_revision(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-validation/studies/{study_id}/replications", dependencies=[Depends(require_backend_key)])
def scholarly_validation_replication(study_id: str, payload: ReplicationAttemptRequest) -> dict[str, Any]:
    try:
        return get_peer_review_store().add_replication(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-validation/studies/{study_id}/editorial-decisions", dependencies=[Depends(require_backend_key)])
def scholarly_validation_decision(study_id: str, payload: EditorialDecisionRequest) -> dict[str, Any]:
    try:
        return get_peer_review_store().add_decision(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-validation/studies/{study_id}/readiness", dependencies=[Depends(require_backend_key)])
def scholarly_validation_readiness(study_id: str) -> dict[str, Any]:
    try:
        return get_peer_review_store().readiness(study_id)
    except Exception as exc:
        raise _translate(exc) from exc

@router.post("/scholarly-validation/studies/{study_id}/packages/freeze", dependencies=[Depends(require_backend_key)])
def scholarly_validation_package_freeze(study_id: str, payload: PeerReviewPackageFreezeRequest) -> dict[str, Any]:
    try:
        return get_peer_review_store().freeze_package(study_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-validation/studies/{study_id}/events", dependencies=[Depends(require_backend_key)])
def scholarly_validation_events(study_id: str, limit: int = 500) -> dict[str, Any]:
    try:
        return {"events": get_peer_review_store().events(study_id, limit)}
    except Exception as exc:
        raise _translate(exc) from exc

@router.get("/scholarly-validation/studies/{study_id}/packages", dependencies=[Depends(require_backend_key)])
def scholarly_validation_packages(study_id: str, limit: int = 100) -> dict[str, Any]:
    try:
        return {"packages": get_peer_review_store().packages(study_id, limit)}
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/scholarly-literature-intelligence/capabilities", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_capabilities_route() -> dict[str, Any]:
    return scholarly_literature_intelligence_capabilities()

@router.post("/scholarly-literature-intelligence/projects", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_create(req: LiteratureIntelligenceCreateRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().create(req)

@router.get("/scholarly-literature-intelligence/projects/{intelligence_id}", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_get(intelligence_id: str) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().get(intelligence_id)

@router.post("/scholarly-literature-intelligence/projects/{intelligence_id}/works", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_add_work(intelligence_id: str, req: LiteratureWorkAddRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().add_work(intelligence_id, req)

@router.post("/scholarly-literature-intelligence/projects/{intelligence_id}/citation-contexts", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_add_citation_context(intelligence_id: str, req: CitationContextAddRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().add_citation_context(intelligence_id, req)

@router.post("/scholarly-literature-intelligence/projects/{intelligence_id}/literature-strands", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_add_strand(intelligence_id: str, req: LiteratureStrandAddRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().add_strand(intelligence_id, req)

@router.post("/scholarly-literature-intelligence/projects/{intelligence_id}/gaps", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_add_gap(intelligence_id: str, req: LiteratureGapAddRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().add_gap(intelligence_id, req)

@router.post("/scholarly-literature-intelligence/projects/{intelligence_id}/seminal-candidates", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_add_seminal_candidate(intelligence_id: str, req: SeminalCandidateAddRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().add_seminal_candidate(intelligence_id, req)

@router.post("/scholarly-literature-intelligence/projects/{intelligence_id}/related-work-candidates", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_add_related_candidate(intelligence_id: str, req: RelatedWorkCandidateAddRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().add_related_work_candidate(intelligence_id, req)

@router.post("/scholarly-literature-intelligence/projects/{intelligence_id}/related-work-decisions", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_decide_related(intelligence_id: str, req: RelatedWorkDecisionRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().decide_related_work(intelligence_id, req)

@router.post("/scholarly-literature-intelligence/projects/{intelligence_id}/review-state", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_state(intelligence_id: str, req: LiteratureIntelligenceStateRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().set_state(intelligence_id, req)

@router.get("/scholarly-literature-intelligence/projects/{intelligence_id}/landscape", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_landscape(intelligence_id: str) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().landscape(intelligence_id)

@router.get("/scholarly-literature-intelligence/projects/{intelligence_id}/citation-matrix", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_citation_matrix(intelligence_id: str) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().citation_matrix(intelligence_id)

@router.get("/scholarly-literature-intelligence/projects/{intelligence_id}/graph-handoffs", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_graph_handoffs(intelligence_id: str) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().graph_handoffs(intelligence_id)

@router.get("/scholarly-literature-intelligence/projects/{intelligence_id}/readiness", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_readiness(intelligence_id: str) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().readiness(intelligence_id)

@router.get("/scholarly-literature-intelligence/projects/{intelligence_id}/core-candidate", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_core_candidate(intelligence_id: str) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().core_candidate(intelligence_id)

@router.post("/scholarly-literature-intelligence/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def scholarly_literature_intelligence_snapshot(req: LiteratureIntelligenceSnapshotRequest) -> dict[str, Any]:
    return get_scholarly_literature_intelligence_store().freeze_snapshot(req)


@router.get("/argument-claim-counterclaim-intelligence/capabilities", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_capabilities_route() -> dict[str, Any]:
    return argument_claim_counterclaim_intelligence_capabilities()

@router.post("/argument-claim-counterclaim-intelligence/projects", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_create(req: ArgumentIntelligenceCreateRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().create(req)

@router.get("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_get(argument_intelligence_id: str) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().get(argument_intelligence_id)

@router.post("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/claims", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_add_claim(argument_intelligence_id: str, req: ArgumentClaimAddRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().add_claim(argument_intelligence_id, req)

@router.post("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/evidence-links", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_add_evidence_link(argument_intelligence_id: str, req: ClaimEvidenceLinkRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().add_evidence_link(argument_intelligence_id, req)

@router.post("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/claim-relations", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_add_relation(argument_intelligence_id: str, req: ClaimRelationAddRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().add_claim_relation(argument_intelligence_id, req)

@router.post("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/assumptions", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_add_assumption(argument_intelligence_id: str, req: ClaimAssumptionAddRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().add_assumption(argument_intelligence_id, req)

@router.post("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/claim-decisions", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_decide_claim(argument_intelligence_id: str, req: ClaimDecisionRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().decide_claim(argument_intelligence_id, req)

@router.post("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/tensions", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_add_tension(argument_intelligence_id: str, req: ArgumentTensionAddRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().add_tension(argument_intelligence_id, req)

@router.post("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/review-state", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_state(argument_intelligence_id: str, req: ArgumentIntelligenceStateRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().set_state(argument_intelligence_id, req)

@router.get("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/claim-evidence-matrix", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_matrix(argument_intelligence_id: str) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().claim_evidence_matrix(argument_intelligence_id)

@router.get("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/argument-map", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_map(argument_intelligence_id: str) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().argument_map(argument_intelligence_id)

@router.get("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/contradiction-register", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_contradictions(argument_intelligence_id: str) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().contradiction_register(argument_intelligence_id)

@router.get("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/argument-synthesis-handoff", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_handoff(argument_intelligence_id: str) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().argument_synthesis_handoff(argument_intelligence_id)

@router.get("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/readiness", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_readiness(argument_intelligence_id: str) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().readiness(argument_intelligence_id)

@router.get("/argument-claim-counterclaim-intelligence/projects/{argument_intelligence_id}/core-candidate", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_core_candidate(argument_intelligence_id: str) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().core_candidate(argument_intelligence_id)

@router.post("/argument-claim-counterclaim-intelligence/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def argument_claim_counterclaim_intelligence_snapshot(req: ArgumentIntelligenceSnapshotRequest) -> dict[str, Any]:
    return get_argument_claim_counterclaim_intelligence_store().freeze_snapshot(req)


@router.get("/research-gap-novelty-intelligence/capabilities", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_capabilities_route() -> dict[str, Any]:
    return research_gap_novelty_intelligence_capabilities()

@router.post("/research-gap-novelty-intelligence/projects", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_create(req: ResearchGapNoveltyCreateRequest) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().create(req)

@router.get("/research-gap-novelty-intelligence/projects/{gap_novelty_id}", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_get(gap_novelty_id: str) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().get(gap_novelty_id)

@router.post("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/gap-candidates", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_add_gap(gap_novelty_id: str, req: ResearchGapCandidateAddRequest) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().add_gap_candidate(gap_novelty_id, req)

@router.post("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/gap-decisions", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_decide_gap(gap_novelty_id: str, req: ResearchGapDecisionRequest) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().decide_gap(gap_novelty_id, req)

@router.post("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/novelty-candidates", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_add_novelty(gap_novelty_id: str, req: NoveltyCandidateAddRequest) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().add_novelty_candidate(gap_novelty_id, req)

@router.post("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/novelty-decisions", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_decide_novelty(gap_novelty_id: str, req: NoveltyDecisionRequest) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().decide_novelty(gap_novelty_id, req)

@router.post("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/research-opportunities", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_add_opportunity(gap_novelty_id: str, req: OriginalResearchOpportunityAddRequest) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().add_research_opportunity(gap_novelty_id, req)

@router.post("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/state", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_state(gap_novelty_id: str, req: ResearchGapNoveltyStateRequest) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().set_state(gap_novelty_id, req)

@router.get("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/structural-signals", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_signals(gap_novelty_id: str) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().structural_signals(gap_novelty_id)

@router.get("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/landscape", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_landscape(gap_novelty_id: str) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().landscape(gap_novelty_id)

@router.get("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/research-planning-handoff", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_handoff(gap_novelty_id: str) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().research_planning_handoff(gap_novelty_id)

@router.get("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/readiness", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_readiness(gap_novelty_id: str) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().readiness(gap_novelty_id)

@router.get("/research-gap-novelty-intelligence/projects/{gap_novelty_id}/core-candidate", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_core_candidate(gap_novelty_id: str) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().core_candidate(gap_novelty_id)

@router.post("/research-gap-novelty-intelligence/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def research_gap_novelty_intelligence_snapshot(req: ResearchGapNoveltySnapshotRequest) -> dict[str, Any]:
    return get_research_gap_novelty_intelligence_store().freeze_snapshot(req)

@router.get("/dataset-discovery-data-fitness/capabilities", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_capabilities_route() -> dict[str, Any]: return dataset_discovery_data_fitness_capabilities()

@router.post("/dataset-discovery-data-fitness/projects", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_create(req: DatasetFitnessCreateRequest) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().create(req)

@router.get("/dataset-discovery-data-fitness/projects/{data_fitness_id}", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_get(data_fitness_id: str) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().get(data_fitness_id)

@router.post("/dataset-discovery-data-fitness/projects/{data_fitness_id}/requirements", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_requirement(data_fitness_id: str, req: DataRequirementAddRequest) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().add_requirement(data_fitness_id,req)

@router.post("/dataset-discovery-data-fitness/projects/{data_fitness_id}/datasets", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_dataset(data_fitness_id: str, req: DatasetCandidateAddRequest) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().add_dataset(data_fitness_id,req)

@router.post("/dataset-discovery-data-fitness/projects/{data_fitness_id}/variables", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_variable(data_fitness_id: str, req: DatasetVariableAddRequest) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().add_variable(data_fitness_id,req)

@router.post("/dataset-discovery-data-fitness/projects/{data_fitness_id}/assessments", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_assess(data_fitness_id: str, req: DatasetFitnessAssessmentRequest) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().assess(data_fitness_id,req)

@router.post("/dataset-discovery-data-fitness/projects/{data_fitness_id}/state", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_state(data_fitness_id: str, req: DatasetFitnessStateRequest) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().set_state(data_fitness_id,req)

@router.get("/dataset-discovery-data-fitness/projects/{data_fitness_id}/coverage-matrix", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_coverage(data_fitness_id: str) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().coverage_matrix(data_fitness_id)

@router.get("/dataset-discovery-data-fitness/projects/{data_fitness_id}/landscape", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_landscape(data_fitness_id: str) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().landscape(data_fitness_id)

@router.get("/dataset-discovery-data-fitness/projects/{data_fitness_id}/readiness", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_readiness(data_fitness_id: str) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().readiness(data_fitness_id)

@router.get("/dataset-discovery-data-fitness/projects/{data_fitness_id}/computational-planning-handoff", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_handoff(data_fitness_id: str) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().computational_planning_handoff(data_fitness_id)

@router.get("/dataset-discovery-data-fitness/projects/{data_fitness_id}/core-candidate", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_core(data_fitness_id: str) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().core_candidate(data_fitness_id)

@router.post("/dataset-discovery-data-fitness/snapshots/freeze", dependencies=[Depends(require_backend_key)])
def dataset_discovery_data_fitness_snapshot(req: DatasetFitnessSnapshotRequest) -> dict[str, Any]: return get_dataset_discovery_data_fitness_store().freeze_snapshot(req)
