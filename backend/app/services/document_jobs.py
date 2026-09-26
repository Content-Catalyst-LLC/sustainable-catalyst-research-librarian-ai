from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

from ..async_jobs import JobClaim
from ..models import KnowledgeRecord
from ..config import settings
from ..provider import embeddings_configured, generate_embedding
from ..store import store
from ..document_intelligence import knowledge_metadata, parse_document
from ..source_identity import get_source_graph_store
from ..contracts.research_intelligence_extraction import ResearchIntelligenceExtractionRequest
from ..contracts.argument_synthesis import ArgumentSynthesisPlanRequest
from ..contracts.statistical_research import StatisticalAnalysisPlanRequest
from ..contracts.visual_research import VisualResearchPlanRequest
from ..contracts.unified_research_runtime import UnifiedResearchRuntimeExecutionRequest
from .research_intelligence_extraction import extract_candidates
from .argument_synthesis import build_plan as build_argument_synthesis_plan
from .statistical_research import build_plan as build_statistical_analysis_plan
from .visual_research import build_plan as build_visual_research_plan
from .unified_research_runtime import execute_safe_runtime
from .research_workflow import get_research_workflow_store
from ..contracts.research_workflow import ResearchWorkflowAdvanceRequest
from ..contracts.scholarly_research import ScholarlyPackageFreezeRequest
from .scholarly_research import get_scholarly_research_store
from ..contracts.peer_review import PeerReviewPackageFreezeRequest
from ..contracts.scholarly_publication import PublicationPackageFreezeRequest
from .peer_review import get_peer_review_store
from .scholarly_publication import get_scholarly_publication_store
from .research_knowledge_graph import get_research_knowledge_graph_store
from ..contracts.research_knowledge_graph import KnowledgeGraphSnapshotRequest
from ..contracts.ai_research_context import AIContextSnapshotRequest
from .ai_research_context import get_ai_research_context_store
from ..contracts.rag_evaluation import RAGEvaluationSnapshotRequest
from .rag_evaluation import get_rag_evaluation_store
from ..contracts.ai_research_experiment import AIExperimentSnapshotRequest
from .ai_research_experiment import get_ai_research_experiment_store
from ..contracts.model_aware_exchange import ModelAwareSnapshotRequest
from .model_aware_exchange import get_model_aware_research_store
from ..contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentSnapshotRequest
from .unified_scholarly_ai_environment import get_unified_scholarly_ai_environment_store
from ..contracts.research_question_hypothesis import ResearchQuestionSnapshotRequest
from .research_question_hypothesis import get_research_question_hypothesis_store
from ..contracts.research_design_methodology import ResearchDesignSnapshotRequest
from .research_design_methodology import get_research_design_methodology_store
from ..contracts.evidence_search_strategy import EvidenceSearchSnapshotRequest
from .evidence_search_strategy import get_evidence_search_strategy_store
from ..contracts.systematic_review_evidence_synthesis import SystematicReviewSnapshotRequest
from .systematic_review_evidence_synthesis import get_systematic_review_evidence_synthesis_store
from ..contracts.scholarly_literature_intelligence import LiteratureIntelligenceSnapshotRequest
from .scholarly_literature_intelligence import get_scholarly_literature_intelligence_store
from ..contracts.argument_claim_counterclaim_intelligence import ArgumentIntelligenceSnapshotRequest
from .argument_claim_counterclaim_intelligence import get_argument_claim_counterclaim_intelligence_store
from ..contracts.research_gap_novelty_intelligence import ResearchGapNoveltySnapshotRequest
from .research_gap_novelty_intelligence import get_research_gap_novelty_intelligence_store
from ..contracts.dataset_discovery_data_fitness import DatasetFitnessSnapshotRequest
from .dataset_discovery_data_fitness import get_dataset_discovery_data_fitness_store
from ..contracts.computational_research_planning import ComputationalResearchPlanSnapshotRequest
from .computational_research_planning import get_computational_research_planning_store

Progress = Callable[[str, int], None]


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _record_payload(payload: dict[str, Any]) -> dict[str, Any]:
    source = dict(payload.get("record") or payload.get("document") or payload)
    content = _text(source.get("content") or source.get("text") or source.get("body"))
    media_type = _text(source.get("media_type") or source.get("content_type") or "text/plain")
    filename = _text(source.get("filename"))
    content_bytes = None
    if source.get("content_base64"):
        import base64
        try:
            content_bytes = base64.b64decode(str(source.get("content_base64") or ""), validate=True)
        except Exception as exc:
            raise ValueError("document content_base64 is invalid") from exc
        if len(content_bytes) > 20 * 1024 * 1024:
            raise ValueError("decoded document exceeds the 20 MiB processing limit")
    title_hint = _text(source.get("title"))
    provisional = title_hint or filename or "Untitled research source"
    url = _text(source.get("url")) or f"urn:sc:research-source:{hashlib.sha256((provisional + content).encode()).hexdigest()[:24]}"
    intelligence = None
    try:
        intelligence = parse_document(content=content, content_bytes=content_bytes, media_type=media_type, filename=filename, source_url=url, title_hint=title_hint)
        parsed_text = "\n\n".join(str(item.get("text") or "") for item in intelligence.get("sections", []))
        if parsed_text:
            content = _text(parsed_text)[:60000]
        title = _text(intelligence.get("title")) or provisional
    except ValueError:
        title = provisional
    record_id = _text(source.get("id")) or "doc-" + hashlib.sha256((url + "\n" + content).encode()).hexdigest()[:32]
    source.update({"id": record_id, "title": title, "url": url, "content": content})
    try:
        if intelligence is None:
            intelligence = parse_document(content=content, media_type=media_type, filename=filename, source_url=url, title_hint=title)
        if intelligence.get("sections"):
            source["headings"] = [str(item.get("heading") or "") for item in intelligence["sections"] if item.get("heading")][:100]
        source["metadata"] = {**dict(source.get("metadata") or {}), **knowledge_metadata(intelligence)}
        source_meta = dict(source.get("metadata") or {})
        identity = get_source_graph_store().resolve({
            "parsed_document": intelligence,
            "title": title,
            "authors": source.get("authors") or intelligence.get("authors") or [],
            "institutions": source.get("institutions") or source_meta.get("institutions") or [],
            "publication_year": source.get("publication_year") or source.get("year") or source_meta.get("publication_year") or source_meta.get("year"),
            "identifiers": source.get("identifiers") or {},
            "source_url": url,
            "filename": filename,
            "media_type": media_type,
            "content_fingerprint": intelligence.get("fingerprint", ""),
            "version_label": source.get("version_label") or source_meta.get("version_label") or "",
            "metadata": {"library_record_id": record_id},
        })
        source["metadata"]["source_identity"] = {
            "schema": identity.get("schema", ""),
            "canonical_source_id": identity.get("canonical_source_id", ""),
            "resolution": identity.get("resolution", ""),
            "citation_edges": int((identity.get("citations") or {}).get("created", 0)),
        }
    except ValueError:
        source.setdefault("metadata", {})
    source.setdefault("source", _text(payload.get("source")) or "async-document-runtime")
    source.setdefault("post_type", "research-source")
    source.setdefault("metadata", {})
    source["metadata"] = {**dict(source.get("metadata") or {}), "async_processing": True, "document_intelligence_version": "8.5.0", "source_identity_version": "8.6.0"}
    return KnowledgeRecord.model_validate(source).model_dump()


async def process_document_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    payload = claim.payload
    progress("normalize", 10)
    record = _record_payload(payload)
    if not record.get("content") and not record.get("summary"):
        raise ValueError("Document jobs require content/text/body or a summary.")

    progress("stage-index", 35)
    sync_id = f"async-{claim.job_id}"
    result = store.sync(
        records=[record],
        mode="upsert",
        source_site=str(payload.get("source_site") or "async-python-runtime"),
        job_id=sync_id,
        batch_index=1,
        batch_count=1,
        deleted_ids=[],
        reason="async-document-processing-v8.6.0",
        defer_commit=False,
    )

    # Postgres activation can be incremental. Drive bounded steps from the worker,
    # preserving the store's restart-safe state machine rather than bypassing it.
    commit_steps = 0
    if not result.committed and result.state not in {"completed", "completed-with-rejections"}:
        progress("activate-index", 55)
        try:
            store.queue_sync_commit(sync_id, "async-document-processing-v8.6.0")
            for _ in range(200):
                status = store.advance_sync_commit(sync_id, "async-document-processing-v8.6.0")
                commit_steps += 1
                state = str(status.get("state") or "")
                if state in {"completed", "completed-with-rejections"}:
                    break
                if state in {"failed", "stalled"}:
                    raise RuntimeError(str(status.get("error") or f"Index activation entered {state}."))
            else:
                raise RuntimeError("Index activation exceeded the bounded worker step limit.")
        except AttributeError:
            pass

    embedded = False
    embedding_error = ""
    if bool(payload.get("embed", False)) and embeddings_configured():
        progress("embed", 78)
        try:
            chunks = [chunk for chunk in store.pending_chunks(250, settings.gemini_embedding_model) if str(chunk.record_id) == str(record["id"])]
            for chunk in chunks:
                embedding = await generate_embedding(chunk.passage, "RETRIEVAL_DOCUMENT")
                store.save_chunk_embedding(chunk.chunk_id, settings.gemini_embedding_model, embedding)
            embedded = bool(chunks)
        except Exception as exc:  # Embedding is optional for an ingestion job.
            embedding_error = str(exc)[:1000]

    progress("validate", 92)
    matches = [item for item in store.records() if str(item.id) == str(record["id"])]
    if not matches:
        raise RuntimeError("Document activation completed but the indexed record could not be read back.")

    summary = store.summary()
    return {
        "record_id": record["id"],
        "title": record["title"],
        "url": record["url"],
        "sync_job_id": sync_id,
        "sync_state": result.state,
        "commit_steps": commit_steps,
        "indexed": True,
        "embedded": embedded,
        "embedding_error": embedding_error,
        "index_version": int(summary.get("index_version", 0)),
        "storage_engine": str(summary.get("storage_engine", "sqlite")),
    }


async def process_validation_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("validate-runtime", 50)
    summary = store.summary()
    progress("validate-complete", 95)
    return {
        "ok": True,
        "total_records": int(summary.get("total_records", 0)),
        "indexed_chunks": int(summary.get("indexed_chunks", 0)),
        "storage_engine": str(summary.get("storage_engine", "sqlite")),
        "database_ready": bool(summary.get("database_ready", True)),
    }


async def process_document_intelligence_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    import base64
    payload = claim.payload
    progress("extract", 20)
    content_bytes = base64.b64decode(str(payload.get("content_base64") or "")) if payload.get("content_base64") else None
    result = parse_document(
        content=str(payload.get("content") or ""),
        content_bytes=content_bytes,
        media_type=str(payload.get("media_type") or "text/plain"),
        filename=str(payload.get("filename") or ""),
        source_url=str(payload.get("source_url") or ""),
        title_hint=str(payload.get("title") or ""),
    )
    progress("structure", 70)
    progress("complete", 95)
    return {"document": result, "knowledge_metadata": knowledge_metadata(result)}


async def process_source_identity_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("normalize-identity", 20)
    payload = dict(claim.payload or {})
    progress("resolve-canonical-source", 55)
    result = get_source_graph_store().resolve(payload, register_citations=bool(payload.get("register_citations", True)))
    progress("citation-graph", 90)
    return result


async def process_research_intelligence_extraction_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("normalize-evidence", 20)
    request = ResearchIntelligenceExtractionRequest.model_validate(claim.payload)
    progress("extract-candidates", 55)
    result = extract_candidates(request)
    progress("review-queue-ready", 95)
    return result


async def process_argument_synthesis_plan_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("normalize-reviewed-objects", 20)
    request = ArgumentSynthesisPlanRequest.model_validate(claim.payload)
    progress("assemble-declared-argument", 60)
    result = build_argument_synthesis_plan(request)
    progress("review-queue-ready", 95)
    return result


async def process_statistical_analysis_plan_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("normalize-research-context", 20)
    request = StatisticalAnalysisPlanRequest.model_validate(claim.payload)
    progress("assemble-analysis-plan", 60)
    result = build_statistical_analysis_plan(request)
    progress("runtime-handoff-ready", 95)
    return result


async def process_visual_research_plan_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("normalize-visual-research-context", 20)
    request = VisualResearchPlanRequest.model_validate(claim.payload)
    progress("assemble-renderer-neutral-visual-plan", 60)
    result = build_visual_research_plan(request)
    progress("human-review-ready", 95)
    return result


async def process_unified_research_runtime_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("normalize-unified-research-run", 15)
    request = UnifiedResearchRuntimeExecutionRequest.model_validate(claim.payload)
    progress("execute-safe-research-stages", 55)
    result = execute_safe_runtime(request)
    progress("reproducible-run-manifest-ready", 95)
    return result


async def process_research_workflow_advance_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-workflow-checkpoint", 20)
    workflow_id = str(claim.payload.get("workflow_id") or "").strip()
    if not workflow_id:
        raise ValueError("workflow_id is required")
    request = ResearchWorkflowAdvanceRequest.model_validate(claim.payload.get("advance") or {})
    progress("reconcile-stage-jobs", 55)
    result = get_research_workflow_store().advance(workflow_id, request)
    progress("workflow-checkpoint-ready", 95)
    return result


async def process_scholarly_research_package_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-scholarly-study", 20)
    study_id = str(claim.payload.get("study_id") or "").strip()
    if not study_id:
        raise ValueError("study_id is required")
    request = ScholarlyPackageFreezeRequest.model_validate(claim.payload.get("freeze") or {})
    progress("evaluate-publication-readiness", 50)
    store = get_scholarly_research_store()
    store.readiness(study_id)
    progress("freeze-reproducibility-package", 80)
    result = store.freeze_package(study_id, request)
    progress("scholarly-package-ready", 95)
    return result


async def process_peer_review_validation_package_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-peer-review-record", 20)
    study_id = str(claim.payload.get("study_id") or "").strip()
    if not study_id:
        raise ValueError("study_id is required")
    request = PeerReviewPackageFreezeRequest.model_validate(claim.payload.get("freeze") or {})
    store = get_peer_review_store()
    progress("evaluate-review-readiness", 50)
    store.readiness(study_id)
    progress("freeze-peer-review-validation-package", 80)
    result = store.freeze_package(study_id, request)
    progress("peer-review-validation-package-ready", 95)
    return result


async def process_scholarly_publication_package_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-scholarly-publication", 20)
    publication_id = str(claim.payload.get("publication_id") or "").strip()
    if not publication_id:
        raise ValueError("publication_id is required")
    request = PublicationPackageFreezeRequest.model_validate(claim.payload.get("freeze") or {})
    store = get_scholarly_publication_store()
    progress("evaluate-dissemination-readiness", 50)
    store.readiness(publication_id)
    progress("freeze-scholarly-publication-package", 80)
    result = store.freeze_package(publication_id, request)
    progress("scholarly-publication-package-ready", 95)
    return result




async def process_research_knowledge_graph_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-research-knowledge-graph", 20)
    request = KnowledgeGraphSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_research_knowledge_graph_store()
    progress("assemble-accepted-graph", 55)
    progress("freeze-research-knowledge-graph-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("research-knowledge-graph-snapshot-ready", 95)
    return result


async def process_ai_research_context_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-ai-research-context", 20)
    request = AIContextSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_ai_research_context_store()
    progress("assemble-ai-context-lineage", 55)
    store.lineage(request.context_id)
    progress("freeze-ai-research-context-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("ai-research-context-snapshot-ready", 95)
    return result

async def process_rag_evaluation_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-rag-evaluation", 20)
    request = RAGEvaluationSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_rag_evaluation_store()
    progress("assemble-rag-evaluation", 55)
    store.summary(request.evaluation_id)
    progress("freeze-rag-evaluation-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("rag-evaluation-snapshot-ready", 95)
    return result

async def process_ai_research_experiment_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-ai-research-experiment", 20)
    request = AIExperimentSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_ai_research_experiment_store()
    progress("assemble-ai-research-experiment", 55)
    store.summary(request.experiment_id)
    progress("freeze-ai-research-experiment-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("ai-research-experiment-snapshot-ready", 95)
    return result

async def process_model_aware_research_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-model-aware-research", 20)
    request = ModelAwareSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_model_aware_research_store()
    progress("assemble-model-aware-lineage", 55)
    store.lineage(request.record_id)
    progress("freeze-model-aware-research-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("model-aware-research-snapshot-ready", 95)
    return result

async def process_unified_research_environment_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-unified-research-environment", 20)
    request = UnifiedResearchEnvironmentSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_unified_scholarly_ai_environment_store()
    progress("assemble-unified-research-dossier", 55)
    store.dossier(request.environment_id)
    progress("freeze-unified-research-environment-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("unified-research-environment-snapshot-ready", 95)
    return result

async def process_research_question_hypothesis_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-research-question-hypothesis-plan", 20)
    request = ResearchQuestionSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_research_question_hypothesis_store()
    progress("assemble-research-question-hypothesis-intelligence", 55)
    store.readiness(request.plan_id)
    progress("freeze-research-question-hypothesis-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("research-question-hypothesis-snapshot-ready", 95)
    return result

async def process_research_design_methodology_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-research-design-methodology-plan", 20)
    request = ResearchDesignSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_research_design_methodology_store()
    progress("assemble-research-design-methodology-plan", 55)
    store.readiness(request.plan_id)
    progress("freeze-research-design-methodology-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("research-design-methodology-snapshot-ready", 95)
    return result

async def process_evidence_search_strategy_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-evidence-search-strategy", 20)
    request = EvidenceSearchSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_evidence_search_strategy_store()
    progress("assemble-evidence-search-strategy", 55)
    store.readiness(request.strategy_id)
    progress("freeze-evidence-search-strategy-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("evidence-search-strategy-snapshot-ready", 95)
    return result

async def process_systematic_review_evidence_synthesis_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-systematic-review-evidence-synthesis", 20)
    request = SystematicReviewSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_systematic_review_evidence_synthesis_store()
    progress("assemble-systematic-review-evidence-synthesis", 55)
    store.readiness(request.review_id)
    progress("freeze-systematic-review-evidence-synthesis-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("systematic-review-evidence-synthesis-snapshot-ready", 95)
    return result


async def process_scholarly_literature_intelligence_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-scholarly-literature-intelligence", 20)
    request = LiteratureIntelligenceSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_scholarly_literature_intelligence_store()
    progress("assemble-scholarly-literature-intelligence", 55)
    store.readiness(request.intelligence_id)
    progress("freeze-scholarly-literature-intelligence-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("scholarly-literature-intelligence-snapshot-ready", 95)
    return result


async def process_argument_claim_counterclaim_intelligence_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-argument-claim-counterclaim-intelligence", 20)
    request = ArgumentIntelligenceSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_argument_claim_counterclaim_intelligence_store()
    progress("assemble-argument-claim-counterclaim-intelligence", 55)
    store.readiness(request.argument_intelligence_id)
    progress("freeze-argument-claim-counterclaim-intelligence-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("argument-claim-counterclaim-intelligence-snapshot-ready", 95)
    return result

async def process_research_gap_novelty_intelligence_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-research-gap-novelty-intelligence", 20)
    request = ResearchGapNoveltySnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_research_gap_novelty_intelligence_store()
    progress("assemble-research-gap-novelty-intelligence", 55)
    store.readiness(request.gap_novelty_id)
    progress("freeze-research-gap-novelty-intelligence-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("research-gap-novelty-intelligence-snapshot-ready", 95)
    return result


async def process_dataset_discovery_data_fitness_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-dataset-discovery-data-fitness", 20)
    request = DatasetFitnessSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_dataset_discovery_data_fitness_store()
    progress("assemble-dataset-discovery-data-fitness", 55)
    store.readiness(request.data_fitness_id)
    progress("freeze-dataset-discovery-data-fitness-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("dataset-discovery-data-fitness-snapshot-ready", 95)
    return result

async def process_computational_research_planning_snapshot_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    progress("load-computational-research-planning", 20)
    request = ComputationalResearchPlanSnapshotRequest.model_validate(claim.payload.get("snapshot") or claim.payload)
    store = get_computational_research_planning_store()
    progress("assemble-computational-research-planning", 55)
    store.readiness(request.computational_plan_id)
    progress("freeze-computational-research-planning-snapshot", 80)
    result = store.freeze_snapshot(request)
    progress("computational-research-planning-snapshot-ready", 95)
    return result


async def execute_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    if claim.job_type in {"document-process", "ingestion"}:
        return await process_document_job(claim, progress)
    if claim.job_type == "document-intelligence":
        return await process_document_intelligence_job(claim, progress)
    if claim.job_type == "validation":
        return await process_validation_job(claim, progress)
    if claim.job_type == "source-identity":
        return await process_source_identity_job(claim, progress)
    if claim.job_type == "research-intelligence-extraction":
        return await process_research_intelligence_extraction_job(claim, progress)
    if claim.job_type == "argument-synthesis-plan":
        return await process_argument_synthesis_plan_job(claim, progress)
    if claim.job_type == "statistical-analysis-plan":
        return await process_statistical_analysis_plan_job(claim, progress)
    if claim.job_type == "visual-research-plan":
        return await process_visual_research_plan_job(claim, progress)
    if claim.job_type == "unified-research-runtime":
        return await process_unified_research_runtime_job(claim, progress)
    if claim.job_type == "research-workflow-advance":
        return await process_research_workflow_advance_job(claim, progress)
    if claim.job_type == "scholarly-research-package":
        return await process_scholarly_research_package_job(claim, progress)
    if claim.job_type == "peer-review-validation-package":
        return await process_peer_review_validation_package_job(claim, progress)
    if claim.job_type == "scholarly-publication-package":
        return await process_scholarly_publication_package_job(claim, progress)
    if claim.job_type == "research-knowledge-graph-snapshot":
        return await process_research_knowledge_graph_snapshot_job(claim, progress)
    if claim.job_type == "ai-research-context-snapshot":
        return await process_ai_research_context_snapshot_job(claim, progress)
    if claim.job_type == "rag-evaluation-snapshot":
        return await process_rag_evaluation_snapshot_job(claim, progress)
    if claim.job_type == "ai-research-experiment-snapshot":
        return await process_ai_research_experiment_snapshot_job(claim, progress)
    if claim.job_type == "model-aware-research-snapshot":
        return await process_model_aware_research_snapshot_job(claim, progress)
    if claim.job_type == "unified-research-environment-snapshot":
        return await process_unified_research_environment_snapshot_job(claim, progress)
    if claim.job_type == "research-question-hypothesis-snapshot":
        return await process_research_question_hypothesis_snapshot_job(claim, progress)
    if claim.job_type == "research-design-methodology-snapshot":
        return await process_research_design_methodology_snapshot_job(claim, progress)
    if claim.job_type == "evidence-search-strategy-snapshot":
        return await process_evidence_search_strategy_snapshot_job(claim, progress)
    if claim.job_type == "systematic-review-evidence-synthesis-snapshot":
        return await process_systematic_review_evidence_synthesis_snapshot_job(claim, progress)
    if claim.job_type == "scholarly-literature-intelligence-snapshot":
        return await process_scholarly_literature_intelligence_snapshot_job(claim, progress)
    if claim.job_type == "argument-claim-counterclaim-intelligence-snapshot":
        return await process_argument_claim_counterclaim_intelligence_snapshot_job(claim, progress)
    if claim.job_type == "research-gap-novelty-intelligence-snapshot":
        return await process_research_gap_novelty_intelligence_snapshot_job(claim, progress)
    if claim.job_type == "dataset-discovery-data-fitness-snapshot":
        return await process_dataset_discovery_data_fitness_snapshot_job(claim, progress)
    if claim.job_type == "computational-research-planning-snapshot":
        return await process_computational_research_planning_snapshot_job(claim, progress)
    raise ValueError(
        f"Job type {claim.job_type!r} is registered for the durable queue but has no v8.3 executor yet; "
        "use document-process, document-intelligence, source-identity, research-intelligence-extraction, argument-synthesis-plan, statistical-analysis-plan, visual-research-plan, unified-research-runtime, research-workflow-advance, scholarly-research-package, peer-review-validation-package, scholarly-publication-package, research-knowledge-graph-snapshot, ai-research-context-snapshot, rag-evaluation-snapshot, ai-research-experiment-snapshot, model-aware-research-snapshot, unified-research-environment-snapshot, research-question-hypothesis-snapshot, research-design-methodology-snapshot, evidence-search-strategy-snapshot, systematic-review-evidence-synthesis-snapshot, scholarly-literature-intelligence-snapshot, argument-claim-counterclaim-intelligence-snapshot, research-gap-novelty-intelligence-snapshot, dataset-discovery-data-fitness-snapshot, computational-research-planning-snapshot, ingestion, or validation."
    )
