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
        summary="Transaction reconciliation test.",
        content=f"Evidence for {record_id}.",
        source="wordpress",
    )


def test_empty_missing_list_is_not_treated_as_complete(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    with store._connection() as connection:
        connection.execute(
            "INSERT INTO sync_jobs(job_id,mode,source_site,state,batch_count,received_batches,started_utc,updated_utc,rejected_records) "
            "VALUES(?,?,?,?,?,?,?,?,0)",
            ("empty-shell", "replace", "https://example.test", "staging", 0, "[]", "now", "now"),
        )
    status = store.sync_job_status("empty-shell")
    assert status["missing_batches"] == []
    assert status["batch_manifest_state"] == "empty-shell"
    reconciled = store.reconcile_sync_job("empty-shell", expected_batch_count=24)
    assert reconciled["reconciliation_action"] == "replay-all"
    assert reconciled["transaction_state"] == "empty-shell"
    assert reconciled["complete_for_expected_count"] is False


def test_complete_manifest_activates_and_incomplete_manifest_replays_missing(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    store.sync([record("one")], "replace", "https://example.test", "complete", 1, 2, [], defer_commit=True)
    store.sync([record("two")], "replace", "https://example.test", "complete", 2, 2, [], defer_commit=True)
    complete = store.reconcile_sync_job("complete", expected_batch_count=2)
    assert complete["reconciliation_action"] == "activate"
    assert complete["transaction_state"] == "complete"
    assert complete["received_batch_count"] == 2

    store.sync([record("partial")], "replace", "https://example.test", "partial", 1, 3, [], defer_commit=True)
    partial = store.reconcile_sync_job("partial", expected_batch_count=3)
    assert partial["reconciliation_action"] == "replay-missing"
    assert partial["missing_batches"] == [2, 3]


def test_batch_count_mismatch_requires_full_replay(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    store.sync([record("one")], "replace", "https://example.test", "mismatch", 1, 1, [], defer_commit=True)
    reconciled = store.reconcile_sync_job("mismatch", expected_batch_count=24)
    assert reconciled["reconciliation_action"] == "replay-all"
    assert reconciled["transaction_state"] == "batch-count-mismatch"


def test_zero_batch_transaction_cannot_queue_activation(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    with store._connection() as connection:
        connection.execute(
            "INSERT INTO sync_jobs(job_id,mode,source_site,state,batch_count,received_batches,started_utc,updated_utc,rejected_records) "
            "VALUES(?,?,?,?,?,?,?,?,0)",
            ("zero", "replace", "https://example.test", "staging", 0, "[]", "now", "now"),
        )
    try:
        store.queue_sync_commit("zero")
    except ValueError as exc:
        assert "no staged source batches" in str(exc).lower()
    else:
        raise AssertionError("zero-batch transaction was allowed to activate")


def test_reconcile_api_reports_explicit_action() -> None:
    response = client.post(
        "/v1/knowledge/sync/jobs/nonexistent-v708/reconcile",
        headers=HEADERS,
        json={"expected_batch_count": 24, "recovery_generation": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "7.1.0"
    assert body["reconciliation_action"] == "replay-all"
    assert body["transaction_state"] == "missing"
    assert body["expected_batch_count"] == 24
    assert body["recovery_generation"] == 3
