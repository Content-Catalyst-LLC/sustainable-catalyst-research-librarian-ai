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
from ..contracts.peer_review import (
    PEER_REVIEW_SCHEMA, PEER_REVIEW_PACKAGE_SCHEMA, PEER_REVIEW_READINESS_SCHEMA,
    ReviewRoundCreateRequest, ReviewerAssignmentRequest, StructuredPeerReviewRequest,
    AuthorResponseRequest, RevisionSubmissionRequest, ReplicationAttemptRequest,
    EditorialDecisionRequest, PeerReviewPackageFreezeRequest,
)
from .scholarly_research import get_scholarly_research_store

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


class PeerReviewStore:
    """Durable human peer-review, replication and editorial-decision registry."""

    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "peer_review.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres peer-review storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._migrate_sqlite()

    @contextmanager
    def _sqlite(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.sqlite_path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=30000")
        try:
            yield c
        finally:
            c.close()

    @contextmanager
    def _postgres(self, migration: bool = False) -> Iterator[Any]:
        url = (settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c = psycopg.connect(url, autocommit=False, row_factory=dict_row)
        c.execute(f'SET search_path TO "{self.database_schema}"')
        try:
            yield c
        finally:
            c.close()

    def _migrate_sqlite(self) -> None:
        with self._lock, self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS peer_review_records(
  study_id TEXT PRIMARY KEY,
  core_project_id TEXT NOT NULL,
  record_json TEXT NOT NULL,
  record_fingerprint TEXT NOT NULL,
  created_utc TEXT NOT NULL,
  updated_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS peer_review_events(
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  study_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor_ref TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL,
  event_hash TEXT NOT NULL,
  created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_peer_review_events_study ON peer_review_events(study_id,event_id);
CREATE TABLE IF NOT EXISTS peer_review_packages(
  package_id TEXT PRIMARY KEY,
  study_id TEXT NOT NULL,
  package_hash TEXT NOT NULL,
  record_json TEXT NOT NULL,
  created_utc TEXT NOT NULL
);
""")

    def _migrate_postgres(self) -> None:
        with self._postgres(True) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_peer_review_records(
              study_id TEXT PRIMARY KEY,core_project_id TEXT NOT NULL,record JSONB NOT NULL,
              record_fingerprint TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now());""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_peer_review_events(
              event_id BIGSERIAL PRIMARY KEY,study_id TEXT NOT NULL REFERENCES sc_rl_peer_review_records(study_id) ON DELETE CASCADE,
              event_type TEXT NOT NULL,actor_ref TEXT NOT NULL DEFAULT '',payload JSONB NOT NULL,event_hash TEXT NOT NULL,
              created_utc TIMESTAMPTZ NOT NULL DEFAULT now());""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_sc_rl_peer_review_events_study ON sc_rl_peer_review_events(study_id,event_id)")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_peer_review_packages(
              package_id TEXT PRIMARY KEY,study_id TEXT NOT NULL REFERENCES sc_rl_peer_review_records(study_id) ON DELETE CASCADE,
              package_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now());""")
            c.commit()

    def _base_record(self, study_id: str) -> dict[str, Any]:
        study = get_scholarly_research_store().get(study_id)
        now = _now()
        return {
            "schema": PEER_REVIEW_SCHEMA,
            "release": settings.release_version,
            "study_id": study_id,
            "core_project_id": study["core_project_id"],
            "study_fingerprint": study["study_fingerprint"],
            "rounds": [], "assignments": [], "reviews": [], "responses": [],
            "revisions": [], "replications": [], "editorial_decisions": [],
            "created_utc": now, "updated_utc": now,
        }

    def _load(self, study_id: str) -> dict[str, Any] | None:
        if self.backend == "postgres":
            with self._postgres() as c:
                row = c.execute("SELECT record FROM sc_rl_peer_review_records WHERE study_id=%s", (study_id,)).fetchone(); c.commit()
            return dict(row["record"]) if row else None
        with self._lock, self._sqlite() as c:
            row = c.execute("SELECT record_json FROM peer_review_records WHERE study_id=?", (study_id,)).fetchone()
        return json.loads(row["record_json"]) if row else None

    def get(self, study_id: str, create_if_missing: bool = True) -> dict[str, Any]:
        get_scholarly_research_store().get(study_id)
        record = self._load(study_id)
        if record is not None:
            return record
        if not create_if_missing:
            raise KeyError(study_id)
        record = self._base_record(study_id)
        record["record_fingerprint"] = _sha(record)
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_peer_review_records(study_id,core_project_id,record,record_fingerprint,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(study_id) DO NOTHING", (study_id, record["core_project_id"], Jsonb(record), record["record_fingerprint"], record["created_utc"], record["updated_utc"])); c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute("INSERT OR IGNORE INTO peer_review_records(study_id,core_project_id,record_json,record_fingerprint,created_utc,updated_utc) VALUES(?,?,?,?,?,?)", (study_id, record["core_project_id"], _json(record), record["record_fingerprint"], record["created_utc"], record["updated_utc"]))
        return self._load(study_id) or record

    def _event(self, study_id: str, event_type: str, actor_ref: str, payload: dict[str, Any]) -> None:
        created = _now(); event_hash = _sha({"study_id": study_id, "event_type": event_type, "actor_ref": actor_ref, "payload": payload, "created_utc": created})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_peer_review_events(study_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)", (study_id,event_type,actor_ref,Jsonb(payload),event_hash,created)); c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute("INSERT INTO peer_review_events(study_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)", (study_id,event_type,actor_ref,_json(payload),event_hash,created))

    def _save(self, record: dict[str, Any], event_type: str, actor_ref: str, payload: dict[str, Any]) -> dict[str, Any]:
        item = json.loads(_json(record)); item["release"] = settings.release_version; item["updated_utc"] = _now()
        item["record_fingerprint"] = _sha({k:v for k,v in item.items() if k not in {"record_fingerprint","updated_utc"}})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute("UPDATE sc_rl_peer_review_records SET record=%s,record_fingerprint=%s,updated_utc=%s WHERE study_id=%s", (Jsonb(item),item["record_fingerprint"],item["updated_utc"],item["study_id"])); c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute("UPDATE peer_review_records SET record_json=?,record_fingerprint=?,updated_utc=? WHERE study_id=?", (_json(item),item["record_fingerprint"],item["updated_utc"],item["study_id"]))
        self._event(item["study_id"], event_type, actor_ref, payload)
        return item

    def create_round(self, study_id: str, request: ReviewRoundCreateRequest) -> tuple[dict[str, Any], bool]:
        record = self.get(study_id)
        key = str(request.idempotency_key or "").strip()
        if key:
            for r in record["rounds"]:
                if r.get("idempotency_key") == key:
                    return r, True
        round_item = {"round_id": _uid("review-round"), **request.model_dump(mode="json"), "state": "open", "created_utc": _now()}
        round_item["round_hash"] = _sha(round_item)
        record["rounds"].append(round_item)
        self._save(record, "review-round-created", request.actor_ref, {"round_id": round_item["round_id"]})
        return round_item, False

    def _round(self, record: dict[str, Any], round_id: str) -> dict[str, Any]:
        for item in record["rounds"]:
            if item["round_id"] == round_id:
                return item
        raise ValueError(f"Unknown round_id: {round_id}")

    def assign_reviewer(self, study_id: str, round_id: str, request: ReviewerAssignmentRequest) -> dict[str, Any]:
        record = self.get(study_id); self._round(record, round_id)
        if any(a["round_id"] == round_id and a["reviewer_ref"] == request.reviewer_ref for a in record["assignments"]):
            raise ValueError("Reviewer is already assigned to this round")
        item = {"assignment_id": _uid("review-assignment"), "round_id": round_id, **request.model_dump(mode="json"), "state": "assigned", "created_utc": _now()}
        item["assignment_hash"] = _sha(item); record["assignments"].append(item)
        return self._save(record, "reviewer-assigned", request.assigned_by_ref, {"assignment_id": item["assignment_id"], "round_id": round_id})

    def submit_review(self, study_id: str, round_id: str, request: StructuredPeerReviewRequest) -> dict[str, Any]:
        record = self.get(study_id); self._round(record, round_id)
        assignment = next((a for a in record["assignments"] if a["round_id"] == round_id and a["reviewer_ref"] == request.reviewer_ref), None)
        if assignment is None:
            raise ValueError("Reviewer must be assigned before submitting a review")
        if assignment.get("conflict_status") == "confirmed":
            raise ValueError("Reviewer with a confirmed conflict cannot submit a review")
        if any(r["round_id"] == round_id and r["reviewer_ref"] == request.reviewer_ref for r in record["reviews"]):
            raise ValueError("Reviewer has already submitted a review for this round")
        item = {"review_id": _uid("peer-review"), "round_id": round_id, **request.model_dump(mode="json"), "submitted_utc": _now()}
        item["review_hash"] = _sha(item); record["reviews"].append(item); assignment["state"] = "submitted"
        return self._save(record, "peer-review-submitted", request.reviewer_ref, {"review_id": item["review_id"], "round_id": round_id})

    def add_response(self, study_id: str, request: AuthorResponseRequest) -> dict[str, Any]:
        record = self.get(study_id)
        review = next((r for r in record["reviews"] if r["review_id"] == request.review_id), None)
        if review is None:
            raise ValueError(f"Unknown review_id: {request.review_id}")
        item = {"response_id": _uid("author-response"), **request.model_dump(mode="json"), "round_id": review["round_id"], "created_utc": _now()}
        item["response_hash"] = _sha(item); record["responses"].append(item)
        return self._save(record, "author-response-submitted", request.author_ref, {"response_id": item["response_id"], "review_id": request.review_id})

    def add_revision(self, study_id: str, request: RevisionSubmissionRequest) -> dict[str, Any]:
        record = self.get(study_id)
        known_responses = {x["response_id"] for x in record["responses"]}
        unknown = [x for x in request.response_refs if x not in known_responses]
        if unknown:
            raise ValueError(f"Unknown response_refs: {unknown}")
        item = {"revision_id": _uid("peer-review-revision"), **request.model_dump(mode="json"), "created_utc": _now()}
        item["revision_hash"] = _sha(item); record["revisions"].append(item)
        return self._save(record, "revision-submitted", request.author_ref, {"revision_id": item["revision_id"]})

    def add_replication(self, study_id: str, request: ReplicationAttemptRequest) -> dict[str, Any]:
        record = self.get(study_id)
        study = get_scholarly_research_store().get(study_id)
        known_results = {x["result_id"] for x in study.get("results", [])}
        unknown = [x for x in request.result_refs if x not in known_results]
        if unknown:
            raise ValueError(f"Unknown result_refs: {unknown}")
        item = {"replication_id": _uid("replication"), **request.model_dump(mode="json"), "created_utc": _now()}
        item["replication_hash"] = _sha(item); record["replications"].append(item)
        return self._save(record, "replication-attempt-recorded", request.actor_ref, {"replication_id": item["replication_id"], "outcome": item["outcome"]})

    def add_decision(self, study_id: str, request: EditorialDecisionRequest) -> dict[str, Any]:
        record = self.get(study_id)
        known_reviews = {x["review_id"] for x in record["reviews"]}; known_replications = {x["replication_id"] for x in record["replications"]}
        unknown_reviews = [x for x in request.based_on_review_ids if x not in known_reviews]
        unknown_replications = [x for x in request.based_on_replication_ids if x not in known_replications]
        if unknown_reviews or unknown_replications:
            raise ValueError(f"Unknown decision references: reviews={unknown_reviews}, replications={unknown_replications}")
        if request.supersedes_decision_id and request.supersedes_decision_id not in {x["decision_id"] for x in record["editorial_decisions"]}:
            raise ValueError("supersedes_decision_id is unknown")
        item = {"decision_id": _uid("editorial-decision"), **request.model_dump(mode="json"), "created_utc": _now()}
        item["decision_hash"] = _sha(item); record["editorial_decisions"].append(item)
        return self._save(record, "editorial-decision-recorded", request.editor_ref, {"decision_id": item["decision_id"], "decision": item["decision"]})

    def readiness(self, study_id: str) -> dict[str, Any]:
        record = self.get(study_id); study = get_scholarly_research_store().get(study_id)
        assigned = {(a["round_id"], a["reviewer_ref"]) for a in record["assignments"] if a.get("conflict_status") != "confirmed"}
        submitted = {(r["round_id"], r["reviewer_ref"]) for r in record["reviews"]}
        review_ids = {r["review_id"] for r in record["reviews"]}; responded = {r["review_id"] for r in record["responses"]}
        latest_decision = record["editorial_decisions"][-1] if record["editorial_decisions"] else None
        checks = {
            "study_protocol_frozen": bool(study.get("protocol_frozen")),
            "at_least_one_review_round": bool(record["rounds"]),
            "at_least_one_eligible_assignment": bool(assigned),
            "assigned_reviews_submitted": bool(assigned) and assigned.issubset(submitted),
            "review_reports_present": bool(record["reviews"]),
            "review_responses_complete": review_ids.issubset(responded) if review_ids else False,
            "editorial_decision_recorded": latest_decision is not None and latest_decision.get("decision") != "no-decision",
            "replication_attempts_are_explicit_if_present": all(bool(x.get("actor_ref") and x.get("summary")) for x in record["replications"]),
        }
        blockers = [k for k,v in checks.items() if not v and k not in {"review_responses_complete"}]
        return {
            "schema": PEER_REVIEW_READINESS_SCHEMA, "release": settings.release_version, "study_id": study_id,
            "ready": not blockers, "checks": checks, "blockers": blockers,
            "latest_editorial_decision": latest_decision,
            "counts": {k: len(record[k]) for k in ["rounds","assignments","reviews","responses","revisions","replications","editorial_decisions"]},
            "governance": {
                "readiness_is_completeness_not_validity": True,
                "automatic_acceptance": False, "automatic_rejection": False,
                "automatic_replication_judgment": False, "automatic_truth_promotion": False,
                "human_peer_review_required": True, "human_editorial_decision_required": True,
            },
        }

    def freeze_package(self, study_id: str, request: PeerReviewPackageFreezeRequest) -> dict[str, Any]:
        record = self.get(study_id); readiness = self.readiness(study_id)
        if request.require_decision and not readiness["checks"]["editorial_decision_recorded"]:
            raise ValueError("An explicit editorial decision is required before freezing this package")
        if request.require_all_reviews_responded and not readiness["checks"]["review_responses_complete"]:
            raise ValueError("All submitted reviews must have author responses before freezing this package")
        study = get_scholarly_research_store().get(study_id)
        package = {
            "schema": PEER_REVIEW_PACKAGE_SCHEMA, "release": settings.release_version,
            "package_id": _uid("rl-peer-review-package"), "package_label": request.package_label,
            "study_id": study_id, "core_project_id": study["core_project_id"],
            "study_fingerprint": study["study_fingerprint"], "protocol_hash": study.get("protocol_hash", ""),
            "peer_review_record_fingerprint": record["record_fingerprint"],
            "rounds": record["rounds"], "assignments": record["assignments"], "reviews": record["reviews"],
            "responses": record["responses"], "revisions": record["revisions"], "replications": record["replications"],
            "editorial_decisions": record["editorial_decisions"], "readiness": readiness,
            "actor_ref": request.actor_ref, "note": request.note, "frozen_utc": _now(),
            "governance": {
                "package_preserves_human_review_record": True,
                "package_is_not_validity_certification": True,
                "replication_outcomes_are_reported_not_inferred": True,
                "editorial_decisions_are_human_authored": True,
                "automatic_truth_promotion": False,
            },
        }
        package["package_hash"] = _sha(package)
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_peer_review_packages(package_id,study_id,package_hash,record,created_utc) VALUES(%s,%s,%s,%s,%s)", (package["package_id"],study_id,package["package_hash"],Jsonb(package),package["frozen_utc"])); c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute("INSERT INTO peer_review_packages(package_id,study_id,package_hash,record_json,created_utc) VALUES(?,?,?,?,?)", (package["package_id"],study_id,package["package_hash"],_json(package),package["frozen_utc"]))
        self._event(study_id, "peer-review-package-frozen", request.actor_ref, {"package_id": package["package_id"], "package_hash": package["package_hash"]})
        return package

    def events(self, study_id: str, limit: int = 500) -> list[dict[str, Any]]:
        self.get(study_id); limit=max(1,min(2000,int(limit)))
        if self.backend == "postgres":
            with self._postgres() as c:
                rows=c.execute("SELECT event_id,event_type,actor_ref,payload,event_hash,created_utc FROM sc_rl_peer_review_events WHERE study_id=%s ORDER BY event_id DESC LIMIT %s",(study_id,limit)).fetchall(); c.commit()
            return [{**dict(r), "payload": dict(r["payload"])} for r in rows]
        with self._lock, self._sqlite() as c:
            rows=c.execute("SELECT event_id,event_type,actor_ref,payload_json,event_hash,created_utc FROM peer_review_events WHERE study_id=? ORDER BY event_id DESC LIMIT ?",(study_id,limit)).fetchall()
        return [{"event_id":r["event_id"],"event_type":r["event_type"],"actor_ref":r["actor_ref"],"payload":json.loads(r["payload_json"]),"event_hash":r["event_hash"],"created_utc":r["created_utc"]} for r in rows]

    def packages(self, study_id: str, limit: int = 100) -> list[dict[str, Any]]:
        self.get(study_id); limit=max(1,min(500,int(limit)))
        if self.backend == "postgres":
            with self._postgres() as c:
                rows=c.execute("SELECT record FROM sc_rl_peer_review_packages WHERE study_id=%s ORDER BY created_utc DESC LIMIT %s",(study_id,limit)).fetchall(); c.commit()
            return [dict(r["record"]) for r in rows]
        with self._lock, self._sqlite() as c:
            rows=c.execute("SELECT record_json FROM peer_review_packages WHERE study_id=? ORDER BY created_utc DESC LIMIT ?",(study_id,limit)).fetchall()
        return [json.loads(r["record_json"]) for r in rows]


_store: PeerReviewStore | None = None
_store_lock = threading.Lock()


def get_peer_review_store() -> PeerReviewStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = PeerReviewStore()
    return _store


def capabilities() -> dict[str, Any]:
    store = get_peer_review_store()
    return {
        "schema": PEER_REVIEW_SCHEMA, "release": settings.release_version, "storage_backend": store.backend,
        "durable_peer_review_registry": True, "structured_review_rounds": True,
        "reviewer_assignment_and_conflict_declarations": True, "author_response_lineage": True,
        "revision_submission_lineage": True, "replication_attempt_registry": True,
        "explicit_editorial_decisions": True, "validation_readiness_checks": True,
        "frozen_peer_review_packages": True, "automatic_acceptance": False,
        "automatic_rejection": False, "automatic_replication_judgment": False,
        "automatic_truth_promotion": False, "machine_peer_review_certification": False,
    }
