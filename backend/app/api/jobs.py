from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import __version__
from ..async_jobs import JOB_RUNTIME_SCHEMA, get_job_store
from ..contracts.jobs import DocumentJobRequest, JobCreateRequest

router = APIRouter(prefix="/v1/jobs", tags=["asynchronous-jobs"])
_registered = False


def register_authenticated_routes(require_key: Any) -> None:
    global _registered
    if _registered:
        return
    _registered = True

    @router.get("/runtime", dependencies=[Depends(require_key)])
    def job_runtime() -> dict[str, Any]:
        return {"ok": True, "version": __version__, **get_job_store().summary()}

    @router.get("", dependencies=[Depends(require_key)])
    def list_jobs(
        state_filter: str = Query(default="", alias="state"),
        job_type: str = Query(default=""),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        store = get_job_store()
        return {"schema": JOB_RUNTIME_SCHEMA, "version": __version__, "jobs": store.list(state=state_filter, job_type=job_type, limit=limit)}

    @router.post("", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_key)])
    def create_job(payload: JobCreateRequest) -> dict[str, Any]:
        job, duplicate = get_job_store().enqueue(
            payload.job_type,
            payload.payload,
            priority=payload.priority,
            max_attempts=payload.max_attempts,
            idempotency_key=payload.idempotency_key,
        )
        return {"ok": True, "version": __version__, "duplicate": duplicate, "job": job}

    @router.post("/documents", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(require_key)])
    def create_document_job(payload: DocumentJobRequest) -> dict[str, Any]:
        job, duplicate = get_job_store().enqueue(
            "document-process",
            {"document": payload.document, "source_site": payload.source_site, "embed": payload.embed},
            priority=payload.priority,
            max_attempts=payload.max_attempts,
            idempotency_key=payload.idempotency_key,
        )
        return {"ok": True, "version": __version__, "duplicate": duplicate, "job": job}

    @router.get("/{job_id}", dependencies=[Depends(require_key)])
    def get_job(job_id: str) -> dict[str, Any]:
        try:
            return {"version": __version__, "job": get_job_store().get(job_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Async job not found.") from exc

    @router.get("/{job_id}/events", dependencies=[Depends(require_key)])
    def get_job_events(job_id: str, limit: int = Query(default=200, ge=1, le=1000)) -> dict[str, Any]:
        try:
            return {"version": __version__, "events": get_job_store().events(job_id, limit)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Async job not found.") from exc

    @router.post("/{job_id}/retry", dependencies=[Depends(require_key)])
    def retry_job(job_id: str) -> dict[str, Any]:
        try:
            return {"ok": True, "version": __version__, "job": get_job_store().retry(job_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Async job not found.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.delete("/{job_id}", dependencies=[Depends(require_key)])
    def cancel_job(job_id: str) -> dict[str, Any]:
        try:
            return {"ok": True, "version": __version__, "job": get_job_store().cancel(job_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Async job not found.") from exc
