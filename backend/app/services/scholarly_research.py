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
from ..contracts.scholarly_research import (
    SCHOLARLY_RESEARCH_SCHEMA,
    SCHOLARLY_REVISION_SCHEMA,
    SCHOLARLY_PACKAGE_SCHEMA,
    PUBLICATION_READINESS_SCHEMA,
    ScholarlyStudyCreateRequest,
    ScholarlyProtocolFreezeRequest,
    ScholarlyDeviationRequest,
    ScholarlyResultRequest,
    ScholarlyInterpretationRequest,
    ScholarlyManuscriptSectionRequest,
    ScholarlyReviewRequest,
    ScholarlyPackageFreezeRequest,
)
from .research_workflow import get_research_workflow_store

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


class ScholarlyResearchStore:
    """Durable scholarly-study registry with immutable revisions and frozen packages."""

    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "scholarly_research.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres scholarly research storage requires psycopg.")
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
CREATE TABLE IF NOT EXISTS scholarly_studies(
  study_id TEXT PRIMARY KEY,
  core_project_id TEXT NOT NULL,
  local_project_id TEXT NOT NULL DEFAULT '',
  workflow_id TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL,
  record_json TEXT NOT NULL,
  study_fingerprint TEXT NOT NULL,
  created_utc TEXT NOT NULL,
  updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scholarly_studies_project ON scholarly_studies(core_project_id,updated_utc);
CREATE INDEX IF NOT EXISTS idx_scholarly_studies_state ON scholarly_studies(state,updated_utc);
CREATE TABLE IF NOT EXISTS scholarly_study_revisions(
  revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
  study_id TEXT NOT NULL,
  revision_number INTEGER NOT NULL,
  revision_hash TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  actor_ref TEXT NOT NULL DEFAULT '',
  record_json TEXT NOT NULL,
  created_utc TEXT NOT NULL,
  UNIQUE(study_id,revision_number)
);
CREATE TABLE IF NOT EXISTS scholarly_packages(
  package_id TEXT PRIMARY KEY,
  study_id TEXT NOT NULL,
  package_hash TEXT NOT NULL,
  record_json TEXT NOT NULL,
  created_utc TEXT NOT NULL
);
"""
            )

    def _migrate_postgres(self) -> None:
        with self._postgres(True) as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS sc_rl_scholarly_studies(
                study_id TEXT PRIMARY KEY,core_project_id TEXT NOT NULL,local_project_id TEXT NOT NULL DEFAULT '',workflow_id TEXT NOT NULL DEFAULT '',state TEXT NOT NULL,record JSONB NOT NULL,study_fingerprint TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now());"""
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_scholarly_studies_project ON sc_rl_scholarly_studies(core_project_id,updated_utc)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_scholarly_studies_state ON sc_rl_scholarly_studies(state,updated_utc)")
            c.execute(
                """CREATE TABLE IF NOT EXISTS sc_rl_scholarly_study_revisions(
                revision_id BIGSERIAL PRIMARY KEY,study_id TEXT NOT NULL REFERENCES sc_rl_scholarly_studies(study_id) ON DELETE CASCADE,revision_number INTEGER NOT NULL,revision_hash TEXT NOT NULL,reason TEXT NOT NULL DEFAULT '',actor_ref TEXT NOT NULL DEFAULT '',record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(study_id,revision_number));"""
            )
            c.execute(
                """CREATE TABLE IF NOT EXISTS sc_rl_scholarly_packages(
                package_id TEXT PRIMARY KEY,study_id TEXT NOT NULL REFERENCES sc_rl_scholarly_studies(study_id) ON DELETE CASCADE,package_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now());"""
            )
            c.commit()

    def _find_by_idempotency(self, key: str) -> dict[str, Any] | None:
        if not key:
            return None
        for item in self.list(limit=500):
            if str(item.get("idempotency_key") or "") == key:
                return item
        return None

    def _revision_count(self, study_id: str) -> int:
        if self.backend == "postgres":
            with self._postgres() as c:
                row = c.execute("SELECT COALESCE(MAX(revision_number),0) AS n FROM sc_rl_scholarly_study_revisions WHERE study_id=%s", (study_id,)).fetchone()
                c.commit()
            return int(row["n"] if row else 0)
        with self._lock, self._sqlite() as c:
            row = c.execute("SELECT COALESCE(MAX(revision_number),0) AS n FROM scholarly_study_revisions WHERE study_id=?", (study_id,)).fetchone()
        return int(row["n"] if row else 0)

    def _write_revision(self, study: dict[str, Any], reason: str, actor_ref: str = "") -> dict[str, Any]:
        number = self._revision_count(study["study_id"]) + 1
        snapshot = json.loads(_json(study))
        revision_hash = _sha({"study": snapshot, "revision_number": number, "reason": reason})
        now = _now()
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute(
                    "INSERT INTO sc_rl_scholarly_study_revisions(study_id,revision_number,revision_hash,reason,actor_ref,record,created_utc) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (study["study_id"], number, revision_hash, reason, actor_ref, Jsonb(snapshot), now),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute(
                    "INSERT INTO scholarly_study_revisions(study_id,revision_number,revision_hash,reason,actor_ref,record_json,created_utc) VALUES(?,?,?,?,?,?,?)",
                    (study["study_id"], number, revision_hash, reason, actor_ref, _json(snapshot), now),
                )
        return {"schema": SCHOLARLY_REVISION_SCHEMA, "revision_number": number, "revision_hash": revision_hash, "reason": reason, "actor_ref": actor_ref, "created_utc": now}

    def _save(self, study: dict[str, Any], reason: str, actor_ref: str = "") -> dict[str, Any]:
        item = dict(study)
        item["updated_utc"] = _now()
        item["study_fingerprint"] = _sha({k: v for k, v in item.items() if k not in {"study_fingerprint", "updated_utc"}})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute(
                    "UPDATE sc_rl_scholarly_studies SET state=%s,record=%s,study_fingerprint=%s,updated_utc=%s WHERE study_id=%s",
                    (item["state"], Jsonb(item), item["study_fingerprint"], item["updated_utc"], item["study_id"]),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute(
                    "UPDATE scholarly_studies SET state=?,record_json=?,study_fingerprint=?,updated_utc=? WHERE study_id=?",
                    (item["state"], _json(item), item["study_fingerprint"], item["updated_utc"], item["study_id"]),
                )
        self._write_revision(item, reason, actor_ref)
        return item

    def create(self, request: ScholarlyStudyCreateRequest) -> tuple[dict[str, Any], bool]:
        key = str(request.idempotency_key or "").strip()
        existing = self._find_by_idempotency(key) if key else None
        if existing:
            return existing, True
        if request.workflow_id:
            workflow = get_research_workflow_store().get(request.workflow_id)
            if workflow["core_project_id"] != request.core_project_id:
                raise ValueError("workflow_id must belong to the same core_project_id as the scholarly study")
        now = _now()
        study_id = _uid("rl-study")
        item = {
            "schema": SCHOLARLY_RESEARCH_SCHEMA,
            "release": settings.release_version,
            "study_id": study_id,
            "state": "draft",
            "core_project_id": request.core_project_id,
            "local_project_id": request.local_project_id or "",
            "workflow_id": request.workflow_id or "",
            "title": request.title,
            "research_question": request.research_question,
            "study_type": request.study_type,
            "protocol": request.protocol.model_dump(mode="json"),
            "protocol_frozen": False,
            "protocol_frozen_utc": "",
            "protocol_reviewer_ref": "",
            "protocol_hash": "",
            "deviations": [],
            "results": [],
            "interpretations": [],
            "manuscript_sections": [],
            "reviews": [],
            "authors": request.authors,
            "affiliations": request.affiliations,
            "funding_statement": request.funding_statement,
            "conflict_of_interest_statement": request.conflict_of_interest_statement,
            "source_refs": sorted(set(request.source_refs)),
            "core_evidence_refs": sorted(set(request.core_evidence_refs)),
            "core_research_object_refs": sorted(set(request.core_research_object_refs)),
            "statistical_reasoning_refs": sorted(set(request.statistical_reasoning_refs)),
            "visual_refs": sorted(set(request.visual_refs)),
            "metadata": request.metadata,
            "idempotency_key": key,
            "created_utc": now,
            "updated_utc": now,
            "study_fingerprint": "",
        }
        item["study_fingerprint"] = _sha(item)
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute(
                    "INSERT INTO sc_rl_scholarly_studies(study_id,core_project_id,local_project_id,workflow_id,state,record,study_fingerprint,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (study_id, request.core_project_id, request.local_project_id or "", request.workflow_id or "", item["state"], Jsonb(item), item["study_fingerprint"], now, now),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute(
                    "INSERT INTO scholarly_studies(study_id,core_project_id,local_project_id,workflow_id,state,record_json,study_fingerprint,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?,?)",
                    (study_id, request.core_project_id, request.local_project_id or "", request.workflow_id or "", item["state"], _json(item), item["study_fingerprint"], now, now),
                )
        self._write_revision(item, "study-created", "")
        return item, False

    def get(self, study_id: str) -> dict[str, Any]:
        if self.backend == "postgres":
            with self._postgres() as c:
                row = c.execute("SELECT record FROM sc_rl_scholarly_studies WHERE study_id=%s", (study_id,)).fetchone()
                c.commit()
            if not row:
                raise KeyError(study_id)
            return dict(row["record"])
        with self._lock, self._sqlite() as c:
            row = c.execute("SELECT record_json FROM scholarly_studies WHERE study_id=?", (study_id,)).fetchone()
        if not row:
            raise KeyError(study_id)
        return json.loads(row["record_json"])

    def list(self, state: str = "", core_project_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(500, int(limit)))
        items: list[dict[str, Any]] = []
        if self.backend == "postgres":
            q = "SELECT record FROM sc_rl_scholarly_studies WHERE 1=1"
            args: list[Any] = []
            if state:
                q += " AND state=%s"; args.append(state)
            if core_project_id:
                q += " AND core_project_id=%s"; args.append(core_project_id)
            q += " ORDER BY updated_utc DESC LIMIT %s"; args.append(limit)
            with self._postgres() as c:
                rows = c.execute(q, tuple(args)).fetchall(); c.commit()
            items = [dict(row["record"]) for row in rows]
        else:
            q = "SELECT record_json FROM scholarly_studies WHERE 1=1"
            args2: list[Any] = []
            if state:
                q += " AND state=?"; args2.append(state)
            if core_project_id:
                q += " AND core_project_id=?"; args2.append(core_project_id)
            q += " ORDER BY updated_utc DESC LIMIT ?"; args2.append(limit)
            with self._lock, self._sqlite() as c:
                rows = c.execute(q, tuple(args2)).fetchall()
            items = [json.loads(row["record_json"]) for row in rows]
        return items

    def freeze_protocol(self, study_id: str, request: ScholarlyProtocolFreezeRequest) -> dict[str, Any]:
        study = self.get(study_id)
        if study["protocol_frozen"]:
            return study
        if not study["protocol"].get("methods") and not study["protocol"].get("analysis_plan"):
            raise ValueError("Protocol must declare methods or an analysis plan before it can be frozen.")
        study["protocol_frozen"] = True
        study["protocol_frozen_utc"] = _now()
        study["protocol_reviewer_ref"] = request.reviewer_ref
        study["protocol_hash"] = _sha(study["protocol"])
        study["state"] = "protocol-frozen"
        study["reviews"].append({"scope": "protocol", "decision": "approved", "reviewer_ref": request.reviewer_ref, "note": request.note, "reviewed_utc": _now()})
        return self._save(study, "protocol-frozen", request.reviewer_ref)

    def add_deviation(self, study_id: str, request: ScholarlyDeviationRequest) -> dict[str, Any]:
        study = self.get(study_id)
        if not study["protocol_frozen"]:
            raise ValueError("Protocol deviations are only recorded after the protocol is frozen.")
        deviation = {"deviation_id": _uid("dev"), **request.model_dump(mode="json"), "created_utc": _now()}
        study["deviations"].append(deviation)
        return self._save(study, "protocol-deviation-recorded", request.actor_ref)

    def add_result(self, study_id: str, request: ScholarlyResultRequest) -> dict[str, Any]:
        study = self.get(study_id)
        if not study["protocol_frozen"]:
            raise ValueError("Results cannot be registered before the study protocol is frozen.")
        result = {"result_id": _uid("result"), **request.model_dump(mode="json"), "created_utc": _now()}
        result["result_hash"] = _sha(result)
        study["results"].append(result)
        study["state"] = "results-review"
        return self._save(study, "result-registered", request.actor_ref)

    def add_interpretation(self, study_id: str, request: ScholarlyInterpretationRequest) -> dict[str, Any]:
        study = self.get(study_id)
        known = {item["result_id"] for item in study["results"]}
        unknown = [ref for ref in request.result_refs if ref not in known]
        if unknown:
            raise ValueError(f"Unknown result_refs: {unknown}")
        item = {"interpretation_id": _uid("interpretation"), **request.model_dump(mode="json"), "created_utc": _now()}
        item["interpretation_hash"] = _sha(item)
        study["interpretations"].append(item)
        return self._save(study, "human-interpretation-added", request.author_ref)

    def add_manuscript_section(self, study_id: str, request: ScholarlyManuscriptSectionRequest) -> dict[str, Any]:
        study = self.get(study_id)
        entry = {"section_id": _uid("section"), **request.model_dump(mode="json"), "created_utc": _now()}
        entry["section_hash"] = _sha(entry)
        study["manuscript_sections"].append(entry)
        study["state"] = "manuscript-draft"
        return self._save(study, f"manuscript-section:{request.section}", request.author_ref)

    def review(self, study_id: str, request: ScholarlyReviewRequest) -> dict[str, Any]:
        study = self.get(study_id)
        study["reviews"].append({**request.model_dump(mode="json"), "reviewed_utc": _now()})
        return self._save(study, f"review:{request.scope}:{request.decision}", request.reviewer_ref)

    def readiness(self, study_id: str) -> dict[str, Any]:
        study = self.get(study_id)
        sections = {x["section"] for x in study["manuscript_sections"]}
        required_sections = {"methods", "results", "discussion", "limitations"}
        checks = {
            "protocol_frozen": bool(study["protocol_frozen"]),
            "research_question_present": bool(study["research_question"].strip()),
            "authors_declared": bool(study["authors"]),
            "funding_statement_declared": bool(study["funding_statement"].strip()),
            "conflict_statement_declared": bool(study["conflict_of_interest_statement"].strip()),
            "results_registered": bool(study["results"]),
            "human_interpretation_present": bool(study["interpretations"]),
            "required_manuscript_sections_present": required_sections.issubset(sections),
            "evidence_or_source_lineage_present": bool(study["source_refs"] or study["core_evidence_refs"]),
            "statistical_or_visual_lineage_declared_if_used": all(
                bool(item.get("statistical_reasoning_ref") or item.get("runtime_ref") or item.get("artifact_ref"))
                for item in study["results"] if item.get("result_type") in {"statistical", "model", "simulation"}
            ),
            "protocol_deviations_explicit": True,
        }
        blockers = [name for name, ok in checks.items() if not ok]
        return {
            "schema": PUBLICATION_READINESS_SCHEMA,
            "release": settings.release_version,
            "study_id": study_id,
            "ready": not blockers,
            "checks": checks,
            "blockers": blockers,
            "governance": {
                "machine_generated_authorship": False,
                "automatic_truth_promotion": False,
                "automatic_claim_acceptance": False,
                "automatic_statistical_interpretation": False,
                "human_authorship_required": True,
                "explicit_protocol_deviations_required": True,
            },
        }

    def freeze_package(self, study_id: str, request: ScholarlyPackageFreezeRequest) -> dict[str, Any]:
        study = self.get(study_id)
        readiness = self.readiness(study_id)
        if request.require_publication_ready and not readiness["ready"]:
            raise ValueError(f"Study is not publication-ready; blockers={readiness['blockers']}")
        package = {
            "schema": SCHOLARLY_PACKAGE_SCHEMA,
            "release": settings.release_version,
            "package_id": _uid("rl-scholarly-package"),
            "package_label": request.package_label,
            "study_id": study_id,
            "core_project_id": study["core_project_id"],
            "workflow_id": study["workflow_id"],
            "study_fingerprint": study["study_fingerprint"],
            "protocol_hash": study["protocol_hash"],
            "protocol": study["protocol"],
            "deviations": study["deviations"],
            "results": study["results"],
            "interpretations": study["interpretations"],
            "manuscript_sections": study["manuscript_sections"],
            "source_refs": study["source_refs"],
            "core_evidence_refs": study["core_evidence_refs"],
            "core_research_object_refs": study["core_research_object_refs"],
            "statistical_reasoning_refs": study["statistical_reasoning_refs"],
            "visual_refs": study["visual_refs"],
            "authors": study["authors"],
            "affiliations": study["affiliations"],
            "funding_statement": study["funding_statement"],
            "conflict_of_interest_statement": study["conflict_of_interest_statement"],
            "publication_readiness": readiness,
            "reviewer_ref": request.reviewer_ref,
            "note": request.note,
            "frozen_utc": _now(),
            "governance": {
                "package_is_reproducibility_snapshot": True,
                "package_is_not_peer_review": True,
                "package_is_not_truth_certification": True,
                "human_authorship_required": True,
            },
        }
        package["package_hash"] = _sha(package)
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_scholarly_packages(package_id,study_id,package_hash,record,created_utc) VALUES(%s,%s,%s,%s,%s)", (package["package_id"], study_id, package["package_hash"], Jsonb(package), package["frozen_utc"]))
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute("INSERT INTO scholarly_packages(package_id,study_id,package_hash,record_json,created_utc) VALUES(?,?,?,?,?)", (package["package_id"], study_id, package["package_hash"], _json(package), package["frozen_utc"]))
        study["state"] = "complete"
        self._save(study, "scholarly-package-frozen", request.reviewer_ref)
        return package

    def revisions(self, study_id: str, limit: int = 200) -> list[dict[str, Any]]:
        self.get(study_id)
        limit = max(1, min(1000, int(limit)))
        if self.backend == "postgres":
            with self._postgres() as c:
                rows = c.execute("SELECT revision_id,revision_number,revision_hash,reason,actor_ref,created_utc FROM sc_rl_scholarly_study_revisions WHERE study_id=%s ORDER BY revision_number DESC LIMIT %s", (study_id, limit)).fetchall(); c.commit()
            return [{"schema": SCHOLARLY_REVISION_SCHEMA, **dict(x)} for x in rows]
        with self._lock, self._sqlite() as c:
            rows = c.execute("SELECT revision_id,revision_number,revision_hash,reason,actor_ref,created_utc FROM scholarly_study_revisions WHERE study_id=? ORDER BY revision_number DESC LIMIT ?", (study_id, limit)).fetchall()
        return [{"schema": SCHOLARLY_REVISION_SCHEMA, **dict(x)} for x in rows]

    def packages(self, study_id: str, limit: int = 100) -> list[dict[str, Any]]:
        self.get(study_id)
        limit = max(1, min(500, int(limit)))
        if self.backend == "postgres":
            with self._postgres() as c:
                rows = c.execute("SELECT record FROM sc_rl_scholarly_packages WHERE study_id=%s ORDER BY created_utc DESC LIMIT %s", (study_id, limit)).fetchall(); c.commit()
            return [dict(x["record"]) for x in rows]
        with self._lock, self._sqlite() as c:
            rows = c.execute("SELECT record_json FROM scholarly_packages WHERE study_id=? ORDER BY created_utc DESC LIMIT ?", (study_id, limit)).fetchall()
        return [json.loads(x["record_json"]) for x in rows]


_store: ScholarlyResearchStore | None = None
_store_lock = threading.Lock()


def get_scholarly_research_store() -> ScholarlyResearchStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ScholarlyResearchStore()
    return _store


def capabilities() -> dict[str, Any]:
    store = get_scholarly_research_store()
    return {
        "schema": SCHOLARLY_RESEARCH_SCHEMA,
        "release": settings.release_version,
        "storage_backend": store.backend,
        "durable_study_registry": True,
        "immutable_revision_history": True,
        "protocol_freeze": True,
        "explicit_protocol_deviations": True,
        "result_provenance_registry": True,
        "human_authored_interpretations": True,
        "human_authored_manuscript_sections": True,
        "publication_readiness_gate": True,
        "frozen_reproducibility_packages": True,
        "workflow_binding": True,
        "platform_core_lineage_refs": True,
        "automatic_truth_promotion": False,
        "automatic_claim_acceptance": False,
        "automatic_authorship": False,
        "automatic_statistical_interpretation": False,
        "package_is_peer_review": False,
    }
