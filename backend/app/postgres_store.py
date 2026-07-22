from __future__ import annotations

"""Neon/Postgres durable knowledge index for Research Librarian v7.1.1.

The Postgres store owns only the knowledge-index lifecycle: source batches,
generations, records, retrieval chunks, embeddings, activation, recovery, and
snapshots. The existing SQLite store remains available for local development
and for ancillary governance/workspace data until those modules are migrated.

Production activation uses an active-generation pointer. No database files are
renamed, and a new generation is invisible to retrieval until its records,
chunks, and checksum have all been verified in Postgres.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import threading
from typing import Any, Iterable, Iterator
import uuid

try:  # Optional during SQLite-only local tests.
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from pgvector import Vector
    from pgvector.psycopg import register_vector
except ImportError:  # pragma: no cover - exercised only on misconfigured deploys.
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]
    Vector = None  # type: ignore[assignment]
    register_vector = None  # type: ignore[assignment]

from .chunking import chunk_record
from .config import settings
from .database_identity import (
    compare_live_identities,
    configured_identity,
    live_database_identity,
    validate_schema_name,
)
from .models import KnowledgeChunk, KnowledgeRecord, utc_now
from .store import KnowledgeStore, SyncResult, _canonical_json, record_hash


POSTGRES_SCHEMA_VERSION = 2
POSTGRES_INDEX_SCHEMA = "sc-research-librarian-postgres-index/1.1"


def _sha256_records(rows: Iterable[dict[str, Any]], seed: str = "") -> str:
    value = seed or hashlib.sha256(b"").hexdigest()
    for row in rows:
        digest = hashlib.sha256()
        digest.update(value.encode("ascii", errors="ignore"))
        digest.update(b"\n")
        digest.update(str(row.get("record_id") or row.get("id") or "").encode("utf-8"))
        digest.update(b":")
        digest.update(str(row.get("content_hash") or "").encode("ascii", errors="ignore"))
        value = digest.hexdigest()
    return value


def _redacted_database_label(url: str) -> str:
    if not url:
        return "postgres://not-configured"
    try:
        tail = url.rsplit("@", 1)[-1]
        return "postgres://" + tail
    except Exception:
        return "postgres://configured"


class PostgresKnowledgeStore:
    """Durable Postgres generation store with SQLite ancillary delegation."""

    CORE_METHODS = {
        "sync",
        "sync_job_status",
        "reconcile_sync_job",
        "queue_sync_commit",
        "advance_sync_commit",
        "commit_sync_job",
        "reset_sync_job",
        "repair_stalled_jobs",
        "records",
        "chunks",
        "pending_chunks",
        "save_chunk_embedding",
        "begin_embedding_run",
        "finish_embedding_run",
        "embedding_status",
        "summary",
        "manifest",
        "job_rejections",
        "list_snapshots",
        "validate_snapshots",
        "rollback",
        "database_diagnostics",
        "database_identity",
    }

    def __init__(self, legacy_store: KnowledgeStore | None = None) -> None:
        if psycopg is None or Jsonb is None:
            raise RuntimeError(
                "SC_RL_DATABASE_BACKEND=postgres requires psycopg, psycopg_pool, and pgvector. "
                "Install backend/requirements.txt before starting the service."
            )
        self.database_url = settings.database_url
        self.direct_database_url = settings.direct_database_url
        self.database_schema = validate_schema_name(settings.database_schema)
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required when SC_RL_DATABASE_BACKEND=postgres.")
        if settings.database_fail_closed and not self.direct_database_url:
            raise RuntimeError(
                "DIRECT_DATABASE_URL is required in fail-closed Postgres mode so migrations cannot "
                "silently target a different or pooled-only connection."
            )
        self.direct_database_url = self.direct_database_url or self.database_url
        self._configured_identity = configured_identity(
            self.database_url, self.direct_database_url, self.database_schema
        )
        self._legacy = legacy_store or KnowledgeStore()
        self._lock = threading.RLock()
        self._identity: dict[str, Any] = {}
        self._migrate()
        self._identity = self._verify_database_identity()

    def __getattr__(self, name: str) -> Any:
        # Governance, handoffs, calibration, and project workspaces remain on the
        # ancillary SQLite store in v7.1.1. Knowledge-index methods are fail-closed:
        # a missing Postgres implementation can never silently fall through.
        if name in self.CORE_METHODS:
            raise AttributeError(f"Postgres knowledge-index method {name!r} is not implemented.")
        return getattr(self._legacy, name)

    @contextmanager
    def _connection(self, *, migration: bool = False) -> Iterator[Any]:
        url = self.direct_database_url if migration else self.database_url
        connection = psycopg.connect(url, autocommit=False, row_factory=dict_row)
        try:
            # database_schema is validated as a simple identifier before use.
            connection.execute(f'SET search_path TO "{self.database_schema}"')
            if register_vector is not None:
                try:
                    register_vector(connection)
                except Exception:
                    # The migration creates the extension. A first connection may
                    # be established before the type exists.
                    pass
            yield connection
        finally:
            connection.close()

    def _verify_database_identity(self) -> dict[str, Any]:
        runtime_target = self._configured_identity["runtime"]
        direct_target = self._configured_identity["direct"]
        with self._connection() as runtime_connection:
            runtime = live_database_identity(runtime_connection, runtime_target)
            table_rows = runtime_connection.execute(
                """
                SELECT to_regclass('sc_rl_generations') IS NOT NULL AS generations,
                       to_regclass('sc_rl_records') IS NOT NULL AS records,
                       to_regclass('sc_rl_chunks') IS NOT NULL AS chunks,
                       to_regclass('sc_rl_meta') IS NOT NULL AS meta
                """
            ).fetchone()
        with self._connection(migration=True) as direct_connection:
            direct = live_database_identity(direct_connection, direct_target)
        comparison = compare_live_identities(runtime, direct)
        if not comparison["identity_match"]:
            raise RuntimeError(
                "Runtime and migration Postgres connections resolve to different database identities: "
                + ", ".join(comparison["identity_mismatches"])
            )
        for label, live in (("runtime", runtime), ("migration", direct)):
            if live["database"] != runtime_target.database or live["user"] != runtime_target.user:
                raise RuntimeError(
                    f"The {label} connection resolved to an unexpected database or role. "
                    "Check the Neon branch, database, and role selected in both connection strings."
                )
            if live["schema"] != self.database_schema:
                raise RuntimeError(
                    f"The {label} connection did not enter schema {self.database_schema!r}."
                )
            if not live["vector_enabled"]:
                raise RuntimeError("The pgvector extension is not enabled in the configured Neon database.")
        migration_ready = all(bool(table_rows.get(name)) for name in ("generations", "records", "chunks", "meta"))
        if not migration_ready:
            raise RuntimeError("The Neon schema migration did not create all required Research Librarian tables.")
        identity = {
            "configured_fingerprint": self._configured_identity["configured_fingerprint"],
            "runtime": runtime,
            "direct": direct,
            **comparison,
            "migration_ready": migration_ready,
            "database_ready": True,
            "fail_closed": bool(settings.database_fail_closed),
        }
        with self._connection() as connection:
            now = utc_now()
            connection.execute(
                """
                INSERT INTO sc_rl_meta(key,value,updated_utc) VALUES
                  ('storage_backend',to_jsonb('postgres'::text),%s),
                  ('database_fingerprint',to_jsonb(%s::text),%s),
                  ('release_version',to_jsonb(%s::text),%s),
                  ('migration_version',to_jsonb(%s::int),%s)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_utc=excluded.updated_utc
                """,
                (now, runtime["live_fingerprint"], now, settings.release_version, now, POSTGRES_SCHEMA_VERSION, now),
            )
            connection.commit()
        return identity

    def _database_fingerprint(self) -> str:
        runtime = self._identity.get("runtime", {}) if isinstance(self._identity, dict) else {}
        return str(runtime.get("live_fingerprint") or self._configured_identity["configured_fingerprint"])

    def _migrate(self) -> None:
        with self._lock, self._connection(migration=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(hashtext('sc_rl_postgres_migration'))")
                connection.commit()
                try:
                    cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.database_schema}"')
                    cursor.execute(f'SET search_path TO "{self.database_schema}"')
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_meta (
                            key TEXT PRIMARY KEY,
                            value JSONB NOT NULL,
                            updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
                        )
                        """
                    )
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_generations (
                            generation_id TEXT PRIMARY KEY,
                            job_id TEXT UNIQUE NOT NULL,
                            source_site TEXT NOT NULL DEFAULT '',
                            mode TEXT NOT NULL DEFAULT 'replace',
                            state TEXT NOT NULL DEFAULT 'staging',
                            commit_phase TEXT NOT NULL DEFAULT 'staged',
                            commit_progress INTEGER NOT NULL DEFAULT 0,
                            expected_batches INTEGER NOT NULL DEFAULT 0,
                            received_batches INTEGER[] NOT NULL DEFAULT '{}',
                            staged_records INTEGER NOT NULL DEFAULT 0,
                            staged_deletions INTEGER NOT NULL DEFAULT 0,
                            rejected_records INTEGER NOT NULL DEFAULT 0,
                            activation_records INTEGER NOT NULL DEFAULT 0,
                            activation_total INTEGER NOT NULL DEFAULT 0,
                            indexed_chunks INTEGER NOT NULL DEFAULT 0,
                            chunk_records_processed INTEGER NOT NULL DEFAULT 0,
                            checksum_records INTEGER NOT NULL DEFAULT 0,
                            activation_cursor TEXT NOT NULL DEFAULT '',
                            chunk_cursor TEXT NOT NULL DEFAULT '',
                            checksum_cursor TEXT NOT NULL DEFAULT '',
                            activation_checksum TEXT NOT NULL DEFAULT '',
                            activation_step_count INTEGER NOT NULL DEFAULT 0,
                            activation_restart_count INTEGER NOT NULL DEFAULT 0,
                            recovery_generation INTEGER NOT NULL DEFAULT 0,
                            active BOOLEAN NOT NULL DEFAULT FALSE,
                            error TEXT NOT NULL DEFAULT '',
                            result JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                            updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                            commit_started_utc TIMESTAMPTZ,
                            commit_heartbeat_utc TIMESTAMPTZ,
                            completed_utc TIMESTAMPTZ
                        )
                        """
                    )
                    cursor.execute("ALTER TABLE sc_rl_generations ADD COLUMN IF NOT EXISTS storage_backend TEXT NOT NULL DEFAULT 'postgres'")
                    cursor.execute("ALTER TABLE sc_rl_generations ADD COLUMN IF NOT EXISTS database_fingerprint TEXT NOT NULL DEFAULT ''")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_generations_state ON sc_rl_generations(state, updated_utc DESC)")
                    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sc_rl_one_active_generation ON sc_rl_generations(active) WHERE active")
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_sync_batches (
                            generation_id TEXT NOT NULL REFERENCES sc_rl_generations(generation_id) ON DELETE CASCADE,
                            batch_index INTEGER NOT NULL,
                            batch_hash TEXT NOT NULL,
                            record_count INTEGER NOT NULL DEFAULT 0,
                            created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                            PRIMARY KEY(generation_id, batch_index)
                        )
                        """
                    )
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_staging_records (
                            generation_id TEXT NOT NULL REFERENCES sc_rl_generations(generation_id) ON DELETE CASCADE,
                            record_id TEXT NOT NULL,
                            title TEXT NOT NULL,
                            url TEXT NOT NULL,
                            payload JSONB NOT NULL,
                            content_hash TEXT NOT NULL,
                            updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                            PRIMARY KEY(generation_id, record_id)
                        )
                        """
                    )
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_staging_cursor ON sc_rl_staging_records(generation_id, record_id)")
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_staging_deletions (
                            generation_id TEXT NOT NULL REFERENCES sc_rl_generations(generation_id) ON DELETE CASCADE,
                            record_id TEXT NOT NULL,
                            PRIMARY KEY(generation_id, record_id)
                        )
                        """
                    )
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_records (
                            generation_id TEXT NOT NULL REFERENCES sc_rl_generations(generation_id) ON DELETE CASCADE,
                            record_id TEXT NOT NULL,
                            title TEXT NOT NULL,
                            url TEXT NOT NULL,
                            payload JSONB NOT NULL,
                            content_hash TEXT NOT NULL,
                            updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                            PRIMARY KEY(generation_id, record_id)
                        )
                        """
                    )
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_records_generation_title ON sc_rl_records(generation_id, lower(title))")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_records_generation_url ON sc_rl_records(generation_id, url)")
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_chunks (
                            generation_id TEXT NOT NULL REFERENCES sc_rl_generations(generation_id) ON DELETE CASCADE,
                            chunk_id TEXT NOT NULL,
                            record_id TEXT NOT NULL,
                            heading TEXT NOT NULL DEFAULT '',
                            page INTEGER,
                            passage TEXT NOT NULL DEFAULT '',
                            position INTEGER NOT NULL DEFAULT 0,
                            content_hash TEXT NOT NULL DEFAULT '',
                            embedding_model TEXT NOT NULL DEFAULT '',
                            embedding vector,
                            updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                            PRIMARY KEY(generation_id, chunk_id),
                            FOREIGN KEY(generation_id, record_id) REFERENCES sc_rl_records(generation_id, record_id) ON DELETE CASCADE
                        )
                        """
                    )
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_chunks_record ON sc_rl_chunks(generation_id, record_id, position)")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_chunks_embedding_model ON sc_rl_chunks(generation_id, embedding_model) WHERE embedding IS NOT NULL")
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_sync_rejections (
                            rejection_id BIGSERIAL PRIMARY KEY,
                            generation_id TEXT NOT NULL REFERENCES sc_rl_generations(generation_id) ON DELETE CASCADE,
                            batch_index INTEGER NOT NULL,
                            record_id TEXT NOT NULL DEFAULT '',
                            error TEXT NOT NULL,
                            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                            created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
                        )
                        """
                    )
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sc_rl_embedding_runs (
                            run_id TEXT PRIMARY KEY,
                            generation_id TEXT,
                            model TEXT NOT NULL,
                            requested INTEGER NOT NULL DEFAULT 0,
                            processed INTEGER NOT NULL DEFAULT 0,
                            failed INTEGER NOT NULL DEFAULT 0,
                            error TEXT NOT NULL DEFAULT '',
                            started_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
                            completed_utc TIMESTAMPTZ
                        )
                        """
                    )
                    cursor.execute(
                        """
                        INSERT INTO sc_rl_meta(key,value) VALUES
                            ('schema_version', to_jsonb(%s::int)),
                            ('index_schema', to_jsonb(%s::text)),
                            ('index_version', '0'::jsonb)
                        ON CONFLICT(key) DO UPDATE SET
                            value=CASE WHEN excluded.key IN ('schema_version','index_schema') THEN excluded.value ELSE sc_rl_meta.value END,
                            updated_utc=now()
                        """,
                        (POSTGRES_SCHEMA_VERSION, POSTGRES_INDEX_SCHEMA),
                    )
                    connection.commit()
                except Exception:
                    connection.rollback()
                    raise
                finally:
                    try:
                        cursor.execute("SELECT pg_advisory_unlock(hashtext('sc_rl_postgres_migration'))")
                        connection.commit()
                    except Exception:
                        connection.rollback()

    @staticmethod
    def _generation_id(job_id: str) -> str:
        return "gen-" + hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:40]

    @staticmethod
    def _iso(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        return str(value)

    @staticmethod
    def _batch_manifest(expected: int, received: list[int]) -> tuple[list[int], str]:
        missing = [index for index in range(1, max(0, expected) + 1) if index not in set(received)]
        if expected <= 0 and not received:
            return missing, "empty"
        if missing:
            return missing, "incomplete"
        return missing, "complete"

    @staticmethod
    def _json_scalar(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        return str(value)

    def _active_generation_status(self, connection: Any) -> dict[str, Any]:
        rows = connection.execute(
            "SELECT generation_id,state,active,database_fingerprint,activation_checksum FROM sc_rl_generations WHERE active=TRUE ORDER BY updated_utc DESC"
        ).fetchall()
        meta_row = connection.execute("SELECT value FROM sc_rl_meta WHERE key='active_generation_id'").fetchone()
        meta_generation = self._json_scalar(meta_row["value"]) if meta_row else ""
        if not rows:
            return {
                "generation_id": "", "meta_generation_id": meta_generation, "verified": False,
                "records": 0, "chunks": 0, "state": "missing", "error": "No active Neon generation is selected.",
            }
        if len(rows) != 1:
            return {
                "generation_id": "", "meta_generation_id": meta_generation, "verified": False,
                "records": 0, "chunks": 0, "state": "invalid", "error": "Multiple active Neon generations were detected.",
            }
        row = rows[0]
        generation_id = str(row["generation_id"] or "")
        counts = connection.execute(
            "SELECT (SELECT count(*) FROM sc_rl_records WHERE generation_id=%s) AS records,"
            " (SELECT count(*) FROM sc_rl_chunks WHERE generation_id=%s) AS chunks",
            (generation_id, generation_id),
        ).fetchone()
        records = int(counts["records"] or 0)
        chunks = int(counts["chunks"] or 0)
        state = str(row["state"] or "")
        fingerprint = str(row.get("database_fingerprint") or "")
        expected_fingerprint = self._database_fingerprint()
        errors: list[str] = []
        if state != "committed":
            errors.append(f"generation state is {state or 'unknown'}")
        if not meta_generation or meta_generation != generation_id:
            errors.append("active-generation pointer does not match the active row")
        if records <= 0:
            errors.append("active generation contains no records")
        if chunks <= 0:
            errors.append("active generation contains no retrieval chunks")
        if fingerprint != expected_fingerprint:
            errors.append("generation belongs to a different database identity")
        return {
            "generation_id": generation_id,
            "meta_generation_id": meta_generation,
            "verified": not errors,
            "records": records,
            "chunks": chunks,
            "state": state,
            "database_fingerprint": fingerprint,
            "expected_database_fingerprint": expected_fingerprint,
            "checksum": str(row.get("activation_checksum") or ""),
            "error": "; ".join(errors),
        }

    def _active_generation(self, connection: Any) -> str:
        status = self._active_generation_status(connection)
        return str(status["generation_id"]) if status.get("verified") else ""

    def _summary_connection(self, connection: Any) -> dict[str, Any]:
        active_status = self._active_generation_status(connection)
        active = str(active_status.get("generation_id") or "") if active_status.get("verified") else ""
        if active:
            counts = connection.execute(
                """
                SELECT
                  (SELECT count(*) FROM sc_rl_records WHERE generation_id=%s) AS total_records,
                  (SELECT count(DISTINCT lower(trim(title))) FROM sc_rl_records WHERE generation_id=%s AND trim(title)<>'') AS indexed_titles,
                  (SELECT count(*) FROM sc_rl_chunks WHERE generation_id=%s) AS indexed_chunks,
                  (SELECT count(*) FROM sc_rl_chunks WHERE generation_id=%s AND embedding IS NOT NULL AND embedding_model=%s) AS embedded_chunks
                """,
                (active, active, active, active, settings.gemini_embedding_model),
            ).fetchone()
            generation = connection.execute("SELECT * FROM sc_rl_generations WHERE generation_id=%s", (active,)).fetchone()
        else:
            counts = {"total_records": 0, "indexed_titles": 0, "indexed_chunks": 0, "embedded_chunks": 0}
            generation = None
        staging_jobs = int(connection.execute("SELECT count(*) AS count FROM sc_rl_generations WHERE state NOT IN ('committed','failed','cancelled')").fetchone()["count"])
        total_records = int(counts["total_records"] or 0)
        indexed_chunks = int(counts["indexed_chunks"] or 0)
        embedded_chunks = int(counts["embedded_chunks"] or 0)
        index_version_row = connection.execute("SELECT value FROM sc_rl_meta WHERE key='index_version'").fetchone()
        index_version = int(index_version_row["value"] or 0) if index_version_row else 0
        ancillary = self._legacy.summary()
        retrieval_config = self._legacy.retrieval_config()
        return {
            "schema_version": POSTGRES_SCHEMA_VERSION,
            "index_schema": POSTGRES_INDEX_SCHEMA,
            "index_version": index_version,
            "total_records": total_records,
            "indexed_titles": int(counts["indexed_titles"] or 0),
            "checksum": str(generation["activation_checksum"] or "") if generation else "",
            "storage_engine": "postgres-neon",
            "database_path": _redacted_database_label(self.database_url),
            "database_backend": "postgres",
            "staging_jobs": staging_jobs,
            "stalled_jobs": 0,
            "snapshot_count": int(connection.execute("SELECT count(*) AS count FROM sc_rl_generations WHERE state='committed'").fetchone()["count"]),
            "indexed_chunks": indexed_chunks,
            "embedded_chunks": embedded_chunks,
            "semantic_coverage": round((embedded_chunks / indexed_chunks) * 100, 2) if indexed_chunks else 0.0,
            "embedding_model": settings.gemini_embedding_model,
            "last_sync_utc": self._iso(generation["completed_utc"]) if generation else "",
            "source_site": str(generation["source_site"] or "") if generation else "",
            "active_generation_id": active,
            "active_generation_candidate_id": str(active_status.get("generation_id") or ""),
            "active_generation_verified": bool(active_status.get("verified")),
            "active_generation_error": str(active_status.get("error") or ""),
            "database_fingerprint": self._database_fingerprint(),
            "database_identity_match": bool(self._identity.get("identity_match", False)),
            "database_ready": bool(self._identity.get("database_ready", False)),
            "recovery_needed": total_records == 0,
            "storage_persistent": True,
            "storage_warning": "",
            "postgres_schema_version": POSTGRES_SCHEMA_VERSION,
            "retrieval_profile": retrieval_config.get("profile", "balanced-v6.5.0"),
            "benchmark_runs": int(ancillary.get("benchmark_runs", 0)),
            "handoff_count": int(ancillary.get("handoff_count", 0)),
            "artifact_return_count": int(ancillary.get("artifact_return_count", 0)),
            "answer_trace_count": int(ancillary.get("answer_trace_count", 0)),
            "release_gate_count": int(ancillary.get("release_gate_count", 0)),
            "source_review_count": int(ancillary.get("source_review_count", 0)),
        }

    def database_diagnostics(self) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT current_database() AS database_name,
                       current_user AS database_user,
                       current_schema() AS database_schema,
                       current_setting('neon.branch_id', true) AS branch_id,
                       current_setting('neon.project_id', true) AS project_id,
                       version() AS postgres_version,
                       pg_database_size(current_database()) AS database_bytes,
                       EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector') AS vector_enabled,
                       (SELECT count(*) FROM sc_rl_generations) AS generation_rows,
                       (SELECT count(*) FROM sc_rl_records) AS record_rows,
                       (SELECT count(*) FROM sc_rl_chunks) AS chunk_rows
                """
            ).fetchone()
            summary = self._summary_connection(connection)
            active_status = self._active_generation_status(connection)
        database_mb = round(int(row["database_bytes"] or 0) / 1048576, 2)
        warning_mb = settings.neon_free_storage_warning_mb
        runtime_identity = dict(self._identity.get("runtime", {}))
        direct_identity = dict(self._identity.get("direct", {}))
        return {
            "ok": True,
            "backend": "postgres",
            "effective_backend": "postgres",
            "configured_backend": settings.database_backend,
            "provider": "neon-compatible",
            "database_name": str(row["database_name"]),
            "database_user": str(row["database_user"]),
            "database_schema": str(row["database_schema"]),
            "branch_id": str(row.get("branch_id") or runtime_identity.get("branch_id") or ""),
            "project_id": str(row.get("project_id") or runtime_identity.get("project_id") or ""),
            "endpoint_id": str(runtime_identity.get("endpoint_id") or ""),
            "runtime_host": str(runtime_identity.get("host") or ""),
            "direct_host": str(direct_identity.get("host") or ""),
            "runtime_connection_label": self._configured_identity["runtime"].public_dict()["label"],
            "direct_connection_label": self._configured_identity["direct"].public_dict()["label"],
            "postgres_version": str(row["postgres_version"]).split(",")[0],
            "database_bytes": int(row["database_bytes"] or 0),
            "database_megabytes": database_mb,
            "free_tier_warning_megabytes": warning_mb,
            "free_tier_headroom_megabytes": max(0.0, round(500.0 - database_mb, 2)),
            "storage_warning": (f"Neon database usage is {database_mb} MB; clean superseded generations or increase capacity." if database_mb >= warning_mb else ""),
            "vector_enabled": bool(row["vector_enabled"]),
            "pooled_runtime": bool(runtime_identity.get("pooled")),
            "direct_migrations": bool(settings.direct_database_url),
            "direct_is_pooled": bool(direct_identity.get("pooled")),
            "identity_match": bool(self._identity.get("identity_match", False)),
            "identity_mismatches": list(self._identity.get("identity_mismatches", [])),
            "database_fingerprint": self._database_fingerprint(),
            "configured_fingerprint": str(self._identity.get("configured_fingerprint") or ""),
            "migration_ready": bool(self._identity.get("migration_ready", False)),
            "database_ready": bool(self._identity.get("database_ready", False)),
            "fail_closed": bool(settings.database_fail_closed),
            "connection_label": _redacted_database_label(self.database_url),
            "generation_rows": int(row.get("generation_rows") or 0),
            "record_rows": int(row.get("record_rows") or 0),
            "chunk_rows": int(row.get("chunk_rows") or 0),
            "active_generation_verified": bool(active_status.get("verified")),
            "active_generation_error": str(active_status.get("error") or ""),
            "active_generation_candidate_id": str(active_status.get("generation_id") or ""),
            **summary,
        }

    def database_identity(self) -> dict[str, Any]:
        diagnostics = self.database_diagnostics()
        keys = (
            "backend", "effective_backend", "configured_backend", "database_name", "database_user",
            "database_schema", "branch_id", "project_id", "endpoint_id", "runtime_host", "direct_host",
            "pooled_runtime", "direct_is_pooled", "identity_match", "identity_mismatches",
            "database_fingerprint", "configured_fingerprint", "migration_ready", "database_ready",
            "fail_closed", "vector_enabled", "active_generation_id", "active_generation_verified",
            "active_generation_error", "generation_rows", "record_rows", "chunk_rows",
        )
        return {"ok": True, **{key: diagnostics.get(key) for key in keys}}

    def sync(
        self,
        records: list[dict[str, Any]],
        mode: str = "replace",
        source_site: str = "",
        job_id: str = "",
        batch_index: int = 1,
        batch_count: int = 1,
        deleted_ids: list[str] | None = None,
        reason: str = "wordpress-sync",
        defer_commit: bool = False,
    ) -> SyncResult:
        raw_records = list(records or [])
        deleted_ids = list(deleted_ids or [])
        job_id = str(job_id or f"sync-{uuid.uuid4().hex}").strip()
        generation_id = self._generation_id(job_id)
        now = utc_now()
        valid: list[KnowledgeRecord] = []
        rejected: list[dict[str, Any]] = []
        for position, raw in enumerate(raw_records):
            try:
                valid.append(KnowledgeRecord.model_validate(raw))
            except Exception as exc:
                rejected.append({
                    "position": position,
                    "record_id": str(raw.get("id") or "") if isinstance(raw, dict) else "",
                    "error": str(exc)[:1000],
                })
        batch_payload_hash = hashlib.sha256(_canonical_json({"mode": mode, "records": raw_records, "deleted_ids": deleted_ids}).encode("utf-8")).hexdigest()
        duplicate = False
        with self._lock, self._connection() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO sc_rl_generations(
                        generation_id,job_id,source_site,mode,state,commit_phase,expected_batches,
                        activation_checksum,storage_backend,database_fingerprint,created_utc,updated_utc
                    ) VALUES(%s,%s,%s,%s,'staging','staged',%s,%s,'postgres',%s,%s,%s)
                    ON CONFLICT(job_id) DO UPDATE SET
                        source_site=excluded.source_site,
                        expected_batches=GREATEST(sc_rl_generations.expected_batches, excluded.expected_batches),
                        storage_backend='postgres',
                        database_fingerprint=excluded.database_fingerprint,
                        updated_utc=excluded.updated_utc,
                        error=''
                    """,
                    (generation_id, job_id, source_site, mode, batch_count, hashlib.sha256(b"").hexdigest(), self._database_fingerprint(), now, now),
                )
                existing = connection.execute(
                    "SELECT batch_hash FROM sc_rl_sync_batches WHERE generation_id=%s AND batch_index=%s",
                    (generation_id, batch_index),
                ).fetchone()
                if existing:
                    if str(existing["batch_hash"]) != batch_payload_hash:
                        raise ValueError(f"Batch {batch_index} was already received with different content.")
                    duplicate = True
                else:
                    for record in valid:
                        payload = record.model_dump(exclude={"embedding"})
                        digest = record_hash(record)
                        connection.execute(
                            """
                            INSERT INTO sc_rl_staging_records(generation_id,record_id,title,url,payload,content_hash,updated_utc)
                            VALUES(%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT(generation_id,record_id) DO UPDATE SET
                              title=excluded.title,url=excluded.url,payload=excluded.payload,
                              content_hash=excluded.content_hash,updated_utc=excluded.updated_utc
                            """,
                            (generation_id, record.id, record.title, record.url, Jsonb(payload), digest, now),
                        )
                    for record_id in deleted_ids:
                        if str(record_id).strip():
                            connection.execute(
                                "INSERT INTO sc_rl_staging_deletions(generation_id,record_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                                (generation_id, str(record_id).strip()),
                            )
                    for item in rejected:
                        connection.execute(
                            "INSERT INTO sc_rl_sync_rejections(generation_id,batch_index,record_id,error,payload) VALUES(%s,%s,%s,%s,%s)",
                            (generation_id, batch_index, item["record_id"], item["error"], Jsonb(item)),
                        )
                    connection.execute(
                        "INSERT INTO sc_rl_sync_batches(generation_id,batch_index,batch_hash,record_count) VALUES(%s,%s,%s,%s)",
                        (generation_id, batch_index, batch_payload_hash, len(valid)),
                    )
                counts = connection.execute(
                    """
                    SELECT
                      (SELECT count(*) FROM sc_rl_staging_records WHERE generation_id=%s) AS staged_records,
                      (SELECT count(*) FROM sc_rl_staging_deletions WHERE generation_id=%s) AS staged_deletions,
                      (SELECT count(*) FROM sc_rl_sync_rejections WHERE generation_id=%s) AS rejected_records,
                      (SELECT coalesce(array_agg(batch_index ORDER BY batch_index),'{}'::int[]) FROM sc_rl_sync_batches WHERE generation_id=%s) AS received_batches
                    """,
                    (generation_id, generation_id, generation_id, generation_id),
                ).fetchone()
                received = list(counts["received_batches"] or [])
                missing, _ = self._batch_manifest(batch_count, received)
                ready = not missing and batch_count > 0
                state = "ready-to-commit" if ready else "staging"
                connection.execute(
                    """
                    UPDATE sc_rl_generations SET state=%s,commit_phase='staged',expected_batches=%s,
                      received_batches=%s,staged_records=%s,staged_deletions=%s,rejected_records=%s,
                      activation_total=%s,updated_utc=%s,error=''
                    WHERE generation_id=%s
                    """,
                    (state, batch_count, received, counts["staged_records"], counts["staged_deletions"], counts["rejected_records"], counts["staged_records"], now, generation_id),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        committed = False
        final_state = str(self.sync_job_status(job_id).get("state") or "staging")
        if batch_index == batch_count and not defer_commit:
            self.queue_sync_commit(job_id, reason)
            for _ in range(10000):
                status = self.advance_sync_commit(job_id, reason)
                if status.get("committed"):
                    committed = True
                    final_state = str(status.get("state") or "committed")
                    break
                if status.get("state") == "failed":
                    raise RuntimeError(str(status.get("error") or "Postgres activation failed."))
            else:
                raise RuntimeError("Postgres activation did not complete within the compatibility step limit.")
        summary = self.summary()
        status = self.sync_job_status(job_id)
        return SyncResult(
            state=final_state,
            committed=committed,
            received=len(raw_records),
            accepted=len(valid),
            rejected=len(rejected),
            rejected_records=rejected[: settings.max_rejection_details],
            inserted=0,
            updated=0,
            unchanged=0,
            deleted=0,
            staged_records=int(status.get("staged_records", 0)),
            staged_deletions=int(status.get("staged_deletions", 0)),
            duplicate_batch=duplicate,
            summary=summary,
        )

    def sync_job_status(self, job_id: str) -> dict[str, Any]:
        job_id = str(job_id or "").strip()
        if not job_id:
            return {"ok": False, "exists": False, "job_id": "", "state": "missing", "committed": False, "error": "A synchronization job ID is required."}
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM sc_rl_generations WHERE job_id=%s", (job_id,)).fetchone()
            if not row:
                return {
                    "ok": True, "exists": False, "job_id": job_id, "state": "missing", "raw_state": "missing", "committed": False,
                    "batch_count": 0, "received_batches": [], "missing_batches": [], "staged_records": 0,
                    "staged_deletions": 0, "rejected_records": 0, "storage_engine": "postgres-neon",
                    "storage_backend": "postgres", "database_fingerprint": self._database_fingerprint(),
                    "database_identity_match": bool(self._identity.get("identity_match", False)),
                    "storage_persistent": True, "storage_path": _redacted_database_label(self.database_url),
                    "needs_full_replay": True, "can_activate": False, "error": "",
                }
            received = sorted(int(value) for value in (row["received_batches"] or []))
            expected = int(row["expected_batches"] or 0)
            missing, manifest_state = self._batch_manifest(expected, received)
            raw_state = str(row["state"] or "staging")
            generation_id = str(row["generation_id"] or "")
            counts = connection.execute(
                "SELECT (SELECT count(*) FROM sc_rl_records WHERE generation_id=%s) AS records,"
                " (SELECT count(*) FROM sc_rl_chunks WHERE generation_id=%s) AS chunks",
                (generation_id, generation_id),
            ).fetchone()
            generation_records = int(counts["records"] or 0)
            generation_chunks = int(counts["chunks"] or 0)
            active_status = self._active_generation_status(connection)
            row_fingerprint = str(row.get("database_fingerprint") or "")
            identity_valid = row_fingerprint == self._database_fingerprint() and str(row.get("storage_backend") or "") == "postgres"
            committed = (
                raw_state == "committed"
                and bool(row["active"])
                and identity_valid
                and bool(active_status.get("verified"))
                and str(active_status.get("generation_id") or "") == generation_id
            )
            state = raw_state
            committed_error = ""
            if raw_state == "committed" and not committed:
                state = "committed-empty" if generation_records <= 0 or generation_chunks <= 0 else "committed-unverified"
                committed_error = str(active_status.get("error") or "The committed generation failed Neon identity verification.")
            return {
                "ok": True,
                "exists": True,
                "job_id": job_id,
                "generation_id": generation_id,
                "transaction_id": generation_id,
                "state": state,
                "raw_state": raw_state,
                "committed": committed,
                "active": bool(row["active"]),
                "batch_count": expected,
                "received_batches": received,
                "received_batch_count": len(received),
                "missing_batches": missing,
                "batch_manifest_state": manifest_state,
                "staged_records": int(row["staged_records"] or 0),
                "staged_deletions": int(row["staged_deletions"] or 0),
                "rejected_records": int(row["rejected_records"] or 0),
                "generation_record_count": generation_records,
                "generation_chunk_count": generation_chunks,
                "commit_phase": str(row["commit_phase"] or ""),
                "commit_progress": int(row["commit_progress"] or 0),
                "activation_records": int(row["activation_records"] or 0),
                "activation_total": int(row["activation_total"] or 0),
                "indexed_chunks": int(row["indexed_chunks"] or 0),
                "chunk_records_processed": int(row["chunk_records_processed"] or 0),
                "checksum_records": int(row["checksum_records"] or 0),
                "activation_checksum": str(row["activation_checksum"] or ""),
                "activation_cursor": str(row["activation_cursor"] or ""),
                "chunk_cursor": str(row["chunk_cursor"] or ""),
                "checksum_cursor": str(row["checksum_cursor"] or ""),
                "activation_step_count": int(row["activation_step_count"] or 0),
                "activation_restart_count": int(row["activation_restart_count"] or 0),
                "recovery_generation": int(row["recovery_generation"] or 0),
                "started_utc": self._iso(row["created_utc"]),
                "updated_utc": self._iso(row["updated_utc"]),
                "completed_utc": self._iso(row["completed_utc"]),
                "commit_started_utc": self._iso(row["commit_started_utc"]),
                "commit_heartbeat_utc": self._iso(row["commit_heartbeat_utc"]),
                "storage_engine": "postgres-neon",
                "storage_backend": "postgres",
                "storage_path": _redacted_database_label(self.database_url),
                "storage_persistent": True,
                "storage_warning": "",
                "database_fingerprint": self._database_fingerprint(),
                "generation_database_fingerprint": row_fingerprint,
                "database_identity_match": identity_valid,
                "active_generation_id": str(active_status.get("generation_id") or "") if active_status.get("verified") else "",
                "active_generation_verified": bool(active_status.get("verified")),
                "can_activate": expected > 0 and len(received) == expected and not missing and identity_valid,
                "needs_full_replay": raw_state == "committed" and not committed,
                "error": committed_error or str(row["error"] or ""),
            }

    def reconcile_sync_job(self, job_id: str, expected_batch_count: int = 0) -> dict[str, Any]:
        status = self.sync_job_status(job_id)
        expected = max(0, int(expected_batch_count or 0))
        if not status.get("exists"):
            action, transaction_state = "replay-all", "missing"
        elif status.get("committed"):
            action, transaction_state = "committed", "committed"
        elif status.get("needs_full_replay"):
            action, transaction_state = "replay-all", str(status.get("state") or "committed-unverified")
        elif not status.get("database_identity_match", True):
            action, transaction_state = "replay-all", "database-identity-mismatch"
        elif expected and int(status.get("batch_count", 0)) != expected:
            action, transaction_state = "replay-all", "batch-count-mismatch"
        elif status.get("missing_batches"):
            action, transaction_state = "replay-missing", "incomplete"
        elif expected and int(status.get("received_batch_count", 0)) == expected:
            action, transaction_state = "activate", "complete"
        elif int(status.get("batch_count", 0)) <= 0:
            action, transaction_state = "replay-all", "empty-shell"
        else:
            action, transaction_state = "replay-all", "indeterminate"
        return {
            **status,
            "reconciliation_action": action,
            "transaction_state": transaction_state,
            "expected_batch_count": expected,
            "backend_batch_count": int(status.get("batch_count", 0)),
            "complete_for_expected_count": action in {"activate", "committed"},
        }

    def queue_sync_commit(self, job_id: str, reason: str = "wordpress-postgres-activation-v7.1.1") -> dict[str, Any]:
        status = self.sync_job_status(job_id)
        if not status.get("exists"):
            raise ValueError("The synchronization transaction does not exist.")
        if status.get("committed"):
            return {**status, "queued": False, "reason": "already-committed"}
        if status.get("needs_full_replay"):
            raise ValueError("The previous commit marker is not a verified Neon generation; replay the preserved WordPress staging file into a fresh transaction.")
        if not status.get("database_identity_match", True):
            raise ValueError("The synchronization transaction belongs to a different database identity and must be replayed.")
        if status.get("missing_batches") or not status.get("received_batches"):
            raise ValueError("The transaction is missing staged source batches.")
        now = utc_now()
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE sc_rl_generations SET state='commit-queued',commit_phase=CASE
                    WHEN commit_phase IN ('copying-records','building-chunks','checksumming','ready-to-switch') THEN commit_phase
                    ELSE 'preparing' END,
                    commit_progress=CASE WHEN commit_progress>0 THEN commit_progress ELSE 1 END,
                    commit_started_utc=coalesce(commit_started_utc,%s),commit_heartbeat_utc=%s,
                    activation_restart_count=activation_restart_count+1,updated_utc=%s,error=''
                WHERE job_id=%s
                """,
                (now, now, now, job_id),
            )
            connection.commit()
        return {**self.sync_job_status(job_id), "queued": True, "reason": reason}

    def advance_sync_commit(self, job_id: str, reason: str = "wordpress-postgres-activation-v7.1.1") -> dict[str, Any]:
        status = self.sync_job_status(job_id)
        if not status.get("exists"):
            raise ValueError("The synchronization transaction does not exist.")
        if status.get("committed"):
            return {**status, "advanced": False, "reason": "already-committed"}
        if status.get("needs_full_replay"):
            raise ValueError("The transaction has an unverified or empty commit marker and must be replayed into a fresh Neon generation.")
        if not status.get("database_identity_match", True):
            raise ValueError("The transaction belongs to a different database identity and must be replayed.")
        if status.get("missing_batches"):
            raise ValueError("The transaction is missing staged batch(es): " + ", ".join(map(str, status["missing_batches"])))
        generation_id = str(status["generation_id"])
        phase = str(status.get("commit_phase") or "preparing")
        now = utc_now()
        with self._lock, self._connection() as connection:
            try:
                if phase not in {"preparing", "copying-records", "building-chunks", "checksumming", "ready-to-switch"}:
                    phase = "preparing"
                if phase == "preparing":
                    connection.execute("DELETE FROM sc_rl_chunks WHERE generation_id=%s", (generation_id,))
                    connection.execute("DELETE FROM sc_rl_records WHERE generation_id=%s", (generation_id,))
                    connection.execute(
                        """
                        UPDATE sc_rl_generations SET state='committing',commit_phase='copying-records',commit_progress=5,
                          activation_records=0,indexed_chunks=0,chunk_records_processed=0,checksum_records=0,
                          activation_cursor='',chunk_cursor='',checksum_cursor='',activation_checksum=%s,
                          activation_step_count=activation_step_count+1,commit_heartbeat_utc=%s,updated_utc=%s,error=''
                        WHERE generation_id=%s
                        """,
                        (hashlib.sha256(b"").hexdigest(), now, now, generation_id),
                    )
                elif phase == "copying-records":
                    cursor_value = str(status.get("activation_cursor") or "")
                    rows = connection.execute(
                        """
                        SELECT record_id,title,url,payload,content_hash FROM sc_rl_staging_records
                        WHERE generation_id=%s AND record_id>%s ORDER BY record_id LIMIT %s
                        """,
                        (generation_id, cursor_value, settings.postgres_activation_record_batch_limit),
                    ).fetchall()
                    if rows:
                        for row in rows:
                            connection.execute(
                                """
                                INSERT INTO sc_rl_records(generation_id,record_id,title,url,payload,content_hash,updated_utc)
                                VALUES(%s,%s,%s,%s,%s,%s,%s)
                                ON CONFLICT(generation_id,record_id) DO UPDATE SET
                                  title=excluded.title,url=excluded.url,payload=excluded.payload,
                                  content_hash=excluded.content_hash,updated_utc=excluded.updated_utc
                                """,
                                (generation_id, row["record_id"], row["title"], row["url"], Jsonb(row["payload"]), row["content_hash"], now),
                            )
                        activation_records = int(status.get("activation_records", 0)) + len(rows)
                        progress = min(42, 5 + int(37 * activation_records / max(1, int(status.get("activation_total", 1)))))
                        connection.execute(
                            """
                            UPDATE sc_rl_generations SET state='committing',commit_phase='copying-records',commit_progress=%s,
                              activation_records=%s,activation_cursor=%s,activation_step_count=activation_step_count+1,
                              commit_heartbeat_utc=%s,updated_utc=%s WHERE generation_id=%s
                            """,
                            (progress, activation_records, str(rows[-1]["record_id"]), now, now, generation_id),
                        )
                    else:
                        connection.execute(
                            "UPDATE sc_rl_generations SET commit_phase='building-chunks',commit_progress=45,chunk_cursor='',activation_step_count=activation_step_count+1,commit_heartbeat_utc=%s,updated_utc=%s WHERE generation_id=%s",
                            (now, now, generation_id),
                        )
                elif phase == "building-chunks":
                    cursor_value = str(status.get("chunk_cursor") or "")
                    rows = connection.execute(
                        "SELECT record_id,payload FROM sc_rl_records WHERE generation_id=%s AND record_id>%s ORDER BY record_id LIMIT %s",
                        (generation_id, cursor_value, settings.postgres_activation_chunk_record_batch_limit),
                    ).fetchall()
                    if rows:
                        chunk_count = 0
                        for row in rows:
                            record = KnowledgeRecord.model_validate(row["payload"])
                            for chunk in chunk_record(record, settings.chunk_max_words, settings.chunk_overlap_words):
                                connection.execute(
                                    """
                                    INSERT INTO sc_rl_chunks(generation_id,chunk_id,record_id,heading,page,passage,position,content_hash,updated_utc)
                                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                                    ON CONFLICT(generation_id,chunk_id) DO UPDATE SET
                                      heading=excluded.heading,page=excluded.page,passage=excluded.passage,
                                      position=excluded.position,content_hash=excluded.content_hash,updated_utc=excluded.updated_utc
                                    """,
                                    (generation_id, chunk.chunk_id, chunk.record_id, chunk.heading, chunk.page, chunk.passage, chunk.position, chunk.content_hash, now),
                                )
                                chunk_count += 1
                        processed = int(status.get("chunk_records_processed", 0)) + len(rows)
                        indexed = int(status.get("indexed_chunks", 0)) + chunk_count
                        progress = min(78, 45 + int(33 * processed / max(1, int(status.get("activation_total", 1)))))
                        connection.execute(
                            """
                            UPDATE sc_rl_generations SET commit_phase='building-chunks',commit_progress=%s,
                              chunk_records_processed=%s,indexed_chunks=%s,chunk_cursor=%s,
                              activation_step_count=activation_step_count+1,commit_heartbeat_utc=%s,updated_utc=%s
                            WHERE generation_id=%s
                            """,
                            (progress, processed, indexed, str(rows[-1]["record_id"]), now, now, generation_id),
                        )
                    else:
                        connection.execute(
                            "UPDATE sc_rl_generations SET commit_phase='checksumming',commit_progress=80,checksum_cursor='',checksum_records=0,activation_checksum=%s,activation_step_count=activation_step_count+1,commit_heartbeat_utc=%s,updated_utc=%s WHERE generation_id=%s",
                            (hashlib.sha256(b"").hexdigest(), now, now, generation_id),
                        )
                elif phase == "checksumming":
                    cursor_value = str(status.get("checksum_cursor") or "")
                    rows = connection.execute(
                        "SELECT record_id,content_hash FROM sc_rl_records WHERE generation_id=%s AND record_id>%s ORDER BY record_id LIMIT %s",
                        (generation_id, cursor_value, settings.postgres_activation_checksum_batch_limit),
                    ).fetchall()
                    if rows:
                        checksum = _sha256_records(rows, str(status.get("activation_checksum") or ""))
                        checked = int(status.get("checksum_records", 0)) + len(rows)
                        progress = min(94, 80 + int(14 * checked / max(1, int(status.get("activation_total", 1)))))
                        connection.execute(
                            """
                            UPDATE sc_rl_generations SET commit_phase='checksumming',commit_progress=%s,
                              checksum_records=%s,checksum_cursor=%s,activation_checksum=%s,
                              activation_step_count=activation_step_count+1,commit_heartbeat_utc=%s,updated_utc=%s
                            WHERE generation_id=%s
                            """,
                            (progress, checked, str(rows[-1]["record_id"]), checksum, now, now, generation_id),
                        )
                    else:
                        connection.execute(
                            "UPDATE sc_rl_generations SET commit_phase='ready-to-switch',commit_progress=96,activation_step_count=activation_step_count+1,commit_heartbeat_utc=%s,updated_utc=%s WHERE generation_id=%s",
                            (now, now, generation_id),
                        )
                elif phase == "ready-to-switch":
                    counts = connection.execute(
                        "SELECT (SELECT count(*) FROM sc_rl_records WHERE generation_id=%s) AS records,(SELECT count(*) FROM sc_rl_chunks WHERE generation_id=%s) AS chunks",
                        (generation_id, generation_id),
                    ).fetchone()
                    expected = int(status.get("staged_records", 0))
                    if int(counts["records"] or 0) != expected or expected <= 0:
                        raise RuntimeError(f"Verified generation count mismatch: expected {expected}, found {int(counts['records'] or 0)}.")
                    if int(counts["chunks"] or 0) <= 0:
                        raise RuntimeError("Verified generation contains no retrieval chunks.")
                    version_row = connection.execute("SELECT value FROM sc_rl_meta WHERE key='index_version' FOR UPDATE").fetchone()
                    version = int(version_row["value"] or 0) + 1 if version_row else 1
                    fingerprint = self._database_fingerprint()
                    connection.execute("UPDATE sc_rl_generations SET active=FALSE WHERE active=TRUE")
                    connection.execute(
                        """
                        UPDATE sc_rl_generations SET active=TRUE,state='switching',commit_phase='verifying-active-generation',
                          commit_progress=98,database_fingerprint=%s,storage_backend='postgres',
                          commit_heartbeat_utc=%s,updated_utc=%s,error=''
                        WHERE generation_id=%s
                        """,
                        (fingerprint, now, now, generation_id),
                    )
                    connection.execute(
                        """
                        INSERT INTO sc_rl_meta(key,value,updated_utc) VALUES
                          ('active_generation_id',to_jsonb(%s::text),%s),
                          ('index_version',to_jsonb(%s::int),%s),
                          ('last_sync_utc',to_jsonb(%s::text),%s),
                          ('checksum',to_jsonb(%s::text),%s),
                          ('database_fingerprint',to_jsonb(%s::text),%s),
                          ('storage_backend',to_jsonb('postgres'::text),%s)
                        ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_utc=excluded.updated_utc
                        """,
                        (generation_id, now, version, now, now, now, str(status.get("activation_checksum") or ""), now, fingerprint, now, now),
                    )
                    verification = connection.execute(
                        """
                        SELECT g.generation_id,g.active,g.state,g.database_fingerprint,
                          (SELECT count(*) FROM sc_rl_records WHERE generation_id=g.generation_id) AS records,
                          (SELECT count(*) FROM sc_rl_chunks WHERE generation_id=g.generation_id) AS chunks,
                          (SELECT value FROM sc_rl_meta WHERE key='active_generation_id') AS active_pointer
                        FROM sc_rl_generations g WHERE g.generation_id=%s
                        """,
                        (generation_id,),
                    ).fetchone()
                    pointer = self._json_scalar(verification["active_pointer"]) if verification else ""
                    if (
                        not verification
                        or not bool(verification["active"])
                        or pointer != generation_id
                        or str(verification["database_fingerprint"] or "") != fingerprint
                        or int(verification["records"] or 0) != expected
                        or int(verification["chunks"] or 0) <= 0
                    ):
                        raise RuntimeError("The Neon active-generation switch failed verification; the transaction was not marked committed.")
                    result = {
                        "generation_id": generation_id,
                        "record_count": int(verification["records"]),
                        "indexed_chunks": int(verification["chunks"]),
                        "checksum": str(status.get("activation_checksum") or ""),
                        "reason": reason,
                        "storage_backend": "postgres",
                        "database_fingerprint": fingerprint,
                    }
                    connection.execute(
                        """
                        UPDATE sc_rl_generations SET state='committed',commit_phase='completed',commit_progress=100,
                          completed_utc=%s,commit_heartbeat_utc=%s,updated_utc=%s,result=%s,error=''
                        WHERE generation_id=%s AND active=TRUE AND database_fingerprint=%s
                        """,
                        (now, now, now, Jsonb(result), generation_id, fingerprint),
                    )
                    # Staging is no longer required after the verified pointer
                    # switch. Removing it immediately avoids retaining a second
                    # full copy of a 100+ MB WordPress export on Neon Free.
                    connection.execute("DELETE FROM sc_rl_staging_records WHERE generation_id=%s", (generation_id,))
                    connection.execute("DELETE FROM sc_rl_staging_deletions WHERE generation_id=%s", (generation_id,))
                    connection.execute("DELETE FROM sc_rl_sync_batches WHERE generation_id=%s", (generation_id,))
                    # Free-tier default retains only the active generation. Sites
                    # with larger Neon plans may raise SC_RL_POSTGRES_GENERATION_RETENTION.
                    obsolete = connection.execute(
                        """
                        SELECT generation_id FROM sc_rl_generations
                        WHERE state='committed' AND active=FALSE
                        ORDER BY completed_utc DESC NULLS LAST
                        OFFSET %s
                        """,
                        (max(0, settings.postgres_generation_retention - 1),),
                    ).fetchall()
                    if obsolete:
                        connection.execute(
                            "DELETE FROM sc_rl_generations WHERE generation_id=ANY(%s)",
                            ([str(item["generation_id"]) for item in obsolete],),
                        )
                connection.commit()
            except Exception as exc:
                connection.rollback()
                with self._connection() as failure:
                    failure.execute(
                        "UPDATE sc_rl_generations SET state='failed',commit_phase='failed',error=%s,updated_utc=%s,commit_heartbeat_utc=%s WHERE generation_id=%s",
                        (str(exc)[:2000], utc_now(), utc_now(), generation_id),
                    )
                    failure.commit()
                raise
        return {**self.sync_job_status(job_id), "advanced": True, "reason": reason}

    def commit_sync_job(self, job_id: str, reason: str = "compatibility-loop-v7.1.1") -> dict[str, Any]:
        self.queue_sync_commit(job_id, reason)
        for _ in range(10000):
            status = self.advance_sync_commit(job_id, reason)
            if status.get("committed") or status.get("state") == "failed":
                return status
        raise RuntimeError("Postgres commit compatibility loop exceeded its bounded step limit.")

    def reset_sync_job(self, job_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute("SELECT generation_id,active FROM sc_rl_generations WHERE job_id=%s", (job_id,)).fetchone()
            if not row:
                return {"ok": True, "deleted": False, "job_id": job_id}
            if bool(row["active"]):
                raise ValueError("The active committed generation cannot be reset.")
            connection.execute("DELETE FROM sc_rl_generations WHERE job_id=%s", (job_id,))
            connection.commit()
        return {"ok": True, "deleted": True, "job_id": job_id}

    def repair_stalled_jobs(self, max_age_seconds: int | None = None, purge_staging: bool = True) -> dict[str, Any]:
        age = max(300, int(max_age_seconds or settings.stalled_job_seconds))
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=age)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT job_id FROM sc_rl_generations WHERE state IN ('staging','commit-queued','committing') AND updated_utc<%s",
                (cutoff,),
            ).fetchall()
            job_ids = [str(row["job_id"]) for row in rows]
            if job_ids:
                connection.execute(
                    "UPDATE sc_rl_generations SET state='commit-stalled',error=%s,updated_utc=%s WHERE job_id=ANY(%s)",
                    (f"No bounded activation heartbeat for {age} seconds; durable Postgres cursors were preserved.", utc_now(), job_ids),
                )
            connection.commit()
        return {"ok": True, "repaired_jobs": job_ids, "count": len(job_ids), "purged": False, "max_age_seconds": age}

    def records(self) -> list[KnowledgeRecord]:
        with self._connection() as connection:
            active = self._active_generation(connection)
            if not active:
                return []
            rows = connection.execute("SELECT payload FROM sc_rl_records WHERE generation_id=%s ORDER BY record_id", (active,)).fetchall()
        return [KnowledgeRecord.model_validate(row["payload"]) for row in rows]

    @staticmethod
    def _embedding_list(value: Any) -> list[float] | None:
        if value is None:
            return None
        try:
            return [float(item) for item in value]
        except Exception:
            text = str(value).strip("[]")
            return [float(item) for item in text.split(",") if item.strip()] if text else None

    def chunks(self) -> list[KnowledgeChunk]:
        with self._connection() as connection:
            active = self._active_generation(connection)
            if not active:
                return []
            rows = connection.execute(
                "SELECT chunk_id,record_id,heading,page,passage,position,content_hash,embedding_model,embedding FROM sc_rl_chunks WHERE generation_id=%s ORDER BY record_id,position",
                (active,),
            ).fetchall()
        return [KnowledgeChunk(
            chunk_id=str(row["chunk_id"]), record_id=str(row["record_id"]), heading=str(row["heading"] or ""),
            page=int(row["page"]) if row["page"] is not None else None, passage=str(row["passage"] or ""),
            position=int(row["position"] or 0), content_hash=str(row["content_hash"] or ""),
            embedding_model=str(row["embedding_model"] or ""), embedding=self._embedding_list(row["embedding"]),
        ) for row in rows]

    def pending_chunks(self, limit: int, model: str) -> list[KnowledgeChunk]:
        with self._connection() as connection:
            active = self._active_generation(connection)
            if not active:
                return []
            rows = connection.execute(
                """
                SELECT chunk_id,record_id,heading,page,passage,position,content_hash,embedding_model,embedding
                FROM sc_rl_chunks WHERE generation_id=%s AND (embedding IS NULL OR embedding_model<>%s)
                ORDER BY record_id,position LIMIT %s
                """,
                (active, model, max(1, int(limit))),
            ).fetchall()
        return [KnowledgeChunk(
            chunk_id=str(row["chunk_id"]), record_id=str(row["record_id"]), heading=str(row["heading"] or ""),
            page=int(row["page"]) if row["page"] is not None else None, passage=str(row["passage"] or ""),
            position=int(row["position"] or 0), content_hash=str(row["content_hash"] or ""),
            embedding_model=str(row["embedding_model"] or ""), embedding=self._embedding_list(row["embedding"]),
        ) for row in rows]

    def save_chunk_embedding(self, chunk_id: str, model: str, embedding: list[float]) -> bool:
        with self._connection() as connection:
            active = self._active_generation(connection)
            if not active:
                return False
            vector = Vector(embedding) if Vector is not None else embedding
            result = connection.execute(
                "UPDATE sc_rl_chunks SET embedding=%s,embedding_model=%s,updated_utc=%s WHERE generation_id=%s AND chunk_id=%s",
                (vector, model, utc_now(), active, chunk_id),
            )
            connection.commit()
            return result.rowcount > 0

    def begin_embedding_run(self, model: str, requested: int) -> str:
        run_id = "embedding-" + uuid.uuid4().hex
        with self._connection() as connection:
            active = self._active_generation(connection)
            connection.execute(
                "INSERT INTO sc_rl_embedding_runs(run_id,generation_id,model,requested) VALUES(%s,%s,%s,%s)",
                (run_id, active or None, model, requested),
            )
            connection.commit()
        return run_id

    def finish_embedding_run(self, run_id: str, processed: int, failed: int, error: str = "") -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE sc_rl_embedding_runs SET processed=%s,failed=%s,error=%s,completed_utc=%s WHERE run_id=%s",
                (processed, failed, error[:2000], utc_now(), run_id),
            )
            connection.commit()

    def embedding_status(self) -> dict[str, Any]:
        with self._connection() as connection:
            active = self._active_generation(connection)
            if not active:
                return {"total_chunks": 0, "embedded_chunks": 0, "pending_chunks": 0, "coverage": 0.0, "embedding_model": settings.gemini_embedding_model, "last_run": {}}
            counts = connection.execute(
                "SELECT count(*) AS total,count(*) FILTER (WHERE embedding IS NOT NULL AND embedding_model=%s) AS embedded FROM sc_rl_chunks WHERE generation_id=%s",
                (settings.gemini_embedding_model, active),
            ).fetchone()
            run = connection.execute("SELECT * FROM sc_rl_embedding_runs WHERE generation_id=%s ORDER BY started_utc DESC LIMIT 1", (active,)).fetchone()
        total = int(counts["total"] or 0)
        embedded = int(counts["embedded"] or 0)
        return {
            "total_chunks": total,
            "indexed_chunks": total,
            "embedded_chunks": embedded,
            "pending_chunks": max(0, total - embedded),
            "coverage": round((embedded / total) * 100, 2) if total else 0.0,
            "semantic_coverage": round((embedded / total) * 100, 2) if total else 0.0,
            "embedding_model": settings.gemini_embedding_model,
            "last_run": dict(run) if run else {},
            "storage_engine": "postgres-neon",
        }

    def summary(self) -> dict[str, Any]:
        with self._connection() as connection:
            return self._summary_connection(connection)

    def manifest(self) -> dict[str, Any]:
        return {
            "schema": POSTGRES_INDEX_SCHEMA,
            "backend": "postgres",
            "provider": "neon-compatible",
            "summary": self.summary(),
            "database": self.database_diagnostics(),
            "snapshots": self.list_snapshots(),
        }

    def job_rejections(self, job_id: str) -> list[dict[str, Any]]:
        generation_id = self._generation_id(job_id)
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT batch_index,record_id,error,payload,created_utc FROM sc_rl_sync_rejections WHERE generation_id=%s ORDER BY rejection_id",
                (generation_id,),
            ).fetchall()
        return [{**dict(row), "created_utc": self._iso(row["created_utc"])} for row in rows]

    def list_snapshots(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT generation_id,job_id,source_site,active,activation_records,indexed_chunks,activation_checksum,completed_utc
                FROM sc_rl_generations WHERE state='committed' ORDER BY completed_utc DESC NULLS LAST LIMIT %s
                """,
                (settings.postgres_generation_retention,),
            ).fetchall()
        return [{
            "snapshot_id": str(row["generation_id"]),
            "generation_id": str(row["generation_id"]),
            "job_id": str(row["job_id"]),
            "source_site": str(row["source_site"] or ""),
            "active": bool(row["active"]),
            "record_count": int(row["activation_records"] or 0),
            "indexed_chunks": int(row["indexed_chunks"] or 0),
            "checksum": str(row["activation_checksum"] or ""),
            "created_utc": self._iso(row["completed_utc"]),
            "storage_engine": "postgres-neon",
        } for row in rows]

    def validate_snapshots(self) -> dict[str, Any]:
        snapshots = self.list_snapshots()
        return {"ok": True, "valid": len(snapshots), "invalid": 0, "snapshots": snapshots}

    def rollback(self, snapshot_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT generation_id FROM sc_rl_generations WHERE generation_id=%s AND state='committed'",
                (snapshot_id,),
            ).fetchone()
            if not row:
                raise KeyError(snapshot_id)
            connection.execute("UPDATE sc_rl_generations SET active=FALSE WHERE active=TRUE")
            connection.execute("UPDATE sc_rl_generations SET active=TRUE,updated_utc=%s WHERE generation_id=%s", (utc_now(), snapshot_id))
            connection.execute(
                "INSERT INTO sc_rl_meta(key,value,updated_utc) VALUES('active_generation_id',to_jsonb(%s::text),%s) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_utc=excluded.updated_utc",
                (snapshot_id, utc_now()),
            )
            connection.commit()
        return {"ok": True, "snapshot_id": snapshot_id, "active_generation_id": snapshot_id, "summary": self.summary()}
