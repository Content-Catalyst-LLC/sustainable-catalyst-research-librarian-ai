from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

from ..async_jobs import JobClaim
from ..models import KnowledgeRecord
from ..config import settings
from ..provider import embeddings_configured, generate_embedding
from ..store import store

Progress = Callable[[str, int], None]


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _record_payload(payload: dict[str, Any]) -> dict[str, Any]:
    source = dict(payload.get("record") or payload.get("document") or payload)
    content = _text(source.get("content") or source.get("text") or source.get("body"))
    title = _text(source.get("title")) or "Untitled research source"
    url = _text(source.get("url")) or f"urn:sc:research-source:{hashlib.sha256((title + content).encode()).hexdigest()[:24]}"
    record_id = _text(source.get("id")) or "doc-" + hashlib.sha256((url + "\n" + content).encode()).hexdigest()[:32]
    source.update({"id": record_id, "title": title, "url": url, "content": content})
    source.setdefault("source", _text(payload.get("source")) or "async-document-runtime")
    source.setdefault("post_type", "research-source")
    source.setdefault("metadata", {})
    source["metadata"] = {**dict(source.get("metadata") or {}), "async_processing": True}
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
        reason="async-document-processing-v8.3.0",
        defer_commit=False,
    )

    # Postgres activation can be incremental. Drive bounded steps from the worker,
    # preserving the store's restart-safe state machine rather than bypassing it.
    commit_steps = 0
    if not result.committed and result.state not in {"completed", "completed-with-rejections"}:
        progress("activate-index", 55)
        try:
            store.queue_sync_commit(sync_id, "async-document-processing-v8.3.0")
            for _ in range(200):
                status = store.advance_sync_commit(sync_id, "async-document-processing-v8.3.0")
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


async def execute_job(claim: JobClaim, progress: Progress) -> dict[str, Any]:
    if claim.job_type in {"document-process", "ingestion"}:
        return await process_document_job(claim, progress)
    if claim.job_type == "validation":
        return await process_validation_job(claim, progress)
    raise ValueError(
        f"Job type {claim.job_type!r} is registered for the durable queue but has no v8.3 executor yet; "
        "use document-process, ingestion, or validation."
    )
