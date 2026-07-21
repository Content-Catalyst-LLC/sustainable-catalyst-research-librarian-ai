from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models import KnowledgeRecord
from app.store import KnowledgeStore


client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def record(record_id: str) -> KnowledgeRecord:
    return KnowledgeRecord(
        id=record_id,
        title=f"Record {record_id}",
        url=f"https://sustainablecatalyst.com/{record_id}/",
        slug=record_id,
        summary="Asynchronous backend commit test.",
        content=f"Content for {record_id}.",
        source="wordpress",
    )


def test_store_defers_activation_until_explicit_commit(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge_index.sqlite3")
    store.sync([record("old")], "replace", "https://example.test", "seed", 1, 1, [])

    first = store.sync(
        [record("new-a")],
        "replace",
        "https://example.test",
        "async-commit-job",
        1,
        2,
        [],
        defer_commit=True,
    )
    assert first.committed is False
    assert {item.id for item in store.records()} == {"old"}

    final = store.sync(
        [record("new-b")],
        "replace",
        "https://example.test",
        "async-commit-job",
        2,
        2,
        ["old"],
        defer_commit=True,
    )
    assert final.committed is False
    assert final.state == "ready-to-commit"
    status = store.sync_job_status("async-commit-job")
    assert status["state"] == "ready-to-commit"
    assert status["missing_batches"] == []
    assert status["staged_records"] == 2
    assert {item.id for item in store.records()} == {"old"}

    queued = store.queue_sync_commit("async-commit-job")
    assert queued["state"] == "commit-queued"
    committed = store.commit_sync_job("async-commit-job")
    assert committed["committed"] is True
    assert committed["commit_phase"] == "completed"
    assert committed["commit_progress"] == 100
    assert committed["activation_records"] == 2
    assert {item.id for item in store.records()} == {"new-a", "new-b"}


def test_api_commit_endpoint_queues_fully_staged_transaction() -> None:
    job_id = "v706-api-async-commit"
    staged = client.post(
        "/v1/knowledge/sync",
        headers=HEADERS,
        json={
            "mode": "replace",
            "job_id": job_id,
            "batch_index": 1,
            "batch_count": 1,
            "defer_commit": True,
            "records": [
                {
                    "id": "v706-api-record",
                    "title": "v7.0.6 API Record",
                    "url": "https://sustainablecatalyst.com/v706-api-record/",
                }
            ],
        },
    )
    assert staged.status_code == 200
    assert staged.json()["committed"] is False
    assert staged.json()["state"] == "ready-to-commit"

    queued = client.post(f"/v1/knowledge/sync/jobs/{job_id}/commit", headers=HEADERS, json={})
    assert queued.status_code == 200
    status = client.get(f"/v1/knowledge/sync/jobs/{job_id}", headers=HEADERS)
    assert status.status_code == 200
    body = status.json()
    # TestClient completes Starlette background tasks before returning control.
    assert body["committed"] is True
    assert body["commit_phase"] == "completed"
    assert body["commit_progress"] == 100


def test_commit_endpoint_rejects_missing_batches() -> None:
    job_id = "v706-api-missing-batch"
    staged = client.post(
        "/v1/knowledge/sync",
        headers=HEADERS,
        json={
            "mode": "replace",
            "job_id": job_id,
            "batch_index": 1,
            "batch_count": 2,
            "defer_commit": True,
            "records": [
                {
                    "id": "v706-incomplete",
                    "title": "Incomplete",
                    "url": "https://sustainablecatalyst.com/v706-incomplete/",
                }
            ],
        },
    )
    assert staged.status_code == 200
    queued = client.post(f"/v1/knowledge/sync/jobs/{job_id}/commit", headers=HEADERS, json={})
    assert queued.status_code == 409
    assert "missing staged batch" in queued.json()["detail"].lower()
