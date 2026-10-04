from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Iterator
import uuid

from ..config import settings
from ..database_identity import validate_schema_name
from ..store import store as knowledge_store
from ..contracts.persistent_research_session_conversation import (
    PERSISTENT_RESEARCH_SESSION_SCHEMA,
    PERSISTENT_RESEARCH_TURN_SCHEMA,
    PERSISTENT_RESEARCH_SESSION_SNAPSHOT_SCHEMA,
    ResearchSessionCreateRequest,
    ResearchSessionTurnAddRequest,
    ResearchSessionContextBindRequest,
    ResearchSessionStateRequest,
    ResearchSessionSnapshotRequest,
)

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None
    dict_row=None
    Jsonb=None


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersistentResearchSessionStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "persistent_research_sessions.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres persistent research session storage requires psycopg.")
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
    def _postgres(self, migration: bool = False) -> Iterator[Any]:
        url = (settings.direct_database_url if migration else settings.database_url) or settings.database_url
        connection = psycopg.connect(url, autocommit=False, row_factory=dict_row)
        connection.execute(f'SET search_path TO "{self.database_schema}"')
        try:
            yield connection
        finally:
            connection.close()

    def _migrate_sqlite(self) -> None:
        with self._lock, self._sqlite() as c:
            c.executescript(
                """
CREATE TABLE IF NOT EXISTS persistent_research_sessions(
 session_id TEXT PRIMARY KEY,
 state TEXT NOT NULL,
 client_ref TEXT NOT NULL DEFAULT '',
 project_id TEXT NOT NULL DEFAULT '',
 scientist_environment_id TEXT NOT NULL DEFAULT '',
 research_context_ref TEXT NOT NULL DEFAULT '',
 record_json TEXT NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL,
 updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_persistent_research_sessions_client
 ON persistent_research_sessions(client_ref,updated_utc);
CREATE INDEX IF NOT EXISTS idx_persistent_research_sessions_project
 ON persistent_research_sessions(project_id,updated_utc);

CREATE TABLE IF NOT EXISTS persistent_research_turns(
 turn_id TEXT PRIMARY KEY,
 session_id TEXT NOT NULL,
 sequence INTEGER NOT NULL,
 role TEXT NOT NULL,
 record_json TEXT NOT NULL,
 record_hash TEXT NOT NULL,
 previous_turn_hash TEXT NOT NULL DEFAULT '',
 created_utc TEXT NOT NULL,
 UNIQUE(session_id,sequence)
);
CREATE INDEX IF NOT EXISTS idx_persistent_research_turns_session
 ON persistent_research_turns(session_id,sequence);

CREATE TABLE IF NOT EXISTS persistent_research_session_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 session_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record_json TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_persistent_research_session_snapshots_session
 ON persistent_research_session_snapshots(session_id,created_utc);
"""
            )

    def _migrate_postgres(self) -> None:
        ddl = [
            """CREATE TABLE IF NOT EXISTS sc_rl_persistent_research_sessions(
 session_id TEXT PRIMARY KEY,state TEXT NOT NULL,client_ref TEXT NOT NULL DEFAULT '',
 project_id TEXT NOT NULL DEFAULT '',scientist_environment_id TEXT NOT NULL DEFAULT '',
 research_context_ref TEXT NOT NULL DEFAULT '',record JSONB NOT NULL,record_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())""",
            "CREATE INDEX IF NOT EXISTS idx_sc_rl_persistent_research_sessions_client ON sc_rl_persistent_research_sessions(client_ref,updated_utc DESC)",
            "CREATE INDEX IF NOT EXISTS idx_sc_rl_persistent_research_sessions_project ON sc_rl_persistent_research_sessions(project_id,updated_utc DESC)",
            """CREATE TABLE IF NOT EXISTS sc_rl_persistent_research_turns(
 turn_id TEXT PRIMARY KEY,session_id TEXT NOT NULL,sequence INTEGER NOT NULL,role TEXT NOT NULL,
 record JSONB NOT NULL,record_hash TEXT NOT NULL,previous_turn_hash TEXT NOT NULL DEFAULT '',
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(session_id,sequence))""",
            "CREATE INDEX IF NOT EXISTS idx_sc_rl_persistent_research_turns_session ON sc_rl_persistent_research_turns(session_id,sequence)",
            """CREATE TABLE IF NOT EXISTS sc_rl_persistent_research_session_snapshots(
 snapshot_id TEXT PRIMARY KEY,session_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,
 record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""",
            "CREATE INDEX IF NOT EXISTS idx_sc_rl_persistent_research_session_snapshots_session ON sc_rl_persistent_research_session_snapshots(session_id,created_utc DESC)",
        ]
        with self._postgres(True) as c:
            for statement in ddl:
                c.execute(statement)
            c.commit()

    def _validate_context(self, project_id: str, scientist_environment_id: str) -> None:
        if project_id and not knowledge_store.research_project(project_id):
            raise ValueError("Research project not found.")
        if scientist_environment_id:
            from .integrated_computational_research_scientist_environment import (
                get_integrated_computational_research_scientist_environment_store,
            )
            try:
                get_integrated_computational_research_scientist_environment_store().get(scientist_environment_id)
            except ValueError as exc:
                raise ValueError("Scientist environment not found.") from exc

    def _save_session(self, record: dict[str, Any]) -> dict[str, Any]:
        record["updated_utc"] = _now()
        record["record_hash"] = _sha({k: v for k, v in record.items() if k != "record_hash"})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute(
                    """INSERT INTO sc_rl_persistent_research_sessions(
 session_id,state,client_ref,project_id,scientist_environment_id,research_context_ref,
 record,record_hash,created_utc,updated_utc)
 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
 ON CONFLICT(session_id) DO UPDATE SET
 state=EXCLUDED.state,client_ref=EXCLUDED.client_ref,project_id=EXCLUDED.project_id,
 scientist_environment_id=EXCLUDED.scientist_environment_id,research_context_ref=EXCLUDED.research_context_ref,
 record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc""",
                    (
                        record["session_id"], record["state"], record["client_ref"], record["project_id"],
                        record["scientist_environment_id"], record["research_context_ref"], Jsonb(record),
                        record["record_hash"], record["created_utc"], record["updated_utc"],
                    ),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute(
                    """INSERT OR REPLACE INTO persistent_research_sessions(
 session_id,state,client_ref,project_id,scientist_environment_id,research_context_ref,
 record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        record["session_id"], record["state"], record["client_ref"], record["project_id"],
                        record["scientist_environment_id"], record["research_context_ref"], _json(record),
                        record["record_hash"], record["created_utc"], record["updated_utc"],
                    ),
                )
        return record

    def create(self, req: ResearchSessionCreateRequest, *, requested_session_id: str = "") -> dict[str, Any]:
        self._validate_context(req.project_id, req.scientist_environment_id)
        session_id = requested_session_id.strip()[:180] or ("session-" + uuid.uuid4().hex)
        if requested_session_id:
            try:
                return self.get(session_id)
            except ValueError:
                pass
        now = _now()
        record = {
            "schema": PERSISTENT_RESEARCH_SESSION_SCHEMA,
            "session_id": session_id,
            "title": req.title or "Research session",
            "client_ref": req.client_ref,
            "project_id": req.project_id,
            "scientist_environment_id": req.scientist_environment_id,
            "research_context_ref": req.research_context_ref,
            "metadata": req.metadata,
            "state": "active",
            "turn_count": 0,
            "last_turn_utc": "",
            "context_bindings": [],
            "created_utc": now,
            "updated_utc": now,
            "governance": {
                "persistent_backend_state": True,
                "wordpress_required": False,
                "client_ref_is_identity": False,
                "client_ref_grants_authorization": False,
                "identity_and_access_deferred_to_v12_0_5": True,
                "conversation_content_is_not_evidence_by_default": True,
                "automatic_truth_promotion": False,
            },
        }
        return self._save_session(record)

    def ensure(self, session_id: str, *, title: str = "Research session", client_ref: str = "") -> dict[str, Any]:
        try:
            return self.get(session_id)
        except ValueError:
            return self.create(
                ResearchSessionCreateRequest(title=title, client_ref=client_ref),
                requested_session_id=session_id,
            )

    def get(self, session_id: str) -> dict[str, Any]:
        if self.backend == "postgres":
            with self._postgres() as c:
                row = c.execute(
                    "SELECT record FROM sc_rl_persistent_research_sessions WHERE session_id=%s",
                    (session_id,),
                ).fetchone()
            if not row:
                raise ValueError("Research session not found.")
            return dict(row["record"])
        with self._lock, self._sqlite() as c:
            row = c.execute(
                "SELECT record_json FROM persistent_research_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
        if not row:
            raise ValueError("Research session not found.")
        return json.loads(str(row["record_json"]))

    def list_sessions(
        self,
        *,
        limit: int = 100,
        client_ref: str = "",
        project_id: str = "",
        state: str = "",
    ) -> list[dict[str, Any]]:
        limit = max(1, min(500, int(limit)))
        if self.backend == "postgres":
            clauses = []
            args: list[Any] = []
            for column, value in (("client_ref", client_ref), ("project_id", project_id), ("state", state)):
                if value:
                    clauses.append(f"{column}=%s")
                    args.append(value)
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            args.append(limit)
            with self._postgres() as c:
                rows = c.execute(
                    f"SELECT record FROM sc_rl_persistent_research_sessions{where} ORDER BY updated_utc DESC LIMIT %s",
                    tuple(args),
                ).fetchall()
            return [dict(row["record"]) for row in rows]

        clauses = []
        args: list[Any] = []
        for column, value in (("client_ref", client_ref), ("project_id", project_id), ("state", state)):
            if value:
                clauses.append(f"{column}=?")
                args.append(value)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        args.append(limit)
        with self._lock, self._sqlite() as c:
            rows = c.execute(
                f"SELECT record_json FROM persistent_research_sessions{where} ORDER BY updated_utc DESC LIMIT ?",
                tuple(args),
            ).fetchall()
        return [json.loads(str(row["record_json"])) for row in rows]

    def _last_turn(self, session_id: str) -> tuple[int, str]:
        if self.backend == "postgres":
            with self._postgres() as c:
                row = c.execute(
                    "SELECT sequence,record_hash FROM sc_rl_persistent_research_turns WHERE session_id=%s ORDER BY sequence DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
        else:
            with self._lock, self._sqlite() as c:
                row = c.execute(
                    "SELECT sequence,record_hash FROM persistent_research_turns WHERE session_id=? ORDER BY sequence DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
        if not row:
            return 0, ""
        return int(row["sequence"]), str(row["record_hash"])

    def add_turn(self, session_id: str, req: ResearchSessionTurnAddRequest, *, requested_turn_id: str = "") -> dict[str, Any]:
        requested_turn_id = requested_turn_id.strip()[:180]
        if requested_turn_id:
            if self.backend == "postgres":
                with self._postgres() as c:
                    existing = c.execute(
                        "SELECT record FROM sc_rl_persistent_research_turns WHERE turn_id=%s AND session_id=%s",
                        (requested_turn_id, session_id),
                    ).fetchone()
                if existing:
                    return dict(existing["record"])
            else:
                with self._lock, self._sqlite() as c:
                    existing = c.execute(
                        "SELECT record_json FROM persistent_research_turns WHERE turn_id=? AND session_id=?",
                        (requested_turn_id, session_id),
                    ).fetchone()
                if existing:
                    return json.loads(str(existing["record_json"]))
        session = self.get(session_id)
        if session["state"] in {"closed", "archived"}:
            raise ValueError("Research session is closed or archived.")
        previous_sequence, previous_hash = self._last_turn(session_id)
        sequence = previous_sequence + 1
        created = _now()
        record = {
            "schema": PERSISTENT_RESEARCH_TURN_SCHEMA,
            "turn_id": requested_turn_id or ("turn-" + uuid.uuid4().hex),
            "session_id": session_id,
            "sequence": sequence,
            "role": req.role,
            "content": req.content,
            "source_refs": req.source_refs,
            "evidence_refs": req.evidence_refs,
            "artifact_refs": req.artifact_refs,
            "answer_trace_ref": req.answer_trace_ref,
            "provider": req.provider,
            "model": req.model,
            "provenance": req.provenance,
            "metadata": req.metadata,
            "previous_turn_hash": previous_hash,
            "created_utc": created,
            "governance": {
                "conversation_turn_is_not_evidence_by_default": True,
                "assistant_turn_is_not_truth_certification": req.role == "assistant",
            },
        }
        record_hash = _sha(record)
        record["record_hash"] = record_hash

        if self.backend == "postgres":
            with self._postgres() as c:
                # Serialize sequence assignment on the session row for multi-worker safety.
                c.execute(
                    "SELECT session_id FROM sc_rl_persistent_research_sessions WHERE session_id=%s FOR UPDATE",
                    (session_id,),
                )
                row = c.execute(
                    "SELECT sequence,record_hash FROM sc_rl_persistent_research_turns WHERE session_id=%s ORDER BY sequence DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
                if row:
                    sequence = int(row["sequence"]) + 1
                    previous_hash = str(row["record_hash"])
                    record["sequence"] = sequence
                    record["previous_turn_hash"] = previous_hash
                    record["record_hash"] = _sha({k: v for k, v in record.items() if k != "record_hash"})
                c.execute(
                    """INSERT INTO sc_rl_persistent_research_turns(
 turn_id,session_id,sequence,role,record,record_hash,previous_turn_hash,created_utc)
 VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        record["turn_id"], session_id, record["sequence"], record["role"], Jsonb(record),
                        record["record_hash"], record["previous_turn_hash"], created,
                    ),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                # Re-read under the process lock before inserting.
                row = c.execute(
                    "SELECT sequence,record_hash FROM persistent_research_turns WHERE session_id=? ORDER BY sequence DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
                if row:
                    record["sequence"] = int(row["sequence"]) + 1
                    record["previous_turn_hash"] = str(row["record_hash"])
                    record["record_hash"] = _sha({k: v for k, v in record.items() if k != "record_hash"})
                c.execute(
                    """INSERT INTO persistent_research_turns(
 turn_id,session_id,sequence,role,record_json,record_hash,previous_turn_hash,created_utc)
 VALUES(?,?,?,?,?,?,?,?)""",
                    (
                        record["turn_id"], session_id, record["sequence"], record["role"], _json(record),
                        record["record_hash"], record["previous_turn_hash"], created,
                    ),
                )

        session = self.get(session_id)
        session["turn_count"] = int(record["sequence"])
        session["last_turn_utc"] = created
        self._save_session(session)
        return record

    def turns(self, session_id: str, *, limit: int = 500, after_sequence: int = 0) -> list[dict[str, Any]]:
        self.get(session_id)
        limit = max(1, min(5000, int(limit)))
        after_sequence = max(0, int(after_sequence))
        if self.backend == "postgres":
            with self._postgres() as c:
                rows = c.execute(
                    "SELECT record FROM sc_rl_persistent_research_turns WHERE session_id=%s AND sequence>%s ORDER BY sequence ASC LIMIT %s",
                    (session_id, after_sequence, limit),
                ).fetchall()
            return [dict(row["record"]) for row in rows]
        with self._lock, self._sqlite() as c:
            rows = c.execute(
                "SELECT record_json FROM persistent_research_turns WHERE session_id=? AND sequence>? ORDER BY sequence ASC LIMIT ?",
                (session_id, after_sequence, limit),
            ).fetchall()
        return [json.loads(str(row["record_json"])) for row in rows]

    def history_for_generation(self, session_id: str, max_turns: int) -> list[dict[str, str]]:
        self.ensure(session_id, title="Legacy /v1/ask session", client_ref="legacy-backend-api")
        turns = self.turns(session_id, limit=5000)
        filtered = [turn for turn in turns if turn.get("role") in {"user", "assistant"}]
        return [
            {"role": str(turn["role"]), "content": str(turn["content"])}
            for turn in filtered[-max(2, max_turns * 2):]
        ]

    def user_turn_count(self, session_id: str) -> int:
        self.get(session_id)
        if self.backend == "postgres":
            with self._postgres() as c:
                row = c.execute(
                    "SELECT COUNT(*) AS n FROM sc_rl_persistent_research_turns WHERE session_id=%s AND role='user'",
                    (session_id,),
                ).fetchone()
        else:
            with self._lock, self._sqlite() as c:
                row = c.execute(
                    "SELECT COUNT(*) AS n FROM persistent_research_turns WHERE session_id=? AND role='user'",
                    (session_id,),
                ).fetchone()
        return int(row["n"] if row else 0)

    def clear_turns(self, session_id: str) -> int:
        try:
            session = self.get(session_id)
        except ValueError:
            return 0
        if self.backend == "postgres":
            with self._postgres() as c:
                row = c.execute(
                    "SELECT COUNT(*) AS n FROM sc_rl_persistent_research_turns WHERE session_id=%s",
                    (session_id,),
                ).fetchone()
                count = int(row["n"] if row else 0)
                c.execute("DELETE FROM sc_rl_persistent_research_turns WHERE session_id=%s", (session_id,))
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                row = c.execute(
                    "SELECT COUNT(*) AS n FROM persistent_research_turns WHERE session_id=?",
                    (session_id,),
                ).fetchone()
                count = int(row["n"] if row else 0)
                c.execute("DELETE FROM persistent_research_turns WHERE session_id=?", (session_id,))
        session["turn_count"] = 0
        session["last_turn_utc"] = ""
        session.setdefault("reset_events", []).append({"reset_utc": _now(), "removed_turns": count})
        self._save_session(session)
        return count

    def bind_context(self, session_id: str, req: ResearchSessionContextBindRequest) -> dict[str, Any]:
        session = self.get(session_id)
        self._validate_context(req.project_id, req.scientist_environment_id)
        previous = {
            "project_id": session.get("project_id", ""),
            "scientist_environment_id": session.get("scientist_environment_id", ""),
            "research_context_ref": session.get("research_context_ref", ""),
        }
        session["project_id"] = req.project_id
        session["scientist_environment_id"] = req.scientist_environment_id
        session["research_context_ref"] = req.research_context_ref
        session.setdefault("context_bindings", []).append(
            {
                "bound_utc": _now(),
                "previous": previous,
                "current": {
                    "project_id": req.project_id,
                    "scientist_environment_id": req.scientist_environment_id,
                    "research_context_ref": req.research_context_ref,
                },
                "note": req.note,
            }
        )
        return self._save_session(session)

    def set_state(self, session_id: str, req: ResearchSessionStateRequest) -> dict[str, Any]:
        session = self.get(session_id)
        session["state"] = req.state
        session.setdefault("state_history", []).append(
            {"state": req.state, "note": req.note, "changed_utc": _now()}
        )
        return self._save_session(session)

    def summary(self, session_id: str) -> dict[str, Any]:
        session = self.get(session_id)
        turns = self.turns(session_id, limit=5000)
        roles: dict[str, int] = {}
        for turn in turns:
            roles[str(turn.get("role", ""))] = roles.get(str(turn.get("role", "")), 0) + 1
        return {
            "schema": PERSISTENT_RESEARCH_SESSION_SCHEMA,
            "session_id": session_id,
            "state": session["state"],
            "turn_count": len(turns),
            "role_counts": roles,
            "project_id": session.get("project_id", ""),
            "scientist_environment_id": session.get("scientist_environment_id", ""),
            "research_context_ref": session.get("research_context_ref", ""),
            "last_turn_utc": session.get("last_turn_utc", ""),
            "client_ref": session.get("client_ref", ""),
            "governance": {
                "client_ref_is_identity": False,
                "summary_does_not_grant_access": True,
                "conversation_content_is_not_evidence_by_default": True,
            },
        }

    def freeze_snapshot(self, session_id: str, req: ResearchSessionSnapshotRequest) -> dict[str, Any]:
        session = self.get(session_id)
        turns = self.turns(session_id, limit=5000)
        payload = {
            "schema": PERSISTENT_RESEARCH_SESSION_SNAPSHOT_SCHEMA,
            "session_id": session_id,
            "session": session,
            "turns": turns,
            "summary": self.summary(session_id),
            "label": req.label,
            "note": req.note,
            "actor_ref": req.actor_ref,
            "frozen_utc": _now(),
            "governance": {
                "snapshot_preserves_conversation_lineage": True,
                "snapshot_is_not_identity_or_authorization_record": True,
                "snapshot_is_not_truth_certification": True,
                "wordpress_required": False,
            },
        }
        h = _sha(payload)
        snapshot_id = "sessionsnap-" + h[:32]
        payload.update({"snapshot_id": snapshot_id, "snapshot_hash": h})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute(
                    """INSERT INTO sc_rl_persistent_research_session_snapshots(
 snapshot_id,session_id,snapshot_hash,record) VALUES(%s,%s,%s,%s)
 ON CONFLICT(snapshot_id) DO NOTHING""",
                    (snapshot_id, session_id, h, Jsonb(payload)),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute(
                    """INSERT OR IGNORE INTO persistent_research_session_snapshots(
 snapshot_id,session_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)""",
                    (snapshot_id, session_id, h, _json(payload), payload["frozen_utc"]),
                )
        return payload


def capabilities() -> dict[str, Any]:
    return {
        "schema": PERSISTENT_RESEARCH_SESSION_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.0.3",
        "durable": True,
        "postgres_production": True,
        "sqlite_local_test": True,
        "persistent_sessions": True,
        "persistent_conversations": True,
        "turn_hash_chain": True,
        "project_context_binding": True,
        "scientist_environment_binding": True,
        "research_context_binding": True,
        "conversation_snapshots": True,
        "legacy_ask_persistence": True,
        "wordpress_required": False,
        "client_ref_is_identity": False,
        "identity_sessions": False,
        "identity_access_deferred_to_v12_0_5": True,
        "automatic_truth_promotion": False,
    }


_store = None


def get_persistent_research_session_store() -> PersistentResearchSessionStore:
    global _store
    if _store is None:
        _store = PersistentResearchSessionStore()
    return _store
