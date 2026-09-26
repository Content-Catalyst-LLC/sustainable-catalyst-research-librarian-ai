from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterator
import uuid

from .config import settings
from .models import utc_now
from .database_identity import validate_schema_name

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - Postgres dependencies are deployment-only in SQLite tests.
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]

JOB_SCHEMA = "sc-research-librarian-async-job/1.0"
JOB_EVENT_SCHEMA = "sc-research-librarian-async-job-event/1.0"
JOB_RUNTIME_SCHEMA = "sc-research-librarian-async-runtime/1.0"
JOB_TYPES = {
    "document-process",
    "document-intelligence",
    "ingestion",
    "embedding",
    "index",
    "validation",
    "connector-run",
    "source-identity",
    "research-intelligence-extraction",
    "argument-synthesis-plan",
    "statistical-analysis-plan",
    "visual-research-plan",
    "unified-research-runtime",
    "research-workflow-advance",
    "scholarly-research-package",
    "peer-review-validation-package",
    "scholarly-publication-package",
    "research-knowledge-graph-snapshot",
    "ai-research-context-snapshot",
    "rag-evaluation-snapshot",
    "ai-research-experiment-snapshot",
    "model-aware-research-snapshot",
    "unified-research-environment-snapshot",
    "research-question-hypothesis-snapshot",
    "research-design-methodology-snapshot",
    "evidence-search-strategy-snapshot",
    "systematic-review-evidence-synthesis-snapshot",
    "scholarly-literature-intelligence-snapshot",
    "argument-claim-counterclaim-intelligence-snapshot",
    "research-gap-novelty-intelligence-snapshot",
    "dataset-discovery-data-fitness-snapshot",
    "computational-research-planning-snapshot",
}
TERMINAL_STATES = {"succeeded", "failed", "cancelled"}
ACTIVE_STATES = {"queued", "retry_wait", "running"}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _due_iso(delay_seconds: float) -> str:
    return (_now_dt() + timedelta(seconds=max(0.0, float(delay_seconds)))).isoformat()


def _fingerprint(job_type: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(job_type.encode("utf-8"))
    digest.update(b"\n")
    digest.update(_json(payload).encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True)
class JobClaim:
    job_id: str
    job_type: str
    payload: dict[str, Any]
    attempts: int
    max_attempts: int
    worker_id: str


class AsyncJobStore:
    """Durable queue with Postgres SKIP LOCKED claims and SQLite local fallback."""

    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "async_jobs.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres async jobs require psycopg and pgvector backend dependencies.")
            if not settings.database_url:
                raise RuntimeError("DATABASE_URL is required for Postgres async jobs.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._migrate_sqlite()

    @contextmanager
    def _sqlite(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.sqlite_path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=30000")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _postgres(self, *, migration: bool = False) -> Iterator[Any]:
        url = (settings.direct_database_url if migration else settings.database_url) or settings.database_url
        connection = psycopg.connect(url, autocommit=False, row_factory=dict_row)
        try:
            connection.execute(f'SET search_path TO "{self.database_schema}"')
            yield connection
        finally:
            connection.close()

    def _migrate_sqlite(self) -> None:
        with self._lock, self._sqlite() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS async_jobs (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 100,
                    idempotency_key TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    result_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    progress INTEGER NOT NULL DEFAULT 0,
                    stage TEXT NOT NULL DEFAULT 'queued',
                    worker_id TEXT NOT NULL DEFAULT '',
                    lease_expires_utc TEXT NOT NULL DEFAULT '',
                    available_utc TEXT NOT NULL,
                    created_utc TEXT NOT NULL,
                    updated_utc TEXT NOT NULL,
                    started_utc TEXT NOT NULL DEFAULT '',
                    completed_utc TEXT NOT NULL DEFAULT '',
                    fingerprint TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_async_jobs_idempotency
                    ON async_jobs(idempotency_key) WHERE idempotency_key <> '';
                CREATE INDEX IF NOT EXISTS idx_async_jobs_claim
                    ON async_jobs(state, available_utc, priority, created_utc);
                CREATE TABLE IF NOT EXISTS async_job_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    stage TEXT NOT NULL DEFAULT '',
                    message TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_utc TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_async_job_events_job
                    ON async_job_events(job_id, event_id);
                """
            )

    def _migrate_postgres(self) -> None:
        with self._postgres(migration=True) as connection:
            connection.execute("SELECT pg_advisory_lock(hashtext('sc_rl_async_jobs_migration'))")
            connection.commit()
            try:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sc_rl_async_jobs (
                        job_id TEXT PRIMARY KEY,
                        job_type TEXT NOT NULL,
                        state TEXT NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 100,
                        idempotency_key TEXT NOT NULL DEFAULT '',
                        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        result JSONB NOT NULL DEFAULT '{}'::jsonb,
                        error TEXT NOT NULL DEFAULT '',
                        attempts INTEGER NOT NULL DEFAULT 0,
                        max_attempts INTEGER NOT NULL DEFAULT 3,
                        progress INTEGER NOT NULL DEFAULT 0,
                        stage TEXT NOT NULL DEFAULT 'queued',
                        worker_id TEXT NOT NULL DEFAULT '',
                        lease_expires_utc TIMESTAMPTZ,
                        available_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                        created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                        updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                        started_utc TIMESTAMPTZ,
                        completed_utc TIMESTAMPTZ,
                        fingerprint TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_async_jobs_idempotency "
                    "ON sc_rl_async_jobs(idempotency_key) WHERE idempotency_key <> ''"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sc_rl_async_jobs_claim "
                    "ON sc_rl_async_jobs(state, available_utc, priority, created_utc)"
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sc_rl_async_job_events (
                        event_id BIGSERIAL PRIMARY KEY,
                        job_id TEXT NOT NULL REFERENCES sc_rl_async_jobs(job_id) ON DELETE CASCADE,
                        event_type TEXT NOT NULL,
                        stage TEXT NOT NULL DEFAULT '',
                        message TEXT NOT NULL DEFAULT '',
                        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sc_rl_async_job_events_job "
                    "ON sc_rl_async_job_events(job_id, event_id)"
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                try:
                    connection.execute("SELECT pg_advisory_unlock(hashtext('sc_rl_async_jobs_migration'))")
                    connection.commit()
                except Exception:
                    connection.rollback()

    def _event(self, job_id: str, event_type: str, stage: str = "", message: str = "", payload: dict[str, Any] | None = None) -> None:
        now = utc_now()
        payload = payload or {}
        if self.backend == "postgres":
            with self._postgres() as connection:
                connection.execute(
                    "INSERT INTO sc_rl_async_job_events(job_id,event_type,stage,message,payload,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",
                    (job_id, event_type, stage, message[:1000], Jsonb(payload), now),
                )
                connection.commit()
            return
        with self._lock, self._sqlite() as connection:
            connection.execute(
                "INSERT INTO async_job_events(job_id,event_type,stage,message,payload_json,created_utc) VALUES(?,?,?,?,?,?)",
                (job_id, event_type, stage, message[:1000], _json(payload), now),
            )

    def _clean_job(self, row: dict[str, Any]) -> dict[str, Any]:
        output = dict(row)
        for key in ("payload", "result"):
            value = output.get(key)
            if isinstance(value, str):
                try:
                    output[key] = json.loads(value)
                except json.JSONDecodeError:
                    output[key] = {}
        for key, value in list(output.items()):
            if isinstance(value, datetime):
                output[key] = value.astimezone(timezone.utc).isoformat()
            elif value is None and key.endswith("_utc"):
                output[key] = ""
        output["schema"] = JOB_SCHEMA
        output["storage_backend"] = self.backend
        return output

    def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        *,
        priority: int = 100,
        max_attempts: int = 3,
        idempotency_key: str = "",
    ) -> tuple[dict[str, Any], bool]:
        if job_type not in JOB_TYPES:
            raise ValueError(f"Unsupported job type: {job_type}")
        now = utc_now()
        fingerprint = _fingerprint(job_type, payload)
        job_id = "job-" + uuid.uuid4().hex
        idempotency_key = idempotency_key.strip()[:220]
        priority = max(0, min(1000, int(priority)))
        max_attempts = max(1, min(20, int(max_attempts)))
        if self.backend == "postgres":
            with self._postgres() as connection:
                if idempotency_key:
                    existing = connection.execute(
                        "SELECT * FROM sc_rl_async_jobs WHERE idempotency_key=%s", (idempotency_key,)
                    ).fetchone()
                    if existing:
                        connection.commit()
                        return self._clean_job(existing), True
                row = connection.execute(
                    """
                    INSERT INTO sc_rl_async_jobs(
                        job_id,job_type,state,priority,idempotency_key,payload,result,error,attempts,max_attempts,
                        progress,stage,worker_id,available_utc,created_utc,updated_utc,fingerprint
                    ) VALUES(%s,%s,'queued',%s,%s,%s,'{}'::jsonb,'',0,%s,0,'queued','',%s,%s,%s,%s)
                    RETURNING *
                    """,
                    (job_id, job_type, priority, idempotency_key, Jsonb(payload), max_attempts, now, now, now, fingerprint),
                ).fetchone()
                connection.commit()
            self._event(job_id, "enqueued", "queued", payload={"job_type": job_type})
            return self._clean_job(row), False
        with self._lock, self._sqlite() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if idempotency_key:
                existing = connection.execute(
                    "SELECT * FROM async_jobs WHERE idempotency_key=?", (idempotency_key,)
                ).fetchone()
                if existing:
                    connection.commit()
                    data = dict(existing)
                    data["payload"] = data.pop("payload_json")
                    data["result"] = data.pop("result_json")
                    return self._clean_job(data), True
            connection.execute(
                """
                INSERT INTO async_jobs(
                    job_id,job_type,state,priority,idempotency_key,payload_json,result_json,error,attempts,max_attempts,
                    progress,stage,worker_id,lease_expires_utc,available_utc,created_utc,updated_utc,started_utc,completed_utc,fingerprint
                ) VALUES(?,?, 'queued', ?,?,?, '{}','',0,?,0,'queued','','',?,?,?,'','',?)
                """,
                (job_id, job_type, priority, idempotency_key, _json(payload), max_attempts, now, now, now, fingerprint),
            )
            connection.commit()
        self._event(job_id, "enqueued", "queued", payload={"job_type": job_type})
        return self.get(job_id), False

    def get(self, job_id: str) -> dict[str, Any]:
        if self.backend == "postgres":
            with self._postgres() as connection:
                row = connection.execute("SELECT * FROM sc_rl_async_jobs WHERE job_id=%s", (job_id,)).fetchone()
                connection.commit()
            if not row:
                raise KeyError(job_id)
            return self._clean_job(row)
        with self._lock, self._sqlite() as connection:
            row = connection.execute("SELECT * FROM async_jobs WHERE job_id=?", (job_id,)).fetchone()
        if not row:
            raise KeyError(job_id)
        data = dict(row)
        data["payload"] = data.pop("payload_json")
        data["result"] = data.pop("result_json")
        return self._clean_job(data)

    def list(self, *, state: str = "", job_type: str = "", limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(500, int(limit)))
        if self.backend == "postgres":
            clauses: list[str] = []
            args: list[Any] = []
            if state:
                clauses.append("state=%s"); args.append(state)
            if job_type:
                clauses.append("job_type=%s"); args.append(job_type)
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            with self._postgres() as connection:
                rows = connection.execute(
                    f"SELECT * FROM sc_rl_async_jobs{where} ORDER BY created_utc DESC LIMIT %s", (*args, limit)
                ).fetchall()
                connection.commit()
            return [self._clean_job(row) for row in rows]
        clauses = []; args = []
        if state:
            clauses.append("state=?"); args.append(state)
        if job_type:
            clauses.append("job_type=?"); args.append(job_type)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._lock, self._sqlite() as connection:
            rows = connection.execute(
                f"SELECT * FROM async_jobs{where} ORDER BY created_utc DESC LIMIT ?", (*args, limit)
            ).fetchall()
        output = []
        for row in rows:
            data = dict(row); data["payload"] = data.pop("payload_json"); data["result"] = data.pop("result_json")
            output.append(self._clean_job(data))
        return output

    def claim(self, worker_id: str, lease_seconds: int) -> JobClaim | None:
        now = utc_now(); lease = _due_iso(lease_seconds)
        if self.backend == "postgres":
            with self._postgres() as connection:
                row = connection.execute(
                    """
                    WITH candidate AS (
                        SELECT job_id FROM sc_rl_async_jobs
                        WHERE state IN ('queued','retry_wait') AND available_utc <= now()
                        ORDER BY priority ASC, created_utc ASC
                        FOR UPDATE SKIP LOCKED LIMIT 1
                    )
                    UPDATE sc_rl_async_jobs j SET
                        state='running', worker_id=%s, attempts=j.attempts+1, stage='claimed', progress=1,
                        started_utc=COALESCE(j.started_utc, now()), updated_utc=now(),
                        lease_expires_utc=now() + (%s * interval '1 second'), error=''
                    FROM candidate c WHERE j.job_id=c.job_id RETURNING j.*
                    """,
                    (worker_id, lease_seconds),
                ).fetchone()
                connection.commit()
            if not row:
                return None
            clean = self._clean_job(row)
        else:
            with self._lock, self._sqlite() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM async_jobs WHERE state IN ('queued','retry_wait') AND available_utc<=? "
                    "ORDER BY priority ASC, created_utc ASC LIMIT 1", (now,)
                ).fetchone()
                if not row:
                    connection.commit(); return None
                connection.execute(
                    "UPDATE async_jobs SET state='running',worker_id=?,attempts=attempts+1,stage='claimed',progress=1,"
                    "started_utc=CASE WHEN started_utc='' THEN ? ELSE started_utc END,updated_utc=?,lease_expires_utc=?,error='' WHERE job_id=?",
                    (worker_id, now, now, lease, row["job_id"]),
                )
                connection.commit()
            clean = self.get(str(row["job_id"]))
        self._event(clean["job_id"], "claimed", "claimed", payload={"worker_id": worker_id, "attempt": clean["attempts"]})
        return JobClaim(
            job_id=clean["job_id"], job_type=clean["job_type"], payload=dict(clean.get("payload") or {}),
            attempts=int(clean["attempts"]), max_attempts=int(clean["max_attempts"]), worker_id=worker_id,
        )

    def heartbeat(self, job_id: str, worker_id: str, stage: str, progress: int, lease_seconds: int) -> None:
        progress = max(1, min(99, int(progress))); lease = _due_iso(lease_seconds); now = utc_now()
        if self.backend == "postgres":
            with self._postgres() as connection:
                updated = connection.execute(
                    "UPDATE sc_rl_async_jobs SET stage=%s,progress=%s,updated_utc=%s,lease_expires_utc=%s "
                    "WHERE job_id=%s AND state='running' AND worker_id=%s RETURNING job_id",
                    (stage, progress, now, lease, job_id, worker_id),
                ).fetchone(); connection.commit()
        else:
            with self._lock, self._sqlite() as connection:
                cur = connection.execute(
                    "UPDATE async_jobs SET stage=?,progress=?,updated_utc=?,lease_expires_utc=? "
                    "WHERE job_id=? AND state='running' AND worker_id=?",
                    (stage, progress, now, lease, job_id, worker_id),
                ); updated = cur.rowcount
        if not updated:
            raise RuntimeError("Job lease is no longer owned by this worker.")

    def succeed(self, job_id: str, worker_id: str, result: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        if self.backend == "postgres":
            with self._postgres() as connection:
                row = connection.execute(
                    "UPDATE sc_rl_async_jobs SET state='succeeded',result=%s,error='',progress=100,stage='completed',"
                    "worker_id='',lease_expires_utc=NULL,updated_utc=%s,completed_utc=%s "
                    "WHERE job_id=%s AND state='running' AND worker_id=%s RETURNING *",
                    (Jsonb(result), now, now, job_id, worker_id),
                ).fetchone(); connection.commit()
            if not row: raise RuntimeError("Cannot complete an unowned job lease.")
            clean = self._clean_job(row)
        else:
            with self._lock, self._sqlite() as connection:
                cur = connection.execute(
                    "UPDATE async_jobs SET state='succeeded',result_json=?,error='',progress=100,stage='completed',worker_id='',"
                    "lease_expires_utc='',updated_utc=?,completed_utc=? WHERE job_id=? AND state='running' AND worker_id=?",
                    (_json(result), now, now, job_id, worker_id),
                )
                if cur.rowcount != 1: raise RuntimeError("Cannot complete an unowned job lease.")
            clean = self.get(job_id)
        self._event(job_id, "succeeded", "completed", payload={"result_keys": sorted(result)})
        return clean

    def fail(self, job_id: str, worker_id: str, error: str, *, retry_base_seconds: float) -> dict[str, Any]:
        current = self.get(job_id)
        attempts = int(current["attempts"]); max_attempts = int(current["max_attempts"])
        retrying = attempts < max_attempts
        state = "retry_wait" if retrying else "failed"
        delay = min(settings.async_job_retry_max_seconds, retry_base_seconds * (2 ** max(0, attempts - 1))) if retrying else 0
        available = _due_iso(delay); now = utc_now(); stage = "retry_wait" if retrying else "failed"
        if self.backend == "postgres":
            with self._postgres() as connection:
                row = connection.execute(
                    "UPDATE sc_rl_async_jobs SET state=%s,error=%s,stage=%s,worker_id='',lease_expires_utc=NULL,"
                    "available_utc=%s,updated_utc=%s,completed_utc=CASE WHEN %s='failed' THEN %s ELSE completed_utc END "
                    "WHERE job_id=%s AND state='running' AND worker_id=%s RETURNING *",
                    (state, error[:4000], stage, available, now, state, now, job_id, worker_id),
                ).fetchone(); connection.commit()
            if not row: raise RuntimeError("Cannot fail an unowned job lease.")
            clean = self._clean_job(row)
        else:
            with self._lock, self._sqlite() as connection:
                cur = connection.execute(
                    "UPDATE async_jobs SET state=?,error=?,stage=?,worker_id='',lease_expires_utc='',available_utc=?,updated_utc=?,"
                    "completed_utc=CASE WHEN ?='failed' THEN ? ELSE completed_utc END WHERE job_id=? AND state='running' AND worker_id=?",
                    (state, error[:4000], stage, available, now, state, now, job_id, worker_id),
                )
                if cur.rowcount != 1: raise RuntimeError("Cannot fail an unowned job lease.")
            clean = self.get(job_id)
        self._event(job_id, "retry_scheduled" if retrying else "failed", stage, error[:1000], {"delay_seconds": delay})
        return clean

    def retry(self, job_id: str) -> dict[str, Any]:
        current = self.get(job_id)
        if current["state"] not in {"failed", "cancelled"}:
            raise ValueError("Only failed or cancelled jobs can be retried manually.")
        now = utc_now()
        if self.backend == "postgres":
            with self._postgres() as connection:
                connection.execute(
                    "UPDATE sc_rl_async_jobs SET state='queued',stage='queued',progress=0,error='',worker_id='',lease_expires_utc=NULL,"
                    "available_utc=%s,updated_utc=%s,completed_utc=NULL WHERE job_id=%s", (now, now, job_id)
                ); connection.commit()
        else:
            with self._lock, self._sqlite() as connection:
                connection.execute(
                    "UPDATE async_jobs SET state='queued',stage='queued',progress=0,error='',worker_id='',lease_expires_utc='',"
                    "available_utc=?,updated_utc=?,completed_utc='' WHERE job_id=?", (now, now, job_id)
                )
        self._event(job_id, "manual_retry", "queued")
        return self.get(job_id)

    def cancel(self, job_id: str) -> dict[str, Any]:
        current = self.get(job_id)
        if current["state"] in TERMINAL_STATES:
            return current
        now = utc_now()
        if self.backend == "postgres":
            with self._postgres() as connection:
                connection.execute(
                    "UPDATE sc_rl_async_jobs SET state='cancelled',stage='cancelled',worker_id='',lease_expires_utc=NULL,"
                    "updated_utc=%s,completed_utc=%s WHERE job_id=%s", (now, now, job_id)
                ); connection.commit()
        else:
            with self._lock, self._sqlite() as connection:
                connection.execute(
                    "UPDATE async_jobs SET state='cancelled',stage='cancelled',worker_id='',lease_expires_utc='',"
                    "updated_utc=?,completed_utc=? WHERE job_id=?", (now, now, job_id)
                )
        self._event(job_id, "cancelled", "cancelled")
        return self.get(job_id)

    def reclaim_stalled(self, lease_seconds: int) -> int:
        cutoff = utc_now()
        if self.backend == "postgres":
            with self._postgres() as connection:
                rows = connection.execute(
                    "UPDATE sc_rl_async_jobs SET state='retry_wait',stage='lease_recovered',worker_id='',lease_expires_utc=NULL,"
                    "available_utc=now(),updated_utc=now(),error='Recovered expired worker lease.' "
                    "WHERE state='running' AND lease_expires_utc IS NOT NULL AND lease_expires_utc < now() RETURNING job_id"
                ).fetchall(); connection.commit()
            count = len(rows)
        else:
            with self._lock, self._sqlite() as connection:
                cur = connection.execute(
                    "UPDATE async_jobs SET state='retry_wait',stage='lease_recovered',worker_id='',lease_expires_utc='',available_utc=?,"
                    "updated_utc=?,error='Recovered expired worker lease.' WHERE state='running' AND lease_expires_utc<>'' AND lease_expires_utc<?",
                    (cutoff, cutoff, cutoff),
                ); count = int(cur.rowcount)
        return count

    def events(self, job_id: str, limit: int = 200) -> list[dict[str, Any]]:
        self.get(job_id)
        limit = max(1, min(1000, int(limit)))
        if self.backend == "postgres":
            with self._postgres() as connection:
                rows = connection.execute(
                    "SELECT * FROM sc_rl_async_job_events WHERE job_id=%s ORDER BY event_id DESC LIMIT %s", (job_id, limit)
                ).fetchall(); connection.commit()
            output = []
            for row in rows:
                data = dict(row)
                if isinstance(data.get("created_utc"), datetime): data["created_utc"] = data["created_utc"].astimezone(timezone.utc).isoformat()
                data["schema"] = JOB_EVENT_SCHEMA; output.append(data)
            return output
        with self._lock, self._sqlite() as connection:
            rows = connection.execute(
                "SELECT * FROM async_job_events WHERE job_id=? ORDER BY event_id DESC LIMIT ?", (job_id, limit)
            ).fetchall()
        output = []
        for row in rows:
            data = dict(row); data["payload"] = json.loads(data.pop("payload_json") or "{}"); data["schema"] = JOB_EVENT_SCHEMA; output.append(data)
        return output

    def summary(self) -> dict[str, Any]:
        states = ["queued", "retry_wait", "running", "succeeded", "failed", "cancelled"]
        if self.backend == "postgres":
            with self._postgres() as connection:
                rows = connection.execute("SELECT state,count(*) AS count FROM sc_rl_async_jobs GROUP BY state").fetchall()
                connection.commit()
            counts = {str(row["state"]): int(row["count"]) for row in rows}
        else:
            with self._lock, self._sqlite() as connection:
                rows = connection.execute("SELECT state,count(*) AS count FROM async_jobs GROUP BY state").fetchall()
            counts = {str(row["state"]): int(row["count"]) for row in rows}
        return {
            "schema": JOB_RUNTIME_SCHEMA,
            "storage_backend": self.backend,
            "durable": True,
            "claim_strategy": "for-update-skip-locked" if self.backend == "postgres" else "begin-immediate",
            "states": {state: counts.get(state, 0) for state in states},
            "active": sum(counts.get(state, 0) for state in ACTIVE_STATES),
            "terminal": sum(counts.get(state, 0) for state in TERMINAL_STATES),
        }


_job_store: AsyncJobStore | None = None
_job_store_lock = threading.Lock()


def get_job_store() -> AsyncJobStore:
    global _job_store
    if _job_store is None:
        with _job_store_lock:
            if _job_store is None:
                _job_store = AsyncJobStore()
    return _job_store
