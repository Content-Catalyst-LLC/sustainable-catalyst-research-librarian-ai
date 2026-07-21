from pathlib import Path

from app.models import KnowledgeRecord
from app.store import KnowledgeStore


def record(record_id: str, words: int = 160) -> KnowledgeRecord:
    return KnowledgeRecord(
        id=record_id,
        title=f"Record {record_id}",
        url=f"https://sustainablecatalyst.com/{record_id}/",
        slug=record_id,
        summary="Durable incremental activation test.",
        content=(f"Evidence for {record_id}. " * words),
        source="wordpress",
    )


def test_incremental_activation_survives_store_restarts(tmp_path: Path) -> None:
    path = tmp_path / "knowledge.sqlite3"
    store = KnowledgeStore(path)
    store.sync([record("previous", 5)], "replace", "https://example.test", "seed", 1, 1, [])

    incoming = [record(f"new-{index:03d}") for index in range(135)]
    batches = [incoming[index : index + 45] for index in range(0, len(incoming), 45)]
    for index, batch in enumerate(batches, start=1):
        result = store.sync(
            batch,
            "replace",
            "https://example.test",
            "durable-job",
            index,
            len(batches),
            [],
            defer_commit=True,
        )
    assert result.state == "ready-to-commit"
    assert {item.id for item in store.records()} == {"previous"}

    queued = store.queue_sync_commit("durable-job")
    assert queued["commit_phase"] == "preparing"
    observed_phases: set[str] = set()
    for step in range(200):
        if step % 3 == 0:
            store = KnowledgeStore(path)  # simulate a Render process restart
        status = store.advance_sync_commit("durable-job")
        observed_phases.add(status["commit_phase"])
        if not status["committed"]:
            # The previous active index remains readable until the atomic switch.
            assert {item.id for item in store.records()} == {"previous"}
        if status["committed"]:
            break
    else:
        raise AssertionError("durable activation did not complete")

    assert {"copying-records", "building-chunks", "checksumming", "switching", "completed"}.issubset(observed_phases)
    assert status["activation_records"] == 135
    assert status["chunk_records_processed"] == 135
    assert status["checksum_records"] == 135
    assert status["indexed_chunks"] > 135
    assert status["activation_step_count"] > 5
    assert {item.id for item in store.records()} == {item.id for item in incoming}


def test_queue_upgrades_legacy_v706_activation_state(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge.sqlite3")
    store.sync([record("new")], "replace", "https://example.test", "legacy-job", 1, 1, [], defer_commit=True)
    with store._connection() as connection:  # intentional migration fixture
        connection.execute(
            "UPDATE sync_jobs SET state='committing',commit_phase='activating',commit_progress=10 WHERE job_id='legacy-job'"
        )
    queued = store.queue_sync_commit("legacy-job")
    assert queued["commit_phase"] == "preparing"
    assert queued["activation_restart_count"] == 1
    committed = store.commit_sync_job("legacy-job")
    assert committed["committed"] is True
    assert {item.id for item in store.records()} == {"new"}
