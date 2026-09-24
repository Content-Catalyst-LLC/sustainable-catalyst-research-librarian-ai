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
    raise ValueError(
        f"Job type {claim.job_type!r} is registered for the durable queue but has no v8.3 executor yet; "
        "use document-process, document-intelligence, source-identity, research-intelligence-extraction, argument-synthesis-plan, statistical-analysis-plan, visual-research-plan, unified-research-runtime, ingestion, or validation."
    )
