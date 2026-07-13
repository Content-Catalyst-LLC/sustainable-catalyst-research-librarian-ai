from pathlib import Path

from app.models import KnowledgeRecord
from app.store import KnowledgeStore


def record(record_id: str, title: str, summary: str = "") -> KnowledgeRecord:
    return KnowledgeRecord(
        id=record_id,
        title=title,
        url=f"https://sustainablecatalyst.com/{record_id}/",
        slug=record_id,
        summary=summary,
        content=f"Content for {title}. {summary}",
        source="wordpress",
    )


def make_store(tmp_path: Path) -> KnowledgeStore:
    return KnowledgeStore(tmp_path / "knowledge_index.sqlite3")


def test_multibatch_replace_is_atomic(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.sync([record("old", "Old Record")], "replace", "https://example.test", "seed", 1, 1, [])

    first = store.sync(
        [record("new-a", "New A")],
        "replace",
        "https://example.test",
        "replace-job",
        1,
        2,
        [],
    )
    assert first.committed is False
    assert first.state == "staging"
    assert [item.id for item in store.records()] == ["old"]

    final = store.sync(
        [record("new-b", "New B")],
        "replace",
        "https://example.test",
        "replace-job",
        2,
        2,
        ["old"],
    )
    assert final.committed is True
    assert final.state == "completed"
    assert {item.id for item in store.records()} == {"new-a", "new-b"}
    assert final.deleted == 1
    assert store.summary()["snapshot_count"] >= 1


def test_completed_job_is_idempotent(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    first = store.sync([record("a", "A")], "replace", "https://example.test", "same-job", 1, 1, [])
    first_version = first.summary["index_version"]
    duplicate = store.sync([record("a", "A")], "replace", "https://example.test", "same-job", 1, 1, [])
    assert duplicate.duplicate_batch is True
    assert duplicate.summary["index_version"] == first_version
    assert len(store.records()) == 1


def test_upsert_delete_and_tombstone(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.sync(
        [record("a", "A", "first"), record("b", "B")],
        "replace",
        "https://example.test",
        "seed",
        1,
        1,
        [],
    )
    result = store.sync(
        [record("a", "A", "updated")],
        "upsert",
        "https://example.test",
        "incremental",
        1,
        1,
        ["b"],
    )
    assert result.updated == 1
    assert result.deleted == 1
    assert [item.id for item in store.records()] == ["a"]
    assert store.manifest()["tombstone_count"] == 1


def test_unchanged_hash_is_detected(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    item = record("a", "A")
    store.sync([item], "replace", "https://example.test", "seed", 1, 1, [])
    result = store.sync([item], "upsert", "https://example.test", "unchanged", 1, 1, [])
    assert result.unchanged == 1
    assert result.updated == 0


def test_runtime_snapshot_rollback(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.sync([record("a", "A")], "replace", "https://example.test", "seed-a", 1, 1, [])
    store.sync([record("b", "B")], "replace", "https://example.test", "replace-b", 1, 1, [])
    snapshots = store.list_snapshots()
    target = next(snapshot for snapshot in snapshots if snapshot["record_count"] == 1)
    result = store.rollback(target["snapshot_id"])
    assert result["ok"] is True
    restored_ids = {item.id for item in store.records()}
    assert restored_ids in ({"a"}, {"b"})
    # The snapshot generated before replace-b must restore A. If another one-record
    # safety snapshot is first, choose by its reason and verify exactly.
    before_replace = next(snapshot for snapshot in snapshots if "before:replace-b" in snapshot["reason"])
    store.rollback(before_replace["snapshot_id"])
    assert {item.id for item in store.records()} == {"a"}


def test_out_of_order_batches_wait_for_complete_job(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.sync([record("old", "Old")], "replace", "https://example.test", "seed", 1, 1, [])

    last_first = store.sync(
        [record("new-b", "New B")],
        "replace",
        "https://example.test",
        "out-of-order",
        2,
        2,
        [],
    )
    assert last_first.committed is False
    assert {item.id for item in store.records()} == {"old"}

    completes = store.sync(
        [record("new-a", "New A")],
        "replace",
        "https://example.test",
        "out-of-order",
        1,
        2,
        [],
    )
    assert completes.committed is True
    assert {item.id for item in store.records()} == {"new-a", "new-b"}


def test_legacy_json_index_migrates_once(tmp_path: Path) -> None:
    legacy = tmp_path / "knowledge_index.json"
    legacy.write_text(
        '{"schema":"sc-research-librarian-knowledge-index/2.0",'
        '"meta":{"source_site":"https://legacy.example","last_sync_utc":"2026-07-12T00:00:00Z"},'
        '"records":[{"id":"legacy","title":"Legacy Record",'
        '"url":"https://legacy.example/record/","summary":"Migrated from JSON."}]}',
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    assert {item.id for item in store.records()} == {"legacy"}
    assert store.summary()["source_site"] == "https://legacy.example"
    assert not legacy.exists()
    assert (tmp_path / "knowledge_index.json.migrated").exists()


def test_invalid_record_is_isolated_and_existing_record_is_preserved(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.sync([record("keep", "Keep")], "replace", "https://example.test", "seed-keep", 1, 1, [])
    result = store.sync(
        [
            {"id": "new", "title": "New", "url": "https://example.test/new/"},
            {"id": "keep", "title": "", "url": "https://example.test/keep/"},
        ],
        "replace",
        "https://example.test",
        "isolated-failure",
        1,
        1,
        [],
    )
    assert result.committed is True
    assert result.rejected == 1
    assert result.state == "completed-with-rejections"
    assert {item.id for item in store.records()} == {"keep", "new"}
    assert store.job_rejections("isolated-failure")[0]["record_id"] == "keep"


def test_stalled_job_repair_purges_staging(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    first = store.sync(
        [record("partial", "Partial")],
        "replace",
        "https://example.test",
        "stalled-job",
        1,
        2,
        [],
    )
    assert first.committed is False
    with store._connection() as connection:
        connection.execute(
            "UPDATE sync_jobs SET updated_utc='2000-01-01T00:00:00+00:00' WHERE job_id='stalled-job'"
        )
    repaired = store.repair_stalled_jobs(300, purge_staging=True)
    assert repaired["count"] == 1
    manifest = store.manifest()
    job = next(item for item in manifest["recent_jobs"] if item["job_id"] == "stalled-job")
    assert job["state"] == "stalled"
    assert job["staged_records"] == 1  # historical count remains visible
    with store._connection() as connection:
        assert connection.execute("SELECT COUNT(*) FROM staging_records WHERE job_id='stalled-job'").fetchone()[0] == 0


def test_runtime_snapshot_integrity_is_reported(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.sync([record("a", "A")], "replace", "https://example.test", "seed-integrity", 1, 1, [])
    store.sync([record("b", "B")], "replace", "https://example.test", "replace-integrity", 1, 1, [])
    snapshots = store.list_snapshots()
    assert snapshots
    assert all("integrity_ok" in item for item in snapshots)
    assert store.validate_snapshots()["invalid_count"] == 0
