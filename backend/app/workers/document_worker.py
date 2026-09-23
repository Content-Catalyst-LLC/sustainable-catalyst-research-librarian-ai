from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
import uuid

from ..async_jobs import get_job_store
from ..config import settings
from ..services.document_jobs import execute_job

logger = logging.getLogger(__name__)


class DocumentWorker:
    def __init__(self) -> None:
        self.worker_id = f"rl-{os.getpid()}-{uuid.uuid4().hex[:10]}"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if not settings.async_jobs_enabled or self.running:
            return
        store = get_job_store()
        store.reclaim_stalled(settings.async_job_lease_seconds)
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="sc-rl-document-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(2.0, settings.async_job_poll_seconds + 1.0))

    def _run(self) -> None:
        store = get_job_store()
        last_reclaim = 0.0
        while not self._stop.is_set():
            try:
                now = time.monotonic()
                if now - last_reclaim >= settings.async_job_reclaim_interval_seconds:
                    store.reclaim_stalled(settings.async_job_lease_seconds)
                    last_reclaim = now
                claim = store.claim(self.worker_id, settings.async_job_lease_seconds)
                if claim is None:
                    self._stop.wait(settings.async_job_poll_seconds)
                    continue

                def progress(stage: str, percent: int) -> None:
                    store.heartbeat(claim.job_id, claim.worker_id, stage, percent, settings.async_job_lease_seconds)

                try:
                    result = asyncio.run(execute_job(claim, progress))
                    store.succeed(claim.job_id, claim.worker_id, result)
                except Exception as exc:
                    logger.exception("Research Librarian async job failed: %s", claim.job_id)
                    store.fail(
                        claim.job_id,
                        claim.worker_id,
                        str(exc),
                        retry_base_seconds=settings.async_job_retry_base_seconds,
                    )
            except Exception:
                logger.exception("Research Librarian async worker loop error")
                self._stop.wait(max(1.0, settings.async_job_poll_seconds))


worker = DocumentWorker()
