from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from .. import __version__
from ..async_jobs import get_job_store
from ..contracts.documents import DocumentParseRequest
from ..document_intelligence import DOCUMENT_INTELLIGENCE_SCHEMA, knowledge_metadata, parse_document

router = APIRouter(prefix="/v1/documents", tags=["document-intelligence"])
_registered = False


def register_authenticated_routes(require_key: Any) -> None:
    global _registered
    if _registered:
        return
    _registered = True

    @router.get("/capabilities", dependencies=[Depends(require_key)])
    def capabilities() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "schema": DOCUMENT_INTELLIGENCE_SCHEMA,
            "formats": ["text/plain", "text/markdown", "text/html", "application/pdf"],
            "extracts": ["sections", "page-provenance", "references", "citation-mentions", "doi", "arxiv", "pmid", "isbn", "urls", "tables", "figures", "equations"],
            "deterministic": True,
            "ocr": False,
            "llm_required": False,
            "platform_core_governs_promoted_evidence": True,
        }

    @router.post("/parse", dependencies=[Depends(require_key)])
    def parse(payload: DocumentParseRequest) -> dict[str, Any]:
        try:
            result = parse_document(
                content=payload.content,
                content_bytes=payload.decoded_bytes(),
                media_type=payload.media_type,
                filename=payload.filename,
                source_url=payload.source_url,
                title_hint=payload.title,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "version": __version__, "document": result, "knowledge_metadata": knowledge_metadata(result)}

    @router.post("/parse/async", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_key)])
    def parse_async(payload: DocumentParseRequest) -> dict[str, Any]:
        job_payload = payload.model_dump()
        job, duplicate = get_job_store().enqueue("document-intelligence", job_payload, priority=100, max_attempts=3)
        return {"ok": True, "version": __version__, "duplicate": duplicate, "job": job}
