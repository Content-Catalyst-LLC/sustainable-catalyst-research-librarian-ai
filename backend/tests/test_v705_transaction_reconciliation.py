from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def record(record_id: str) -> dict[str, str]:
    return {
        "id": record_id,
        "title": f"Record {record_id}",
        "url": f"https://sustainablecatalyst.com/{record_id}/",
        "slug": record_id,
        "summary": "Transaction reconciliation test record.",
    }


def test_transaction_status_reports_and_closes_missing_batch() -> None:
    job_id = "v705-status-missing-batch"
    first = client.post(
        "/v1/knowledge/sync",
        headers=HEADERS,
        json={
            "mode": "replace",
            "job_id": job_id,
            "batch_index": 1,
            "batch_count": 3,
            "records": [record("v705-a")],
        },
    )
    assert first.status_code == 200
    assert first.json()["committed"] is False

    third = client.post(
        "/v1/knowledge/sync",
        headers=HEADERS,
        json={
            "mode": "replace",
            "job_id": job_id,
            "batch_index": 3,
            "batch_count": 3,
            "records": [record("v705-c")],
        },
    )
    assert third.status_code == 200
    assert third.json()["committed"] is False

    status = client.get(f"/v1/knowledge/sync/jobs/{job_id}", headers=HEADERS)
    assert status.status_code == 200
    body = status.json()
    assert body["exists"] is True
    assert body["committed"] is False
    assert body["received_batches"] == [1, 3]
    assert body["missing_batches"] == [2]
    assert body["staged_records"] == 2

    second = client.post(
        "/v1/knowledge/sync",
        headers=HEADERS,
        json={
            "mode": "replace",
            "job_id": job_id,
            "batch_index": 2,
            "batch_count": 3,
            "records": [record("v705-b")],
        },
    )
    assert second.status_code == 200
    assert second.json()["committed"] is True

    committed = client.get(f"/v1/knowledge/sync/jobs/{job_id}", headers=HEADERS).json()
    assert committed["committed"] is True
    assert committed["missing_batches"] == []
    assert committed["received_batches"] == [1, 2, 3]


def test_incomplete_transaction_can_be_reset_for_durable_replay() -> None:
    job_id = "v705-reset-incomplete"
    staged = client.post(
        "/v1/knowledge/sync",
        headers=HEADERS,
        json={
            "mode": "replace",
            "job_id": job_id,
            "batch_index": 1,
            "batch_count": 2,
            "records": [record("v705-reset-a")],
        },
    )
    assert staged.status_code == 200
    assert staged.json()["committed"] is False

    reset = client.delete(f"/v1/knowledge/sync/jobs/{job_id}", headers=HEADERS)
    assert reset.status_code == 200
    assert reset.json()["reset"] is True

    status = client.get(f"/v1/knowledge/sync/jobs/{job_id}", headers=HEADERS)
    assert status.status_code == 200
    assert status.json()["exists"] is False
