from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterable, Iterator
import uuid

from .calibration import DEFAULT_RETRIEVAL_CONFIG, sanitize_retrieval_config
from .chunking import chunk_record
from .config import settings
from .models import KnowledgeChunk, KnowledgeRecord, utc_now
from .governance import DEFAULT_GOVERNANCE_POLICY, sanitize_governance_policy


SCHEMA_VERSION = 10
INDEX_SCHEMA = "sc-research-librarian-knowledge-index/10.0"
SNAPSHOT_SCHEMA = "sc-research-librarian-runtime-snapshot/4.0"


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
    rejected_records: list[dict[str, Any]]
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
        self.repair_stalled_jobs(settings.stalled_job_seconds, purge_staging=True)

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

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {str(row["name"]) for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _utc_cutoff(seconds: int) -> str:
        return (datetime.now(timezone.utc) - timedelta(seconds=max(0, seconds))).isoformat()

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
                CREATE TABLE IF NOT EXISTS retrieval_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    heading TEXT NOT NULL DEFAULT '',
                    page INTEGER,
                    passage TEXT NOT NULL,
                    position INTEGER NOT NULL DEFAULT 0,
                    content_hash TEXT NOT NULL,
                    embedding_model TEXT NOT NULL DEFAULT '',
                    embedding_json TEXT NOT NULL DEFAULT '',
                    updated_utc TEXT NOT NULL,
                    FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_retrieval_chunks_record ON retrieval_chunks(record_id, position);
                CREATE INDEX IF NOT EXISTS idx_retrieval_chunks_embedding ON retrieval_chunks(embedding_model);
                CREATE TABLE IF NOT EXISTS embedding_runs (
                    run_id TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    state TEXT NOT NULL,
                    requested INTEGER NOT NULL DEFAULT 0,
                    processed INTEGER NOT NULL DEFAULT 0,
                    failed INTEGER NOT NULL DEFAULT 0,
                    started_utc TEXT NOT NULL,
                    completed_utc TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT ''
                );
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
                CREATE TABLE IF NOT EXISTS sync_rejections (
                    rejection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    batch_index INTEGER NOT NULL DEFAULT 1,
                    record_id TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL,
                    payload TEXT NOT NULL DEFAULT '{}',
                    created_utc TEXT NOT NULL,
                    FOREIGN KEY(job_id) REFERENCES sync_jobs(job_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_sync_rejections_job ON sync_rejections(job_id, batch_index);
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
                CREATE TABLE IF NOT EXISTS retrieval_benchmark_runs (
                    run_id TEXT PRIMARY KEY,
                    created_utc TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    case_count INTEGER NOT NULL DEFAULT 0,
                    lexical_mrr REAL NOT NULL DEFAULT 0,
                    hybrid_mrr REAL NOT NULL DEFAULT 0,
                    lexical_hit_at_1 REAL NOT NULL DEFAULT 0,
                    hybrid_hit_at_1 REAL NOT NULL DEFAULT 0,
                    report_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_retrieval_benchmark_created ON retrieval_benchmark_runs(created_utc DESC);
                CREATE TABLE IF NOT EXISTS platform_handoffs (
                    handoff_id TEXT PRIMARY KEY,
                    created_utc TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    status TEXT NOT NULL,
                    session_id TEXT NOT NULL DEFAULT '',
                    schema_name TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_platform_handoffs_created ON platform_handoffs(created_utc DESC);
                CREATE INDEX IF NOT EXISTS idx_platform_handoffs_destination ON platform_handoffs(destination, created_utc DESC);
                CREATE TABLE IF NOT EXISTS platform_artifact_returns (
                    artifact_id TEXT PRIMARY KEY,
                    handoff_id TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(handoff_id) REFERENCES platform_handoffs(handoff_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_platform_artifacts_handoff ON platform_artifact_returns(handoff_id, created_utc DESC);
                CREATE TABLE IF NOT EXISTS platform_handoff_receipts (
                    receipt_id TEXT PRIMARY KEY,
                    handoff_id TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(handoff_id) REFERENCES platform_handoffs(handoff_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_platform_receipts_handoff ON platform_handoff_receipts(handoff_id, created_utc DESC);
                CREATE TABLE IF NOT EXISTS cross_product_events (
                    event_key TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    expires_utc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_cross_product_events_expiry ON cross_product_events(expires_utc);

                CREATE TABLE IF NOT EXISTS governance_policies (
                    policy_id TEXT PRIMARY KEY,
                    created_utc TEXT NOT NULL,
                    reviewer TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    policy_fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_governance_policies_active ON governance_policies(active, created_utc DESC);
                CREATE TABLE IF NOT EXISTS source_governance_reviews (
                    record_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    reviewer TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    reviewed_utc TEXT NOT NULL,
                    expires_utc TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_source_governance_state ON source_governance_reviews(state, reviewed_utc DESC);
                CREATE TABLE IF NOT EXISTS answer_traces (
                    trace_id TEXT PRIMARY KEY,
                    created_utc TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    quality_score REAL NOT NULL DEFAULT 0,
                    review_required INTEGER NOT NULL DEFAULT 0,
                    trace_fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_answer_traces_created ON answer_traces(created_utc DESC);
                CREATE TABLE IF NOT EXISTS quality_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL DEFAULT '',
                    created_utc TEXT NOT NULL,
                    reviewer TEXT NOT NULL DEFAULT '',
                    quality_score REAL NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_quality_evaluations_created ON quality_evaluations(created_utc DESC);
                CREATE TABLE IF NOT EXISTS release_gate_runs (
                    gate_id TEXT PRIMARY KEY,
                    created_utc TEXT NOT NULL,
                    release_version TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    gate_fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_release_gate_created ON release_gate_runs(created_utc DESC);
                CREATE TABLE IF NOT EXISTS governance_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    actor TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_governance_events_created ON governance_events(created_utc DESC);
                CREATE TABLE IF NOT EXISTS research_projects (
                    project_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    owner_ref TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_research_projects_updated ON research_projects(updated_utc DESC);
                CREATE TABLE IF NOT EXISTS research_investigations (
                    investigation_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES research_projects(project_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_research_investigations_project ON research_investigations(project_id, updated_utc DESC);
                CREATE TABLE IF NOT EXISTS research_project_entities (
                    entity_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    created_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES research_projects(project_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_research_entities_project ON research_project_entities(project_id, entity_type, updated_utc DESC);
                CREATE TABLE IF NOT EXISTS research_project_events (
                    event_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    actor TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES research_projects(project_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_research_events_project ON research_project_events(project_id, created_utc DESC);
                CREATE TABLE IF NOT EXISTS connected_platform_backups (
                    backup_id TEXT PRIMARY KEY,
                    created_utc TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    state TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_connected_backups_created ON connected_platform_backups(created_utc DESC);
                """
            )
            self._ensure_column(connection, "sync_jobs", "rejected_records", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "platform_handoffs", "compatibility_state", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "platform_handoffs", "retry_attempt", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "platform_handoffs", "token_expires_utc", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "platform_handoffs", "idempotency_key", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "platform_artifact_returns", "artifact_fingerprint", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "platform_artifact_returns", "idempotency_key", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "research_projects", "owner_ref", "TEXT NOT NULL DEFAULT ''")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_research_projects_owner ON research_projects(owner_ref, updated_utc DESC)")
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
                "retrieval_config": _canonical_json(DEFAULT_RETRIEVAL_CONFIG),
                "governance_policy": _canonical_json(sanitize_governance_policy(DEFAULT_GOVERNANCE_POLICY)),
            }
            for key, value in defaults.items():
                connection.execute("INSERT OR IGNORE INTO meta(key,value) VALUES(?,?)", (key, value))
            connection.execute(
                "INSERT INTO meta(key,value) VALUES('schema_version',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )
            connection.execute(
                "INSERT INTO meta(key,value) VALUES('index_schema',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (INDEX_SCHEMA,),
            )
            record_count = int(connection.execute("SELECT COUNT(*) FROM records").fetchone()[0])
            chunk_count = int(connection.execute("SELECT COUNT(*) FROM retrieval_chunks").fetchone()[0])
            if record_count and not chunk_count:
                self._rebuild_all_chunks(connection)


    def _rebuild_all_chunks(self, connection: sqlite3.Connection) -> int:
        existing_embeddings = {
            str(row["chunk_id"]): (
                str(row["content_hash"]),
                str(row["embedding_model"] or ""),
                str(row["embedding_json"] or ""),
            )
            for row in connection.execute(
                "SELECT chunk_id,content_hash,embedding_model,embedding_json FROM retrieval_chunks"
            )
        }
        connection.execute("DELETE FROM retrieval_chunks")
        now = utc_now()
        count = 0
        for row in connection.execute("SELECT payload FROM records ORDER BY id"):
            try:
                record = KnowledgeRecord.model_validate(json.loads(str(row["payload"])))
            except (ValueError, TypeError):
                continue
            for chunk in chunk_record(record, settings.chunk_max_words, settings.chunk_overlap_words):
                prior = existing_embeddings.get(chunk.chunk_id)
                model = ""
                vector = ""
                if prior and prior[0] == chunk.content_hash:
                    model, vector = prior[1], prior[2]
                connection.execute(
                    "INSERT INTO retrieval_chunks(chunk_id,record_id,heading,page,passage,position,content_hash,embedding_model,embedding_json,updated_utc) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        chunk.chunk_id,
                        chunk.record_id,
                        chunk.heading,
                        chunk.page,
                        chunk.passage,
                        chunk.position,
                        chunk.content_hash,
                        model,
                        vector,
                        now,
                    ),
                )
                count += 1
        self._set_meta(connection, {"indexed_chunks": count})
        return count

    @staticmethod
    def _chunk_from_row(row: sqlite3.Row) -> KnowledgeChunk:
        embedding = None
        raw = str(row["embedding_json"] or "")
        if raw:
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, list):
                    embedding = [float(value) for value in decoded]
            except (ValueError, TypeError):
                embedding = None
        page = row["page"]
        return KnowledgeChunk(
            chunk_id=str(row["chunk_id"]),
            record_id=str(row["record_id"]),
            heading=str(row["heading"] or ""),
            page=int(page) if page is not None else None,
            passage=str(row["passage"] or ""),
            position=int(row["position"] or 0),
            content_hash=str(row["content_hash"] or ""),
            embedding_model=str(row["embedding_model"] or ""),
            embedding=embedding,
        )

    def chunks(self) -> list[KnowledgeChunk]:
        with self._lock, self._connection() as connection:
            return [
                self._chunk_from_row(row)
                for row in connection.execute(
                    "SELECT chunk_id,record_id,heading,page,passage,position,content_hash,embedding_model,embedding_json "
                    "FROM retrieval_chunks ORDER BY record_id,position"
                )
            ]

    def pending_chunks(self, limit: int, model: str) -> list[KnowledgeChunk]:
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT chunk_id,record_id,heading,page,passage,position,content_hash,embedding_model,embedding_json "
                "FROM retrieval_chunks WHERE embedding_json='' OR embedding_model<>? ORDER BY record_id,position LIMIT ?",
                (model, max(1, int(limit))),
            )
            return [self._chunk_from_row(row) for row in rows]

    def save_chunk_embedding(self, chunk_id: str, model: str, embedding: list[float]) -> bool:
        if not embedding:
            return False
        with self._lock, self._connection() as connection:
            cursor = connection.execute(
                "UPDATE retrieval_chunks SET embedding_model=?,embedding_json=?,updated_utc=? WHERE chunk_id=?",
                (model, _canonical_json([float(value) for value in embedding]), utc_now(), chunk_id),
            )
            return cursor.rowcount > 0

    def begin_embedding_run(self, model: str, requested: int) -> str:
        run_id = "embedding-" + uuid.uuid4().hex
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT INTO embedding_runs(run_id,model,state,requested,started_utc) VALUES(?,?,?,?,?)",
                (run_id, model, "running", max(0, int(requested)), utc_now()),
            )
        return run_id

    def finish_embedding_run(self, run_id: str, processed: int, failed: int, error: str = "") -> None:
        with self._lock, self._connection() as connection:
            connection.execute(
                "UPDATE embedding_runs SET state=?,processed=?,failed=?,completed_utc=?,error=? WHERE run_id=?",
                ("completed" if not error else "partial", processed, failed, utc_now(), error[:1000], run_id),
            )

    def embedding_status(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM retrieval_chunks").fetchone()[0])
            embedded = int(connection.execute(
                "SELECT COUNT(*) FROM retrieval_chunks WHERE embedding_json<>'' AND embedding_model=?",
                (settings.gemini_embedding_model,),
            ).fetchone()[0])
            latest = connection.execute(
                "SELECT run_id,model,state,requested,processed,failed,started_utc,completed_utc,error "
                "FROM embedding_runs ORDER BY started_utc DESC LIMIT 1"
            ).fetchone()
            return {
                "indexed_chunks": total,
                "embedded_chunks": embedded,
                "pending_chunks": max(0, total - embedded),
                "semantic_coverage": round((embedded / total) * 100, 2) if total else 0.0,
                "embedding_model": settings.gemini_embedding_model,
                "latest_run": dict(latest) if latest else {},
            }

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
        cutoff = self._utc_cutoff(settings.stalled_job_seconds)
        stalled_jobs = int(connection.execute(
            "SELECT COUNT(*) FROM sync_jobs WHERE state='stalled' OR (state='staging' AND updated_utc < ?)",
            (cutoff,),
        ).fetchone()[0])
        snapshots = int(connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])
        indexed_chunks = int(connection.execute("SELECT COUNT(*) FROM retrieval_chunks").fetchone()[0])
        embedded_chunks = int(connection.execute(
            "SELECT COUNT(*) FROM retrieval_chunks WHERE embedding_json<>'' AND embedding_model=?",
            (settings.gemini_embedding_model,),
        ).fetchone()[0])
        benchmark_runs = int(connection.execute("SELECT COUNT(*) FROM retrieval_benchmark_runs").fetchone()[0])
        handoff_count = int(connection.execute("SELECT COUNT(*) FROM platform_handoffs").fetchone()[0])
        artifact_return_count = int(connection.execute("SELECT COUNT(*) FROM platform_artifact_returns").fetchone()[0])
        answer_trace_count = int(connection.execute("SELECT COUNT(*) FROM answer_traces").fetchone()[0])
        release_gate_count = int(connection.execute("SELECT COUNT(*) FROM release_gate_runs").fetchone()[0])
        source_review_count = int(connection.execute("SELECT COUNT(*) FROM source_governance_reviews").fetchone()[0])
        retrieval_config = self._retrieval_config_from_connection(connection)
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
            "stalled_jobs": stalled_jobs,
            "snapshot_count": snapshots,
            "indexed_chunks": indexed_chunks,
            "embedded_chunks": embedded_chunks,
            "semantic_coverage": round((embedded_chunks / indexed_chunks) * 100, 2) if indexed_chunks else 0.0,
            "embedding_model": settings.gemini_embedding_model,
            "retrieval_profile": retrieval_config.get("profile", "balanced-v6.5.0"),
            "benchmark_runs": benchmark_runs,
            "handoff_count": handoff_count,
            "artifact_return_count": artifact_return_count,
            "answer_trace_count": answer_trace_count,
            "release_gate_count": release_gate_count,
            "source_review_count": source_review_count,
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
        records: Iterable[Any],
        mode: str,
        source_site: str = "",
        job_id: str = "",
        batch_index: int = 1,
        batch_count: int = 1,
        deleted_ids: Iterable[str] | None = None,
        reason: str = "wordpress-sync",
    ) -> SyncResult:
        raw_incoming = list(records)
        valid_records: list[KnowledgeRecord] = []
        rejected_records: list[dict[str, Any]] = []
        for position, raw in enumerate(raw_incoming):
            try:
                valid_records.append(KnowledgeRecord.model_validate(raw))
            except (ValueError, TypeError) as exc:
                record_id = ""
                if isinstance(raw, dict):
                    record_id = str(raw.get("id", "")).strip()[:220]
                rejected_records.append(
                    {
                        "position": position,
                        "id": record_id,
                        "error": str(exc)[:1000],
                    }
                )

        deletions = sorted({str(value).strip() for value in (deleted_ids or []) if str(value).strip()})
        job_id = job_id.strip() or "sync-" + uuid.uuid4().hex
        requested_mode = mode if mode in {"replace", "upsert", "delete"} else "upsert"
        now = utc_now()
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute("SELECT * FROM sync_jobs WHERE job_id=?", (job_id,)).fetchone()
                if existing and str(existing["state"]) in {"completed", "completed-with-rejections"}:
                    stored = json.loads(str(existing["result"] or "{}"))
                    summary = self._summary_from_connection(connection)
                    connection.commit()
                    return SyncResult(
                        state=str(existing["state"]),
                        committed=True,
                        received=len(raw_incoming),
                        accepted=int(stored.get("accepted", 0)),
                        rejected=int(stored.get("rejected", 0)),
                        rejected_records=list(stored.get("rejected_records", [])),
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
                    if str(existing["state"]) in {"failed", "stalled"} and batch_index == 1:
                        connection.execute("DELETE FROM staging_records WHERE job_id=?", (job_id,))
                        connection.execute("DELETE FROM staging_deletions WHERE job_id=?", (job_id,))
                        connection.execute("DELETE FROM sync_rejections WHERE job_id=?", (job_id,))
                        received_batches = set()
                        connection.execute(
                            "UPDATE sync_jobs SET state='staging',received_batches='[]',staged_records=0,staged_deletions=0,rejected_records=0,started_utc=?,updated_utc=?,completed_utc='',result='{}',error='' WHERE job_id=?",
                            (now, now, job_id),
                        )
                else:
                    job_mode = requested_mode
                    received_batches: set[int] = set()
                    connection.execute(
                        "INSERT INTO sync_jobs(job_id,mode,source_site,state,batch_count,received_batches,started_utc,updated_utc,rejected_records) VALUES(?,?,?,?,?,?,?,?,0)",
                        (job_id, job_mode, source_site, "staging", batch_count, "[]", now, now),
                    )

                duplicate_batch = batch_index in received_batches
                if not duplicate_batch:
                    for record in valid_records:
                        payload = record.model_dump()
                        payload["content_hash"] = record_hash(record)
                        connection.execute(
                            "INSERT INTO staging_records(job_id,id,payload,content_hash) VALUES(?,?,?,?) "
                            "ON CONFLICT(job_id,id) DO UPDATE SET payload=excluded.payload,content_hash=excluded.content_hash",
                            (job_id, record.id, _canonical_json(payload), payload["content_hash"]),
                        )
                        connection.execute("DELETE FROM staging_deletions WHERE job_id=? AND id=?", (job_id, record.id))
                    for rejection in rejected_records:
                        raw_payload = raw_incoming[int(rejection["position"])]
                        connection.execute(
                            "INSERT INTO sync_rejections(job_id,batch_index,record_id,error,payload,created_utc) VALUES(?,?,?,?,?,?)",
                            (
                                job_id,
                                batch_index,
                                rejection["id"],
                                rejection["error"],
                                _canonical_json(raw_payload)[:12000],
                                now,
                            ),
                        )
                    for record_id in deletions:
                        connection.execute(
                            "INSERT OR IGNORE INTO staging_deletions(job_id,id) VALUES(?,?)", (job_id, record_id)
                        )
                        connection.execute("DELETE FROM staging_records WHERE job_id=? AND id=?", (job_id, record_id))
                    received_batches.add(batch_index)

                staged_records = int(connection.execute("SELECT COUNT(*) FROM staging_records WHERE job_id=?", (job_id,)).fetchone()[0])
                staged_deletions = int(connection.execute("SELECT COUNT(*) FROM staging_deletions WHERE job_id=?", (job_id,)).fetchone()[0])
                rejected_total = int(connection.execute("SELECT COUNT(*) FROM sync_rejections WHERE job_id=?", (job_id,)).fetchone()[0])
                rejection_rows = [
                    {"position": int(row["batch_index"]), "id": str(row["record_id"]), "error": str(row["error"])}
                    for row in connection.execute(
                        "SELECT batch_index,record_id,error FROM sync_rejections WHERE job_id=? ORDER BY rejection_id LIMIT ?",
                        (job_id, settings.max_rejection_details),
                    )
                ]
                effective_batch_count = max(batch_count, int(existing["batch_count"]) if existing else batch_count)
                connection.execute(
                    "UPDATE sync_jobs SET source_site=?,batch_count=?,received_batches=?,staged_records=?,staged_deletions=?,rejected_records=?,updated_utc=? WHERE job_id=?",
                    (
                        source_site,
                        effective_batch_count,
                        _canonical_json(sorted(received_batches)),
                        staged_records,
                        staged_deletions,
                        rejected_total,
                        now,
                        job_id,
                    ),
                )

                final_batch = len(received_batches) >= effective_batch_count
                if not final_batch:
                    summary = self._summary_from_connection(connection)
                    connection.commit()
                    return SyncResult(
                        state="staging-with-rejections" if rejected_total else "staging",
                        committed=False,
                        received=len(raw_incoming),
                        accepted=len(valid_records),
                        rejected=len(rejected_records),
                        rejected_records=rejected_records[: settings.max_rejection_details],
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
                    protected_ids = {
                        str(row["record_id"])
                        for row in connection.execute(
                            "SELECT DISTINCT record_id FROM sync_rejections WHERE job_id=? AND trim(record_id) <> ''",
                            (job_id,),
                        )
                    }
                    existing_ids = {str(row["id"]) for row in connection.execute("SELECT id FROM records")}
                    removed = existing_ids - staged_ids - protected_ids
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
                            (row["id"], str(payload.get("title", "")), str(payload.get("url", "")), row["payload"], row["content_hash"], now),
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

                indexed_chunks = self._rebuild_all_chunks(connection)
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
                final_state = "completed-with-rejections" if rejected_total else "completed"
                result = {
                    "accepted": staged_records,
                    "rejected": rejected_total,
                    "rejected_records": rejection_rows,
                    "inserted": inserted,
                    "updated": updated,
                    "unchanged": unchanged,
                    "deleted": deleted,
                    "snapshot_id": snapshot_id,
                    "index_version": version,
                    "checksum": checksum,
                    "indexed_chunks": indexed_chunks,
                }
                connection.execute(
                    "UPDATE sync_jobs SET state=?,completed_utc=?,updated_utc=?,result=?,error='' WHERE job_id=?",
                    (final_state, now, now, _canonical_json(result), job_id),
                )
                connection.execute("DELETE FROM staging_records WHERE job_id=?", (job_id,))
                connection.execute("DELETE FROM staging_deletions WHERE job_id=?", (job_id,))
                summary = self._summary_from_connection(connection)
                connection.commit()
                return SyncResult(
                    state=final_state,
                    committed=True,
                    received=len(raw_incoming),
                    accepted=staged_records,
                    rejected=rejected_total,
                    rejected_records=rejection_rows,
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

    def repair_stalled_jobs(self, max_age_seconds: int | None = None, purge_staging: bool = True) -> dict[str, Any]:
        age = max(300, int(max_age_seconds or settings.stalled_job_seconds))
        cutoff = self._utc_cutoff(age)
        repaired: list[str] = []
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = list(connection.execute(
                    "SELECT job_id FROM sync_jobs WHERE state='staging' AND updated_utc < ? ORDER BY updated_utc",
                    (cutoff,),
                ))
                now = utc_now()
                for row in rows:
                    job_id = str(row["job_id"])
                    repaired.append(job_id)
                    if purge_staging:
                        connection.execute("DELETE FROM staging_records WHERE job_id=?", (job_id,))
                        connection.execute("DELETE FROM staging_deletions WHERE job_id=?", (job_id,))
                    connection.execute(
                        "UPDATE sync_jobs SET state='stalled',updated_utc=?,error=? WHERE job_id=?",
                        (now, f"Staging job exceeded {age} seconds without all expected batches.", job_id),
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {"ok": True, "repaired_jobs": repaired, "count": len(repaired), "purged": purge_staging, "max_age_seconds": age}

    @staticmethod
    def _retrieval_config_from_connection(connection: sqlite3.Connection) -> dict[str, Any]:
        row = connection.execute("SELECT value FROM meta WHERE key='retrieval_config'").fetchone()
        try:
            raw = json.loads(str(row["value"])) if row is not None else {}
        except (ValueError, TypeError, json.JSONDecodeError):
            raw = {}
        return sanitize_retrieval_config(raw)

    def retrieval_config(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            return self._retrieval_config_from_connection(connection)

    def set_retrieval_config(self, value: dict[str, Any]) -> dict[str, Any]:
        config = sanitize_retrieval_config(value)
        with self._lock, self._connection() as connection:
            self._set_meta(connection, {"retrieval_config": _canonical_json(config)})
        return config

    def save_benchmark_run(self, report: dict[str, Any]) -> str:
        run_id = str(report.get("run_id") or ("benchmark-" + uuid.uuid4().hex))
        metrics = report.get("metrics", {}) if isinstance(report.get("metrics"), dict) else {}
        lexical = metrics.get("lexical", {}) if isinstance(metrics.get("lexical"), dict) else {}
        hybrid = metrics.get("hybrid", {}) if isinstance(metrics.get("hybrid"), dict) else {}
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO retrieval_benchmark_runs(run_id,created_utc,profile,case_count,lexical_mrr,hybrid_mrr,lexical_hit_at_1,hybrid_hit_at_1,report_json) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    str(report.get("created_utc") or utc_now()),
                    str(report.get("profile") or "balanced-v6.5.0"),
                    int(report.get("case_count") or 0),
                    float(lexical.get("mrr") or 0.0),
                    float(hybrid.get("mrr") or 0.0),
                    float(lexical.get("hit_at_1") or 0.0),
                    float(hybrid.get("hit_at_1") or 0.0),
                    _canonical_json(report),
                ),
            )
            connection.execute(
                "DELETE FROM retrieval_benchmark_runs WHERE run_id NOT IN (SELECT run_id FROM retrieval_benchmark_runs ORDER BY created_utc DESC LIMIT 25)"
            )
        return run_id

    def benchmark_history(self, limit: int = 10) -> list[dict[str, Any]]:
        bounded = max(1, min(25, int(limit)))
        with self._lock, self._connection() as connection:
            rows = connection.execute(
                "SELECT report_json FROM retrieval_benchmark_runs ORDER BY created_utc DESC LIMIT ?", (bounded,)
            )
            output: list[dict[str, Any]] = []
            for row in rows:
                try:
                    output.append(json.loads(str(row["report_json"])))
                except (ValueError, TypeError, json.JSONDecodeError):
                    continue
            return output

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
            cutoff = self._utc_cutoff(settings.stalled_job_seconds)
            jobs: list[dict[str, Any]] = []
            for row in connection.execute(
                "SELECT job_id,mode,state,batch_count,staged_records,staged_deletions,rejected_records,started_utc,updated_utc,completed_utc,error "
                "FROM sync_jobs ORDER BY started_utc DESC LIMIT 20"
            ):
                item = dict(row)
                item["stalled"] = item["state"] == "stalled" or (item["state"] == "staging" and str(item["updated_utc"]) < cutoff)
                jobs.append(item)
            tombstones = int(connection.execute("SELECT COUNT(*) FROM tombstones").fetchone()[0])
            return {
                "schema": INDEX_SCHEMA,
                "manifest": summary,
                "recent_jobs": jobs,
                "tombstone_count": tombstones,
                "stalled_job_seconds": settings.stalled_job_seconds,
            }

    def job_rejections(self, job_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT batch_index,record_id,error,created_utc FROM sync_rejections WHERE job_id=? ORDER BY rejection_id LIMIT ?",
                (job_id, settings.max_rejection_details),
            )]

    @staticmethod
    def _validate_snapshot_row(row: sqlite3.Row) -> dict[str, Any]:
        errors: list[str] = []
        try:
            payload = json.loads(gzip.decompress(bytes(row["payload_gzip"])).decode("utf-8"))
        except (OSError, ValueError, TypeError, gzip.BadGzipFile) as exc:
            return {"ok": False, "errors": [f"snapshot-decode: {exc}"]}
        raw_records = payload.get("records", []) if isinstance(payload, dict) else []
        if not isinstance(raw_records, list):
            return {"ok": False, "errors": ["records is not a list"]}
        digest = hashlib.sha256()
        valid_count = 0
        for position, raw in enumerate(raw_records):
            try:
                record = KnowledgeRecord.model_validate(raw)
            except (ValueError, TypeError) as exc:
                errors.append(f"record {position}: {str(exc)[:300]}")
                continue
            digest.update(record.id.encode("utf-8"))
            digest.update(b":")
            digest.update(record_hash(record).encode("ascii", errors="ignore"))
            digest.update(b"\n")
            valid_count += 1
        calculated = digest.hexdigest()
        manifest = payload.get("manifest", {}) if isinstance(payload, dict) else {}
        expected_checksum = str(manifest.get("checksum", row["checksum"] or ""))
        expected_count = int(manifest.get("record_count", row["record_count"] or 0))
        if expected_count != len(raw_records):
            errors.append(f"record-count mismatch: expected {expected_count}, found {len(raw_records)}")
        if expected_checksum and calculated != expected_checksum:
            errors.append("record checksum mismatch")
        if valid_count != len(raw_records):
            errors.append(f"{len(raw_records) - valid_count} invalid record(s)")
        return {
            "ok": not errors,
            "errors": errors[:20],
            "record_count": len(raw_records),
            "checksum": calculated,
            "payload": payload,
        }

    def list_snapshots(self) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            result: list[dict[str, Any]] = []
            for row in connection.execute(
                "SELECT snapshot_id,created_utc,reason,index_version,checksum,record_count,payload_gzip FROM snapshots ORDER BY created_utc DESC"
            ):
                item = {key: row[key] for key in ("snapshot_id", "created_utc", "reason", "index_version", "checksum", "record_count")}
                integrity = self._validate_snapshot_row(row)
                item["integrity_ok"] = bool(integrity["ok"])
                item["integrity_errors"] = integrity["errors"]
                result.append(item)
            return result

    def validate_snapshots(self) -> dict[str, Any]:
        snapshots = self.list_snapshots()
        invalid = [item for item in snapshots if not item.get("integrity_ok")]
        return {"ok": not invalid, "snapshot_count": len(snapshots), "invalid_count": len(invalid), "snapshots": snapshots}

    def rollback(self, snapshot_id: str) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT * FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
            if row is None:
                raise KeyError(snapshot_id)
            integrity = self._validate_snapshot_row(row)
            if not integrity["ok"]:
                raise ValueError("Runtime snapshot failed integrity validation: " + "; ".join(integrity["errors"]))
            payload = integrity["payload"]
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
                        (record.id, record.title, record.url, _canonical_json(payload_row), payload_row["content_hash"], now),
                    )
                self._rebuild_all_chunks(connection)
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
            return {"ok": True, "snapshot_id": snapshot_id, "integrity": {"ok": True, "checksum": integrity["checksum"]}, "summary": self.summary()}


    def save_platform_handoff(self, payload: dict[str, Any]) -> dict[str, Any]:
        handoff_id = str(payload.get("handoff_id", "")).strip()
        if not handoff_id:
            raise ValueError("handoff_id is required")
        encoded = _canonical_json(payload)
        fingerprint_value = str((payload.get("provenance") or {}).get("payload_fingerprint") or hashlib.sha256(encoded.encode("utf-8")).hexdigest())
        route = payload.get("route") if isinstance(payload.get("route"), dict) else {}
        compatibility = route.get("compatibility") if isinstance(route.get("compatibility"), dict) else {}
        delivery = payload.get("delivery") if isinstance(payload.get("delivery"), dict) else {}
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT INTO platform_handoffs(handoff_id,created_utc,destination,status,session_id,schema_name,fingerprint,payload_json,compatibility_state,retry_attempt,token_expires_utc,idempotency_key) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(handoff_id) DO UPDATE SET status=excluded.status,payload_json=excluded.payload_json,fingerprint=excluded.fingerprint,compatibility_state=excluded.compatibility_state,retry_attempt=excluded.retry_attempt,token_expires_utc=excluded.token_expires_utc,idempotency_key=excluded.idempotency_key",
                (handoff_id, str(payload.get("created_utc") or utc_now()), str(payload.get("destination") or ""), str(payload.get("status") or "prepared"), str(payload.get("session_id") or ""), str(payload.get("schema") or ""), fingerprint_value, encoded, str(compatibility.get("state") or ""), int(delivery.get("attempt") or 0), str(delivery.get("token_expires_utc") or ""), str(payload.get("idempotency_key") or "")),
            )
        return payload

    def platform_handoff(self, handoff_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT payload_json FROM platform_handoffs WHERE handoff_id=?", (handoff_id,)).fetchone()
            return json.loads(str(row["payload_json"])) if row else None

    def platform_handoff_by_idempotency(self, idempotency_key: str) -> dict[str, Any] | None:
        if not idempotency_key:
            return None
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT payload_json FROM platform_handoffs WHERE idempotency_key=? ORDER BY created_utc DESC LIMIT 1", (idempotency_key,)).fetchone()
            return json.loads(str(row["payload_json"])) if row else None

    def platform_handoffs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT payload_json FROM platform_handoffs ORDER BY created_utc DESC LIMIT ?", (max(1, min(500, int(limit))),))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def cleanup_cross_product_events(self) -> int:
        now = utc_now()
        with self._lock, self._connection() as connection:
            cursor = connection.execute("DELETE FROM cross_product_events WHERE expires_utc<=?", (now,))
            return int(cursor.rowcount or 0)

    def cross_product_event(self, event_key: str) -> dict[str, Any] | None:
        if not event_key:
            return None
        self.cleanup_cross_product_events()
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT * FROM cross_product_events WHERE event_key=?", (event_key,)).fetchone()
            if not row:
                return None
            return {"event_key": str(row["event_key"]), "event_type": str(row["event_type"]), "payload_hash": str(row["payload_hash"]), "response": json.loads(str(row["response_json"])), "created_utc": str(row["created_utc"]), "expires_utc": str(row["expires_utc"])}

    def save_cross_product_event(self, event_key: str, event_type: str, payload_hash: str, response: dict[str, Any], ttl_seconds: int) -> dict[str, Any]:
        if not event_key:
            return response
        created = datetime.now(timezone.utc)
        expires = (created + timedelta(seconds=max(300, int(ttl_seconds)))).isoformat()
        with self._lock, self._connection() as connection:
            existing = connection.execute("SELECT payload_hash FROM cross_product_events WHERE event_key=?", (event_key,)).fetchone()
            if existing and str(existing["payload_hash"]) != payload_hash:
                raise ValueError("Idempotency key was already used with a different payload.")
            connection.execute("INSERT INTO cross_product_events(event_key,event_type,payload_hash,response_json,created_utc,expires_utc) VALUES(?,?,?,?,?,?) ON CONFLICT(event_key) DO UPDATE SET response_json=excluded.response_json,expires_utc=excluded.expires_utc", (event_key, event_type, payload_hash, _canonical_json(response), created.isoformat(), expires))
        return response

    def save_handoff_receipt(self, payload: dict[str, Any]) -> dict[str, Any]:
        receipt_id = str(payload.get("receipt_id") or "").strip()
        if not receipt_id:
            raise ValueError("receipt_id is required")
        encoded = _canonical_json(payload)
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT payload_json FROM platform_handoff_receipts WHERE receipt_id=?", (receipt_id,)).fetchone()
            if row:
                existing = json.loads(str(row["payload_json"]))
                if _canonical_json(existing) != encoded:
                    raise ValueError("Receipt ID is immutable and already exists with different contents.")
                existing["duplicate_event"] = True
                return existing
            connection.execute("INSERT INTO platform_handoff_receipts(receipt_id,handoff_id,destination,status,created_utc,payload_json) VALUES(?,?,?,?,?,?)", (receipt_id, str(payload.get("handoff_id") or ""), str(payload.get("destination") or ""), str(payload.get("status") or ""), str(payload.get("created_utc") or utc_now()), encoded))
            connection.execute("UPDATE platform_handoffs SET status=? WHERE handoff_id=?", ("receipt-" + str(payload.get("status") or "received"), str(payload.get("handoff_id") or "")))
        return payload

    def handoff_receipts(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT payload_json FROM platform_handoff_receipts ORDER BY created_utc DESC LIMIT ?", (max(1, min(500, int(limit))),))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def artifact_return(self, artifact_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT payload_json,status FROM platform_artifact_returns WHERE artifact_id=?", (artifact_id,)).fetchone()
            if not row:
                return None
            payload = json.loads(str(row["payload_json"]))
            payload["storage_status"] = str(row["status"])
            return payload

    def save_artifact_return(self, payload: dict[str, Any], status: str = "accepted") -> dict[str, Any]:
        artifact_id = str(payload.get("artifact_id", "")).strip()
        handoff_id = str(payload.get("handoff_id", "")).strip()
        if not artifact_id or not handoff_id:
            raise ValueError("artifact_id and handoff_id are required")
        encoded = _canonical_json(payload)
        artifact_fingerprint = str((payload.get("provenance") or {}).get("artifact_fingerprint") or hashlib.sha256(encoded.encode("utf-8")).hexdigest())
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT payload_json,artifact_fingerprint FROM platform_artifact_returns WHERE artifact_id=?", (artifact_id,)).fetchone()
            if row:
                existing = json.loads(str(row["payload_json"]))
                existing_fp = str(row["artifact_fingerprint"] or (existing.get("provenance") or {}).get("artifact_fingerprint") or "")
                if existing_fp != artifact_fingerprint:
                    raise ValueError("Artifact ID is immutable and already exists with different contents.")
                existing["duplicate_event"] = True
                return existing
            connection.execute("INSERT INTO platform_artifact_returns(artifact_id,handoff_id,destination,artifact_type,created_utc,status,payload_json,artifact_fingerprint,idempotency_key) VALUES(?,?,?,?,?,?,?,?,?)", (artifact_id, handoff_id, str(payload.get("destination") or ""), str(payload.get("artifact_type") or ""), str(payload.get("created_utc") or utc_now()), status, encoded, artifact_fingerprint, str(payload.get("idempotency_key") or "")))
            connection.execute("UPDATE platform_handoffs SET status='artifact-returned' WHERE handoff_id=?", (handoff_id,))
        return payload

    def artifact_returns(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT payload_json,status FROM platform_artifact_returns ORDER BY created_utc DESC LIMIT ?", (max(1, min(500, int(limit))),))
            result: list[dict[str, Any]] = []
            for row in rows:
                payload = json.loads(str(row["payload_json"]))
                payload["storage_status"] = str(row["status"])
                result.append(payload)
            return result

    def platform_handoff_summary(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            handoffs = int(connection.execute("SELECT COUNT(*) FROM platform_handoffs").fetchone()[0])
            artifacts = int(connection.execute("SELECT COUNT(*) FROM platform_artifact_returns").fetchone()[0])
            receipts = int(connection.execute("SELECT COUNT(*) FROM platform_handoff_receipts").fetchone()[0])
            events = int(connection.execute("SELECT COUNT(*) FROM cross_product_events WHERE expires_utc>?", (utc_now(),)).fetchone()[0])
            destination_rows = connection.execute("SELECT destination,COUNT(*) AS total FROM platform_handoffs GROUP BY destination ORDER BY total DESC")
            compatibility_rows = connection.execute("SELECT compatibility_state,COUNT(*) AS total FROM platform_handoffs GROUP BY compatibility_state ORDER BY total DESC")
            latest = connection.execute("SELECT handoff_id,destination,status,created_utc,retry_attempt,token_expires_utc FROM platform_handoffs ORDER BY created_utc DESC LIMIT 1").fetchone()
            return {"handoff_count": handoffs, "artifact_return_count": artifacts, "receipt_count": receipts, "active_idempotency_events": events, "destination_counts": {str(row["destination"]): int(row["total"]) for row in destination_rows}, "compatibility_counts": {str(row["compatibility_state"] or "unknown"): int(row["total"]) for row in compatibility_rows}, "latest_handoff": dict(latest) if latest else {}}


    def governance_policy(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT payload_json FROM governance_policies WHERE active=1 ORDER BY created_utc DESC LIMIT 1").fetchone()
            if row:
                try:
                    return sanitize_governance_policy(json.loads(str(row["payload_json"])))
                except (ValueError, TypeError):
                    pass
            meta = self._meta(connection)
            try:
                return sanitize_governance_policy(json.loads(meta.get("governance_policy", "{}")))
            except (ValueError, TypeError):
                return sanitize_governance_policy(DEFAULT_GOVERNANCE_POLICY)

    def save_governance_policy(self, policy: dict[str, Any], reviewer: str = "", reason: str = "policy-update") -> dict[str, Any]:
        clean = sanitize_governance_policy(policy)
        policy_id = "policy-" + uuid.uuid4().hex
        created = utc_now()
        with self._lock, self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("UPDATE governance_policies SET active=0 WHERE active=1")
            connection.execute(
                "INSERT INTO governance_policies(policy_id,created_utc,reviewer,reason,policy_fingerprint,payload_json,active) VALUES(?,?,?,?,?,?,1)",
                (policy_id, created, str(reviewer)[:160], str(reason)[:300], clean["policy_fingerprint"], _canonical_json(clean)),
            )
            self._set_meta(connection, {"governance_policy": _canonical_json(clean)})
            connection.execute("COMMIT")
        self.save_governance_event("policy-updated", {"policy_id": policy_id, "policy_fingerprint": clean["policy_fingerprint"], "reason": reason}, reviewer)
        return {**clean, "policy_id": policy_id, "created_utc": created, "reviewer": str(reviewer)[:160], "reason": str(reason)[:300]}

    def save_source_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        clean = {
            "schema": "sc-research-source-review/1.0",
            "record_id": str(payload.get("record_id") or "")[:220],
            "state": str(payload.get("state") or "review")[:40],
            "reviewer": str(payload.get("reviewer") or "")[:160],
            "note": str(payload.get("note") or "")[:2000],
            "reviewed_utc": utc_now(),
            "expires_utc": str(payload.get("expires_utc") or "")[:80],
        }
        if clean["state"] not in {"approved", "review", "excluded"}:
            raise ValueError("Unsupported source-governance state.")
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT INTO source_governance_reviews(record_id,state,reviewer,note,reviewed_utc,expires_utc,payload_json) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(record_id) DO UPDATE SET state=excluded.state,reviewer=excluded.reviewer,note=excluded.note,reviewed_utc=excluded.reviewed_utc,expires_utc=excluded.expires_utc,payload_json=excluded.payload_json",
                (clean["record_id"], clean["state"], clean["reviewer"], clean["note"], clean["reviewed_utc"], clean["expires_utc"], _canonical_json(clean)),
            )
        self.save_governance_event("source-review", clean, clean["reviewer"])
        return clean

    def source_reviews(self, limit: int = 1000) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT payload_json FROM source_governance_reviews ORDER BY reviewed_utc DESC LIMIT ?", (max(1, min(5000, int(limit))),))
            output = []
            for row in rows:
                try:
                    output.append(json.loads(str(row["payload_json"])))
                except (ValueError, TypeError):
                    continue
            return output

    def source_review_map(self) -> dict[str, dict[str, Any]]:
        return {str(item.get("record_id") or ""): item for item in self.source_reviews(5000) if item.get("record_id")}

    def save_answer_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO answer_traces(trace_id,created_utc,query_hash,quality_score,review_required,trace_fingerprint,payload_json) VALUES(?,?,?,?,?,?,?)",
                (str(trace.get("trace_id") or ""), str(trace.get("created_utc") or utc_now()), str(trace.get("query_hash") or ""), float((trace.get("quality") or {}).get("quality_score") or 0), 1 if (trace.get("quality") or {}).get("review_required") else 0, str(trace.get("trace_fingerprint") or ""), _canonical_json(trace)),
            )
        return trace

    def answer_trace(self, trace_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as connection:
            row = connection.execute("SELECT payload_json FROM answer_traces WHERE trace_id=?", (trace_id,)).fetchone()
            return json.loads(str(row["payload_json"])) if row else None

    def answer_traces(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT payload_json FROM answer_traces ORDER BY created_utc DESC LIMIT ?", (max(1, min(500, int(limit))),))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def save_quality_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        evaluation_id = str(payload.get("evaluation_id") or "evaluation-" + uuid.uuid4().hex)
        clean = {**payload, "evaluation_id": evaluation_id, "created_utc": str(payload.get("created_utc") or utc_now())}
        with self._lock, self._connection() as connection:
            connection.execute("INSERT OR REPLACE INTO quality_evaluations(evaluation_id,trace_id,created_utc,reviewer,quality_score,payload_json) VALUES(?,?,?,?,?,?)", (evaluation_id, str(clean.get("trace_id") or ""), clean["created_utc"], str(clean.get("reviewer") or "")[:160], float(clean.get("quality_score") or 0), _canonical_json(clean)))
        return clean

    def quality_evaluations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT payload_json FROM quality_evaluations ORDER BY created_utc DESC LIMIT ?", (max(1, min(500, int(limit))),))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def save_release_gate(self, report: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            connection.execute("INSERT OR REPLACE INTO release_gate_runs(gate_id,created_utc,release_version,decision,gate_fingerprint,payload_json) VALUES(?,?,?,?,?,?)", (str(report.get("gate_id") or ""), str(report.get("created_utc") or utc_now()), str(report.get("release_version") or ""), str(report.get("decision") or "review"), str(report.get("gate_fingerprint") or ""), _canonical_json(report)))
        return report

    def release_gate_history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT payload_json FROM release_gate_runs ORDER BY created_utc DESC LIMIT ?", (max(1, min(200, int(limit))),))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def save_governance_event(self, event_type: str, payload: dict[str, Any], actor: str = "") -> dict[str, Any]:
        event = {"event_id": "governance-" + uuid.uuid4().hex, "event_type": str(event_type)[:100], "created_utc": utc_now(), "actor": str(actor)[:160], "payload": payload}
        with self._lock, self._connection() as connection:
            connection.execute("INSERT INTO governance_events(event_id,event_type,created_utc,actor,payload_json) VALUES(?,?,?,?,?)", (event["event_id"], event["event_type"], event["created_utc"], event["actor"], _canonical_json(event)))
        return event

    def governance_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows = connection.execute("SELECT payload_json FROM governance_events ORDER BY created_utc DESC LIMIT ?", (max(1, min(500, int(limit))),))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def governance_metrics(self, trace_limit: int = 500) -> dict[str, Any]:
        traces = self.answer_traces(trace_limit)
        evaluations = self.quality_evaluations(200)
        benchmarks = self.benchmark_history(1)
        count = len(traces)
        if count:
            citation_precision = sum(1 for item in traces if (item.get("quality") or {}).get("citation_verified")) / count
            citation_completeness = sum(float((item.get("quality") or {}).get("citation_coverage") or 0) for item in traces) / count
            unsupported_claims = sum(int((item.get("quality") or {}).get("unsupported_claims") or 0) for item in traces)
            unsupported_rate = unsupported_claims / count
            fallback_success = sum(1 for item in traces if (item.get("quality") or {}).get("generation_mode") in {"citation-verified-ai", "deterministic-evidence-fallback"}) / count
            mean_quality = sum(float((item.get("quality") or {}).get("quality_score") or 0) for item in traces) / count
        else:
            citation_precision = citation_completeness = fallback_success = mean_quality = 0.0
            unsupported_rate = 1.0
        latest_benchmark = benchmarks[0] if benchmarks else {}
        metrics_from_reviews: dict[str, list[float]] = {"route_accuracy": [], "pdf_page_accuracy": []}
        for item in evaluations:
            raw = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
            for key in metrics_from_reviews:
                if key in raw:
                    try:
                        metrics_from_reviews[key].append(float(raw[key]))
                    except (TypeError, ValueError):
                        pass
        exact_title = float((latest_benchmark.get("metrics") or {}).get("hybrid", {}).get("hit_at_1") or latest_benchmark.get("hybrid_hit_at_1") or 0)
        hit_at_3 = float((latest_benchmark.get("metrics") or {}).get("hybrid", {}).get("hit_at_3") or 0)
        return {
            "schema": "sc-research-quality-metrics/1.0",
            "generated_utc": utc_now(),
            "sample_sizes": {"answer_traces": count, "quality_evaluations": len(evaluations), "benchmark_runs": len(benchmarks)},
            "metrics": {
                "exact_title_accuracy": round(exact_title, 4),
                "hit_at_3": round(hit_at_3, 4),
                "citation_precision": round(citation_precision, 4),
                "citation_completeness": round(citation_completeness, 4),
                "unsupported_claim_rate": round(unsupported_rate, 4),
                "route_accuracy": round(sum(metrics_from_reviews["route_accuracy"]) / len(metrics_from_reviews["route_accuracy"]), 4) if metrics_from_reviews["route_accuracy"] else 0.0,
                "pdf_page_accuracy": round(sum(metrics_from_reviews["pdf_page_accuracy"]) / len(metrics_from_reviews["pdf_page_accuracy"]), 4) if metrics_from_reviews["pdf_page_accuracy"] else 0.0,
                "fallback_success": round(fallback_success, 4),
                "mean_answer_quality": round(mean_quality, 4),
            },
            "unmeasured": [key for key, values in metrics_from_reviews.items() if not values] + ([] if benchmarks else ["exact_title_accuracy", "hit_at_3"]),
        }

    def governance_retention(self, dry_run: bool = True) -> dict[str, Any]:
        policy = self.governance_policy()
        now = datetime.now(timezone.utc)
        cutoffs = {
            "answer_traces": (now - timedelta(days=int(policy["retention"]["answer_trace_days"]))).isoformat(),
            "quality_evaluations": (now - timedelta(days=int(policy["retention"]["quality_evaluation_days"]))).isoformat(),
            "governance_events": (now - timedelta(days=int(policy["retention"]["governance_event_days"]))).isoformat(),
        }
        with self._lock, self._connection() as connection:
            candidates = {
                "answer_traces": int(connection.execute("SELECT COUNT(*) FROM answer_traces WHERE created_utc < ?", (cutoffs["answer_traces"],)).fetchone()[0]),
                "quality_evaluations": int(connection.execute("SELECT COUNT(*) FROM quality_evaluations WHERE created_utc < ?", (cutoffs["quality_evaluations"],)).fetchone()[0]),
                "governance_events": int(connection.execute("SELECT COUNT(*) FROM governance_events WHERE created_utc < ?", (cutoffs["governance_events"],)).fetchone()[0]),
            }
            if not dry_run:
                connection.execute("DELETE FROM answer_traces WHERE created_utc < ?", (cutoffs["answer_traces"],))
                connection.execute("DELETE FROM quality_evaluations WHERE created_utc < ?", (cutoffs["quality_evaluations"],))
                connection.execute("DELETE FROM governance_events WHERE created_utc < ?", (cutoffs["governance_events"],))
        return {"ok": True, "dry_run": bool(dry_run), "cutoffs": cutoffs, "candidates": candidates, "deleted": {key: (0 if dry_run else value) for key, value in candidates.items()}}


    def save_research_project(self, project: dict[str, Any]) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO research_projects(project_id,title,owner_ref,status,created_utc,updated_utc,fingerprint,payload_json) VALUES(?,?,?,?,?,?,?,?)",
                (str(project.get("project_id") or ""), str(project.get("title") or ""), str(project.get("owner_ref") or ""), str(project.get("status") or "active"), str(project.get("created_utc") or utc_now()), str(project.get("updated_utc") or utc_now()), str(project.get("fingerprint") or ""), _canonical_json(project)),
            )
        return project

    def research_project(self, project_id: str) -> dict[str, Any] | None:
        with self._lock, self._connection() as connection:
            row=connection.execute("SELECT payload_json FROM research_projects WHERE project_id=?",(project_id,)).fetchone()
            return json.loads(str(row["payload_json"])) if row else None

    def research_projects(self, limit: int = 100, owner_ref: str = "") -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            if owner_ref:
                rows=connection.execute("SELECT payload_json FROM research_projects WHERE owner_ref=? ORDER BY updated_utc DESC LIMIT ?",(owner_ref,max(1,min(500,int(limit)))))
            else:
                rows=connection.execute("SELECT payload_json FROM research_projects ORDER BY updated_utc DESC LIMIT ?",(max(1,min(500,int(limit))),))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def save_research_investigation(self, investigation: dict[str, Any]) -> dict[str, Any]:
        if not self.research_project(str(investigation.get("project_id") or "")):
            raise ValueError("Unknown research project.")
        with self._lock, self._connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO research_investigations(investigation_id,project_id,status,created_utc,updated_utc,fingerprint,payload_json) VALUES(?,?,?,?,?,?,?)",
                (str(investigation.get("investigation_id") or ""),str(investigation.get("project_id") or ""),str(investigation.get("status") or "open"),str(investigation.get("created_utc") or utc_now()),str(investigation.get("updated_utc") or utc_now()),str(investigation.get("fingerprint") or ""),_canonical_json(investigation)),
            )
        return investigation

    def research_investigations(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows=connection.execute("SELECT payload_json FROM research_investigations WHERE project_id=? ORDER BY updated_utc DESC LIMIT ?",(project_id,max(1,min(500,int(limit)))))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def save_project_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        project_id=str(entity.get("project_id") or "")
        if not self.research_project(project_id): raise ValueError("Unknown research project.")
        entity_id=str(entity.get("entity_id") or "entity-"+uuid.uuid4().hex)
        now=utc_now(); clean={**entity,"entity_id":entity_id,"created_utc":str(entity.get("created_utc") or now),"updated_utc":now}
        clean["fingerprint"]=hashlib.sha256(_canonical_json({k:v for k,v in clean.items() if k!="fingerprint"}).encode()).hexdigest()
        with self._lock, self._connection() as connection:
            connection.execute("INSERT OR REPLACE INTO research_project_entities(entity_id,project_id,entity_type,title,created_utc,updated_utc,fingerprint,payload_json) VALUES(?,?,?,?,?,?,?,?)",(entity_id,project_id,str(clean.get("entity_type") or "record"),str(clean.get("title") or ""),clean["created_utc"],clean["updated_utc"],clean["fingerprint"],_canonical_json(clean)))
        return clean

    def project_entities(self, project_id: str, entity_type: str = "", limit: int = 500) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            if entity_type:
                rows=connection.execute("SELECT payload_json FROM research_project_entities WHERE project_id=? AND entity_type=? ORDER BY updated_utc DESC LIMIT ?",(project_id,entity_type,max(1,min(1000,int(limit)))))
            else:
                rows=connection.execute("SELECT payload_json FROM research_project_entities WHERE project_id=? ORDER BY updated_utc DESC LIMIT ?",(project_id,max(1,min(1000,int(limit)))))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def save_project_event(self, project_id: str, event_type: str, payload: dict[str, Any], actor: str = "") -> dict[str, Any]:
        event={"event_id":"project-event-"+uuid.uuid4().hex,"project_id":project_id,"event_type":event_type[:100],"created_utc":utc_now(),"actor":actor[:160],"payload":payload}
        with self._lock, self._connection() as connection:
            connection.execute("INSERT INTO research_project_events(event_id,project_id,event_type,created_utc,actor,payload_json) VALUES(?,?,?,?,?,?)",(event["event_id"],project_id,event["event_type"],event["created_utc"],event["actor"],_canonical_json(event)))
        return event

    def project_bundle(self, project_id: str) -> dict[str, Any]:
        project=self.research_project(project_id)
        if not project: raise ValueError("Unknown research project.")
        handoffs=[x for x in self.platform_handoffs(1000) if str(x.get("payload",{}).get("project_id") or x.get("project_id") or "")==project_id]
        handoff_ids={str(x.get("handoff_id") or "") for x in handoffs}
        artifacts=[x for x in self.artifact_returns(1000) if str(x.get("handoff_id") or "") in handoff_ids]
        return {"project":project,"investigations":self.research_investigations(project_id,500),"entities":self.project_entities(project_id,"",1000),"handoffs":handoffs,"artifacts":artifacts}

    def save_connected_backup(self, envelope: dict[str, Any], state: str = "created") -> dict[str, Any]:
        backup_id=str(envelope.get("backup_id") or "backup-"+uuid.uuid4().hex); clean={**envelope,"backup_id":backup_id}
        with self._lock, self._connection() as connection:
            connection.execute("INSERT OR REPLACE INTO connected_platform_backups(backup_id,created_utc,checksum,state,payload_json) VALUES(?,?,?,?,?)",(backup_id,str(clean.get("created_utc") or utc_now()),str(clean.get("checksum") or ""),state,_canonical_json(clean)))
        return clean

    def connected_backups(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock, self._connection() as connection:
            rows=connection.execute("SELECT payload_json FROM connected_platform_backups ORDER BY created_utc DESC LIMIT ?",(max(1,min(100,int(limit))),))
            return [json.loads(str(row["payload_json"])) for row in rows]

    def connected_platform_summary(self) -> dict[str, Any]:
        with self._lock, self._connection() as connection:
            counts={name:int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for name,table in {"projects":"research_projects","investigations":"research_investigations","entities":"research_project_entities","backups":"connected_platform_backups"}.items()}
        return {"schema":"sc-connected-research-platform-summary/1.0","version":"7.0.2","counts":counts,"workspace_schema":"sc-research-librarian-public-workspace/2.0","api_schema":"sc-connected-research-api/1.0"}


store = KnowledgeStore()
