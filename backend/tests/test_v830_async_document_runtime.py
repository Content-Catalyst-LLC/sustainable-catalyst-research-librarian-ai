import asyncio
from pathlib import Path

import app.async_jobs as async_jobs
import app.services.document_jobs as document_jobs
from app.async_jobs import AsyncJobStore
from app.store import KnowledgeStore


def test_sqlite_queue_is_idempotent_and_lease_safe(tmp_path: Path) -> None:
    queue = AsyncJobStore(tmp_path / "jobs.sqlite3")
    first, duplicate = queue.enqueue(
        "validation", {"scope": "index"}, idempotency_key="validate-index-once", max_attempts=3
    )
    second, replay = queue.enqueue(
        "validation", {"scope": "index"}, idempotency_key="validate-index-once", max_attempts=3
    )
    assert duplicate is False
    assert replay is True
    assert first["job_id"] == second["job_id"]
    assert first["storage_backend"] == "sqlite"

    claim = queue.claim("worker-test", 60)
    assert claim is not None
    assert claim.job_id == first["job_id"]
    assert claim.attempts == 1
    queue.heartbeat(claim.job_id, claim.worker_id, "validate", 55, 60)
    completed = queue.succeed(claim.job_id, claim.worker_id, {"ok": True})
    assert completed["state"] == "succeeded"
    assert completed["progress"] == 100
    assert queue.summary()["states"]["succeeded"] == 1
    assert {event["event_type"] for event in queue.events(claim.job_id)} >= {"enqueued", "claimed", "succeeded"}


def test_failed_job_is_retried_then_can_be_cancelled(tmp_path: Path) -> None:
    queue = AsyncJobStore(tmp_path / "jobs.sqlite3")
    job, _ = queue.enqueue("validation", {}, max_attempts=2)
    claim = queue.claim("worker-retry", 60)
    assert claim is not None
    retrying = queue.fail(claim.job_id, claim.worker_id, "temporary", retry_base_seconds=0.1)
    assert retrying["state"] == "retry_wait"
    cancelled = queue.cancel(job["job_id"])
    assert cancelled["state"] == "cancelled"
    queued = queue.retry(job["job_id"])
    assert queued["state"] == "queued"


def test_document_job_normalizes_indexes_and_validates(monkeypatch, tmp_path: Path) -> None:
    local = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    monkeypatch.setattr(document_jobs, "store", local)

    class Claim:
        job_id = "job-doc-test"
        job_type = "document-process"
        attempts = 1
        max_attempts = 3
        worker_id = "worker-doc-test"
        payload = {
            "document": {
                "id": "paper:carbon-1",
                "title": "Carbon Systems Evidence",
                "url": "https://example.test/carbon-systems",
                "content": "Carbon accounting requires transparent boundaries and reproducible source lineage.",
            },
            "source_site": "test-suite",
            "embed": False,
        }

    stages = []
    result = asyncio.run(document_jobs.process_document_job(Claim(), lambda stage, progress: stages.append((stage, progress))))
    assert result["indexed"] is True
    assert result["record_id"] == "paper:carbon-1"
    assert local.records()[0].title == "Carbon Systems Evidence"
    assert [stage for stage, _ in stages] == ["normalize", "stage-index", "validate"]


def test_async_job_postgres_contract_uses_skip_locked() -> None:
    source = Path(async_jobs.__file__).read_text(encoding="utf-8")
    assert "FOR UPDATE SKIP LOCKED" in source
    assert "sc_rl_async_jobs" in source
    assert "lease_expires_utc" in source
