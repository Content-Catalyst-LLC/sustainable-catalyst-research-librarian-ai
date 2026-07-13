from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterable, Iterator
import uuid

from .config import settings
from .models import KnowledgeRecord, utc_now


SCHEMA_VERSION = 3
INDEX_SCHEMA = "sc-research-librarian-knowledge-index/3.0"
SNAPSHOT_SCHEMA = "sc-research-librarian-runtime-snapshot/3.0"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_hash(record: KnowledgeRecord) -> str:
    if record.content_hash:
        return record.content_hash
    payload = record.model_dump(exclude={"embedding", "content_hash"})
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SyncResult:
    state: str
    committed: bool
    received: int
    accepted: int
    rejected: int
    inserted: int
    updated: int
    unchanged: int
    deleted: int
    staged_records: int
    staged_deletions: int
    duplicate_batch: bool
    summary: dict[str, Any]


class KnowledgeStore:
    """Transactional SQLite index with staged, idempotent multi-batch synchronization.

    SQLite is intentionally the runtime store, not the only durable source. WordPress
    owns a compressed canonical snapshot and can rehydrate this database after an
    ephemeral Render restart.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (settings.data_dir / "knowledge_index.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()
        self._migrate_legacy_json()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    updated_utc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_records_title ON records(title COLLATE NOCASE);
                CREATE INDEX IF NOT EXISTS idx_records_url ON records(url);
                CREATE TABLE IF NOT EXISTS sync_jobs (
                    job_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    source_site TEXT NOT NULL DEFAULT '',
                    state TEXT NOT NULL,
                    batch_count INTEGER NOT NULL DEFAULT 1,
                    received_batches TEXT NOT NULL DEFAULT '[]',
                    staged_records INTEGER NOT NULL DEFAULT 0,
                    staged_deletions INTEGER NOT NULL DEFAULT 0,
                    started_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL,
                    completed_utc TEXT NOT NULL DEFAULT '',
                    result TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS staging_records (
                    job_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    PRIMARY KEY(job_id, id),
                    FOREIGN KEY(job_id) REFERENCES sync_jobs(job_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS staging_deletions (
                    job_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    PRIMARY KEY(job_id, id),
                    FOREIGN KEY(job_id) REFERENCES sync_jobs(job_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS tombstones (
                    id TEXT PRIMARY KEY,
                    deleted_utc TEXT NOT NULL,
                    job_id TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    created_utc TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    index_version INTEGER NOT NULL,
                    checksum TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    payload_gzip BLOB NOT NULL
                );
                """
            )
            defaults = {
                "schema_version": str(SCHEMA_VERSION),
                "index_schema": INDEX_SCHEMA,
                "index_version": "0",
                "last_sync_utc": "",
                "source_site": "",
                "total_records": "0",
                "checksum": hashlib.sha256(b"").hexdigest(),
                "last_job_id": "",
                "last_recovery_utc": "",
                "last_rollback_utc": "",
            }
            for key, value in defaults.items():
                connection.execute("INSERT OR IGNORE INTO meta(key,value) VALUES(?,?)", (key, value))
            connection.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )

    def _migrate_legacy_json(self) -> None:
        legacy = self.path.parent / "knowledge_index.json"
        if not legacy.exists() or self.summary()["total_records"]:
            return
        try:
            payload = json.loads(legacy.read_text(encoding="utf-8"))
            rows = payload.get("records", []) if isinstance(payload, dict) else []
            records = [KnowledgeRecord.model_validate(item) for item in rows]
        except (OSError, ValueError, TypeError):
            return
        if not records:
            return
        self.sync(
            records=records,
            mode="replace",
            source_site=str((payload.get("meta", {}) or {}).get("source_site", "")),
            job_id="legacy-json-migration",
            batch_index=1,
            batch_count=1,
            deleted_ids=[],
            reason="legacy-json-migration",
        )
        try:
            legacy.rename(legacy.with_suffix(".json.migrated"))
        except OSError:
            pass

    @staticmethod
    def _meta(connection: sqlite3.Connection) -> dict[str, str]:
        return {str(row["key"]): str(row["value"]) for row in connection.execute("SELECT key,value FROM meta")}

    @staticmethod
    def _set_meta(connection: sqlite3.Connection, values: dict[str, Any]) -> None:
        for key, value in values.items():
            connection.execute(
                "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(key), str(value)),
            )

    @staticmethod
    def _checksum_rows(connection: sqlite3.Connection) -> str:
        digest = hashlib.sha256()
        for row in connection.execute("SELECT id,content_hash FROM records ORDER BY id ASC"):
            digest.update(str(row["id"]).encode("utf-8"))
            digest.update(b":")
            digest.update(str(row["content_hash"]).encode("ascii", errors="ignore"))
            digest.update(b"\n")
        return digest.hexdigest()

    @staticmethod
    def _record_count(connection: sqlite3.Connection) -> int:
        return int(connection.execute("SELECT COUNT(*) FROM records").fetchone()[0])

    @staticmethod
    def _title_count(connection: sqlite3.Connection) -> int:
        return int(connection.execute("SELECT COUNT(DISTINCT lower(trim(title))) FROM records WHERE trim(title) <> ''").fetchone()[0])

    def _summary_from_connection(self, connection: sqlite3.Connection) -> dict[str, Any]:
        meta = self._meta(connection)
        total_records = self._record_count(connection)
        indexed_titles = self._title_count(connection)
        staging_jobs = int(connection.execute("SELECT COUNT(*) FROM sync_jobs WHERE state='staging'").fetchone()[0])
        snapshots = int(connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])
        return {
            **meta,
            "schema_version": int(meta.get("schema_version", SCHEMA_VERSION)),
            "index_version": int(meta.get("index_version", 0)),
            "total_records": total_records,
            "indexed_titles": indexed_titles,
            "checksum": meta.get("checksum", self._checksum_rows(connection)),
            "storage_engine": "sqlite",
            "database_path": str(self.path),
            "staging_jobs": staging_jobs,
            "snapshot_count": snapshots,
            "recovery_needed": total_records == 0,
        }

    def _snapshot_current(self, connection: sqlite3.Connection, reason: str) -> str:
        rows = [json.loads(str(row["payload"])) for row in connection.execute("SELECT payload FROM records ORDER BY id ASC")]
        if not rows:
            return ""
        meta = self._meta(connection)
        snapshot_id = "runtime-" + uuid.uuid4().hex
        payload = {
            "schema": SNAPSHOT_SCHEMA,
            "created_utc": utc_now(),
            "reason": reason,
            "manifest": {
                "index_version": int(meta.get("index_version", 0)),
                "checksum": meta.get("checksum", ""),
                "record_count": len(rows),
                "source_site": meta.get("source_site", ""),
            },
            "records": rows,
        }
        encoded = gzip.compress(_canonical_json(payload).encode("utf-8"), compresslevel=6)
        connection.execute(
            "INSERT INTO snapshots(snapshot_id,created_utc,reason,index_version,checksum,record_count,payload_gzip) VALUES(?,?,?,?,?,?,?)",
            (
                snapshot_id,
                payload["created_utc"],
                reason,
                payload["manifest"]["index_version"],
                payload["manifest"]["checksum"],
                len(rows),
                encoded,
            ),
        )
        max_snapshots = settings.max_runtime_snapshots
        old_ids = [
            str(row["snapshot_id"])
            for row in connection.execute(
                "SELECT snapshot_id FROM snapshots ORDER BY created_utc DESC LIMIT -1 OFFSET ?", (max_snapshots,)
            )
        ]
        if old_ids:
            connection.executemany("DELETE FROM snapshots WHERE snapshot_id=?", [(snapshot_id,) for snapshot_id in old_ids])
        return snapshot_id

    def sync(
        self,
        records: Iterable[KnowledgeRecord],
        mode: str,
        source_site: str = "",
        job_id: str = "",
        batch_index: int = 1,
        batch_count: int = 1,
        deleted_ids: Iterable[str] | None = None,
        reason: str = "wordpress-sync",
    ) -> SyncResult:
        incoming = list(records)
        deletions = sorted({str(value).strip() for value in (deleted_ids or []) if str(value).strip()})
        job_id = job_id.strip() or "sync-" + uuid.uuid4().hex
        requested_mode = mode if mode in {"replace", "upsert", "delete"} else "upsert"
        now = utc_now()
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute("SELECT * FROM sync_jobs WHERE job_id=?", (job_id,)).fetchone()
                if existing and str(existing["state"]) == "completed":
                    stored = json.loads(str(existing["result"] or "{}"))
                    summary = self._summary_from_connection(connection)
                    connection.commit()
                    return SyncResult(
                        state="completed",
                        committed=True,
                        received=len(incoming),
                        accepted=int(stored.get("accepted", 0)),
                        rejected=int(stored.get("rejected", 0)),
                        inserted=int(stored.get("inserted", 0)),
                        updated=int(stored.get("updated", 0)),
                        unchanged=int(stored.get("unchanged", 0)),
                        deleted=int(stored.get("deleted", 0)),
                        staged_records=0,
                        staged_deletions=0,
                        duplicate_batch=True,
                        summary=summary,
                    )

                if existing:
                    job_mode = str(existing["mode"])
                    received_batches = set(json.loads(str(existing["received_batches"] or "[]")))
                else:
                    job_mode = requested_mode
                    received_batches: set[int] = set()
                    connection.execute(
                        "INSERT INTO sync_jobs(job_id,mode,source_site,state,batch_count,received_batches,started_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?)",
                        (job_id, job_mode, source_site, "staging", batch_count, "[]", now, now),
                    )

                duplicate_batch = batch_index in received_batches
                for record in incoming:
                    payload = record.model_dump()
                    payload["content_hash"] = record_hash(record)
                    connection.execute(
                        "INSERT INTO staging_records(job_id,id,payload,content_hash) VALUES(?,?,?,?) "
                        "ON CONFLICT(job_id,id) DO UPDATE SET payload=excluded.payload,content_hash=excluded.content_hash",
                        (job_id, record.id, _canonical_json(payload), payload["content_hash"]),
                    )
                    connection.execute("DELETE FROM staging_deletions WHERE job_id=? AND id=?", (job_id, record.id))
                for record_id in deletions:
                    connection.execute(
                        "INSERT OR IGNORE INTO staging_deletions(job_id,id) VALUES(?,?)", (job_id, record_id)
                    )
                    connection.execute("DELETE FROM staging_records WHERE job_id=? AND id=?", (job_id, record_id))

                received_batches.add(batch_index)
                staged_records = int(connection.execute("SELECT COUNT(*) FROM staging_records WHERE job_id=?", (job_id,)).fetchone()[0])
                staged_deletions = int(connection.execute("SELECT COUNT(*) FROM staging_deletions WHERE job_id=?", (job_id,)).fetchone()[0])
                effective_batch_count = max(
                    batch_count, int(existing["batch_count"]) if existing else batch_count
                )
                connection.execute(
                    "UPDATE sync_jobs SET source_site=?,batch_count=?,received_batches=?,staged_records=?,staged_deletions=?,updated_utc=? WHERE job_id=?",
                    (
                        source_site,
                        effective_batch_count,
                        _canonical_json(sorted(received_batches)),
                        staged_records,
                        staged_deletions,
                        now,
                        job_id,
                    ),
                )

                final_batch = len(received_batches) >= effective_batch_count
                if not final_batch:
                    summary = self._summary_from_connection(connection)
                    connection.commit()
                    return SyncResult(
                        state="staging",
                        committed=False,
                        received=len(incoming),
                        accepted=len(incoming),
                        rejected=0,
                        inserted=0,
                        updated=0,
                        unchanged=0,
                        deleted=0,
                        staged_records=staged_records,
                        staged_deletions=staged_deletions,
                        duplicate_batch=duplicate_batch,
                        summary=summary,
                    )

                snapshot_id = self._snapshot_current(connection, f"before:{job_id}:{reason}")
                inserted = updated = unchanged = deleted = 0
                if job_mode == "replace":
                    staged_ids = {str(row["id"]) for row in connection.execute("SELECT id FROM staging_records WHERE job_id=?", (job_id,))}
                    existing_ids = {str(row["id"]) for row in connection.execute("SELECT id FROM records")}
                    removed = existing_ids - staged_ids
                    if removed:
                        connection.executemany("DELETE FROM records WHERE id=?", [(value,) for value in removed])
                        connection.executemany(
                            "INSERT INTO tombstones(id,deleted_utc,job_id) VALUES(?,?,?) "
                            "ON CONFLICT(id) DO UPDATE SET deleted_utc=excluded.deleted_utc,job_id=excluded.job_id",
                            [(value, now, job_id) for value in removed],
                        )
                        deleted += len(removed)

                if job_mode != "delete":
                    for row in connection.execute("SELECT id,payload,content_hash FROM staging_records WHERE job_id=?", (job_id,)):
                        current = connection.execute("SELECT content_hash FROM records WHERE id=?", (row["id"],)).fetchone()
                        payload = json.loads(str(row["payload"]))
                        if current is None:
                            inserted += 1
                        elif str(current["content_hash"]) == str(row["content_hash"]):
                            unchanged += 1
                        else:
                            updated += 1
                        connection.execute(
                            "INSERT INTO records(id,title,url,payload,content_hash,updated_utc) VALUES(?,?,?,?,?,?) "
                            "ON CONFLICT(id) DO UPDATE SET title=excluded.title,url=excluded.url,payload=excluded.payload,content_hash=excluded.content_hash,updated_utc=excluded.updated_utc",
                            (
                                row["id"],
                                str(payload.get("title", "")),
                                str(payload.get("url", "")),
                                row["payload"],
                                row["content_hash"],
                                now,
                            ),
                        )
                        connection.execute("DELETE FROM tombstones WHERE id=?", (row["id"],))

                for row in connection.execute("SELECT id FROM staging_deletions WHERE job_id=?", (job_id,)):
                    record_id = str(row["id"])
                    existed = connection.execute("SELECT 1 FROM records WHERE id=?", (record_id,)).fetchone() is not None
                    connection.execute("DELETE FROM records WHERE id=?", (record_id,))
                    connection.execute(
                        "INSERT INTO tombstones(id,deleted_utc,job_id) VALUES(?,?,?) "
                        "ON CONFLICT(id) DO UPDATE SET deleted_utc=excluded.deleted_utc,job_id=excluded.job_id",
                        (record_id, now, job_id),
                    )
                    if existed:
                        deleted += 1

                meta = self._meta(connection)
                version = int(meta.get("index_version", 0)) + 1
                checksum = self._checksum_rows(connection)
                total_records = self._record_count(connection)
                meta_updates = {
                    "schema_version": SCHEMA_VERSION,
                    "index_schema": INDEX_SCHEMA,
                    "index_version": version,
                    "last_sync_utc": now,
                    "source_site": source_site,
                    "total_records": total_records,
                    "checksum": checksum,
                    "last_job_id": job_id,
                }
                if "recovery" in reason:
                    meta_updates["last_recovery_utc"] = now
                self._set_meta(connection, meta_updates)
                result = {
                    "accepted": staged_records,
                    "rejected": 0,
                    "inserted": inserted,
                    "updated": updated,
                    "unchanged": unchanged,
                    "deleted": deleted,
                    "snapshot_id": snapshot_id,
                    "index_version": version,
                    "checksum": checksum,
                }
                connection.execute(
                    "UPDATE sync_jobs SET state='completed',completed_utc=?,updated_utc=?,result=?,error='' WHERE job_id=?",
                    (now, now, _canonical_json(result), job_id),
                )
                connection.execute("DELETE FROM staging_records WHERE job_id=?", (job_id,))
                connection.execute("DELETE FROM staging_deletions WHERE job_id=?", (job_id,))
                summary = self._summary_from_connection(connection)
                connection.commit()
                return SyncResult(
                    state="completed",
                    committed=True,
                    received=len(incoming),
                    accepted=staged_records,
                    rejected=0,
                    inserted=inserted,
                    updated=updated,
                    unchanged=unchanged,
                    deleted=deleted,
                    staged_records=0,
                    staged_deletions=0,
                    duplicate_batch=duplicate_batch,
                    summary={**summary, "snapshot_id": snapshot_id},
                )
            except Exception as exc:
                connection.rollback()
                with self._connection() as failure_connection:
                    failure_connection.execute(
                        "UPDATE sync_jobs SET state='failed',updated_utc=?,error=? WHERE job_id=?",
                        (utc_now(), str(exc)[:1000], job_id),
                    )
                raise

    def records(self) -> list[KnowledgeRecord]:
        with self._lock, self._connection() as connection:
            result: list[KnowledgeRecord] = []
            for row in connection.execute("SELECT payload FROM records ORDER BY lower(title),id"):
                try:
                    result.append(KnowledgeRecord.model_validate(json.loads(str(row["payload"]))))
                except (ValueError, TypeError):
                    continue
            return result

    def summary(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            return self._summary_from_connection(connection)

    def manifest(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            summary = self._summary_from_connection(connection)
            jobs = [dict(row) for row in connection.execute(
                "SELECT job_id,mode,state,batch_count,staged_records,staged_deletions,started_utc,updated_utc,completed_utc,error "
                "FROM sync_jobs ORDER BY started_utc DESC LIMIT 20"
            )]
            tombstones = int(connection.execute("SELECT COUNT(*) FROM tombstones").fetchone()[0])
            return {
                "schema": INDEX_SCHEMA,
                "manifest": summary,
                "recent_jobs": jobs,
                "tombstone_count": tombstones,
            }

    def list_snapshots(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT snapshot_id,created_utc,reason,index_version,checksum,record_count FROM snapshots ORDER BY created_utc DESC"
            )]

    def rollback(self, snapshot_id: str) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT * FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
            if row is None:
                raise KeyError(snapshot_id)
            payload = json.loads(gzip.decompress(bytes(row["payload_gzip"])).decode("utf-8"))
            records = [KnowledgeRecord.model_validate(item) for item in payload.get("records", [])]
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._snapshot_current(connection, f"before-rollback:{snapshot_id}")
                connection.execute("DELETE FROM records")
                now = utc_now()
                for record in records:
                    payload_row = record.model_dump()
                    payload_row["content_hash"] = record_hash(record)
                    connection.execute(
                        "INSERT INTO records(id,title,url,payload,content_hash,updated_utc) VALUES(?,?,?,?,?,?)",
                        (
                            record.id,
                            record.title,
                            record.url,
                            _canonical_json(payload_row),
                            payload_row["content_hash"],
                            now,
                        ),
                    )
                meta = self._meta(connection)
                new_version = int(meta.get("index_version", 0)) + 1
                checksum = self._checksum_rows(connection)
                self._set_meta(
                    connection,
                    {
                        "index_version": new_version,
                        "last_sync_utc": now,
                        "last_rollback_utc": now,
                        "total_records": len(records),
                        "checksum": checksum,
                        "last_job_id": f"rollback:{snapshot_id}",
                    },
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            return {"ok": True, "snapshot_id": snapshot_id, "summary": self.summary()}


store = KnowledgeStore()
