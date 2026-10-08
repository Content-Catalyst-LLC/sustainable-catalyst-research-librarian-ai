from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.cross_language_entity_toponym_resolution import *

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg = None
    dict_row = None
    Jsonb = None


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, value: Any) -> str:
    return prefix + _sha(value)[:32]


def _uniq(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))


def resolution_manifest() -> dict[str, Any]:
    return {
        "schema": CROSS_LANGUAGE_RESOLUTION_SCHEMA,
        "release": "12.4.0",
        "milestone": "12.4.0",
        "name": "Cross-Language Entity & Toponym Resolution",
        "runtime_authority": "python-fastapi-backend",
        "wordpress_required": False,
        "durable": True,
        "principles": {
            "original_script_preserved": True,
            "original_language_context_preserved": True,
            "candidate_generation_separate_from_confirmation": True,
            "aliases_and_transliterations_are_provenanced_representations": True,
            "toponym_historical_and_jurisdictional_ambiguity_preserved": True,
            "confidence_is_descriptive_not_truth": True,
            "human_review_required_for_acceptance": True,
            "canonical_identity_promotion_is_external_governed_action": True,
        },
        "scope": {
            "cross_language_entity_resolution": True,
            "cross_language_toponym_resolution": True,
            "alias_alignment": True,
            "transliteration_aware_candidates": True,
            "translation_variant_candidates": True,
            "historical_toponym_candidates": True,
            "jurisdiction_aware_toponym_candidates": True,
            "reviewable_resolution_decisions": True,
            "immutable_resolution_snapshots": True,
            "automatic_identity_promotion": False,
            "automatic_truth_promotion": False,
            "automatic_remote_geocoding": False,
            "automatic_citation_resolution": False,
            "automatic_evidence_resolution": False,
        },
        "authority": {
            "research_librarian_resolution_context_authority": True,
            "platform_core_contract_and_provenance_authority": True,
            "knowledge_library_source_identity_authority": True,
            "specialist_runtime_candidate_generation_allowed": True,
            "wordpress_runtime_authority": False,
        },
        "governance": {
            "accepted_resolution_requires_human_review": True,
            "competing_candidates_preserved": True,
            "source_evidence_preserved": True,
            "transformation_lineage_preserved": True,
            "politically_contested_toponyms_not_silently_normalized": True,
            "canonical_identity_not_written_automatically": True,
        },
        "database_migration": "044_cross_language_entity_toponym_resolution.sql",
        "next_boundary": "cross-language-citation-evidence-resolution",
    }


def capabilities() -> dict[str, Any]:
    return {
        "milestone": "12.4.0",
        "entity_mentions": True,
        "entity_candidates": True,
        "entity_resolution_decisions": True,
        "toponym_mentions": True,
        "toponym_candidates": True,
        "toponym_resolution_decisions": True,
        "alias_alignment": True,
        "historical_toponym_context": True,
        "jurisdiction_context": True,
        "human_review_gate": True,
        "core_candidate_export": True,
        "immutable_snapshots": True,
        "automatic_identity_promotion": False,
        "automatic_remote_geocoding": False,
        "wordpress_required": False,
    }


class CrossLanguageEntityToponymResolutionStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "cross_language_entity_toponym_resolution.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres cross-language resolution storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._migrate_sqlite()

    @contextmanager
    def _sqlite(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.sqlite_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _postgres(self, migration: bool = False) -> Iterator[Any]:
        url = (settings.direct_database_url if migration else settings.database_url) or settings.database_url
        conn = psycopg.connect(url, autocommit=False, row_factory=dict_row)
        conn.execute(f'SET search_path TO "{self.database_schema}"')
        try:
            yield conn
        finally:
            conn.close()

    def _migrate_sqlite(self) -> None:
        with self._lock, self._sqlite() as conn:
            conn.executescript("""
CREATE TABLE IF NOT EXISTS cross_language_resolution_projects(
 resolution_id TEXT PRIMARY KEY,
 owner_ref TEXT NOT NULL,
 record_json TEXT NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL,
 updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cross_language_resolution_projects_owner
 ON cross_language_resolution_projects(owner_ref);
CREATE TABLE IF NOT EXISTS cross_language_resolution_events(
 event_id INTEGER PRIMARY KEY AUTOINCREMENT,
 resolution_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 event_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cross_language_resolution_events_project
 ON cross_language_resolution_events(resolution_id);
CREATE TABLE IF NOT EXISTS cross_language_resolution_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 resolution_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record_json TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cross_language_resolution_snapshots_project
 ON cross_language_resolution_snapshots(resolution_id);
""")

    def _migrate_postgres(self) -> None:
        with self._postgres(True) as conn:
            for ddl in [
                """CREATE TABLE IF NOT EXISTS sc_rl_cross_language_resolution_projects(
 resolution_id TEXT PRIMARY KEY,
 owner_ref TEXT NOT NULL,
 record JSONB NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_language_resolution_projects_owner ON sc_rl_cross_language_resolution_projects(owner_ref)",
                """CREATE TABLE IF NOT EXISTS sc_rl_cross_language_resolution_events(
 event_id BIGSERIAL PRIMARY KEY,
 resolution_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 payload JSONB NOT NULL,
 event_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_language_resolution_events_project ON sc_rl_cross_language_resolution_events(resolution_id)",
                """CREATE TABLE IF NOT EXISTS sc_rl_cross_language_resolution_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 resolution_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record JSONB NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_language_resolution_snapshots_project ON sc_rl_cross_language_resolution_snapshots(resolution_id)",
            ]:
                conn.execute(ddl)
            conn.commit()

    def _event(self, resolution_id: str, event_type: str, actor_ref: str, payload: dict[str, Any]) -> None:
        created = _now()
        event_hash = _sha({
            "resolution_id": resolution_id,
            "event_type": event_type,
            "actor_ref": actor_ref,
            "payload": payload,
            "created_utc": created,
        })
        if self.backend == "postgres":
            with self._postgres() as conn:
                conn.execute(
                    "INSERT INTO sc_rl_cross_language_resolution_events(resolution_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",
                    (resolution_id, event_type, actor_ref, Jsonb(payload), event_hash, created),
                )
                conn.commit()
        else:
            with self._lock, self._sqlite() as conn:
                conn.execute(
                    "INSERT INTO cross_language_resolution_events(resolution_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",
                    (resolution_id, event_type, actor_ref, _json(payload), event_hash, created),
                )

    def _save(self, record: dict[str, Any]) -> dict[str, Any]:
        record["updated_utc"] = _now()
        record["record_hash"] = _sha({k: v for k, v in record.items() if k != "record_hash"})
        if self.backend == "postgres":
            with self._postgres() as conn:
                conn.execute(
                    """INSERT INTO sc_rl_cross_language_resolution_projects(resolution_id,owner_ref,record,record_hash,created_utc,updated_utc)
VALUES(%s,%s,%s,%s,%s,%s)
ON CONFLICT(resolution_id) DO UPDATE SET owner_ref=EXCLUDED.owner_ref,record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc""",
                    (
                        record["resolution_id"], record["owner_ref"], Jsonb(record), record["record_hash"],
                        record["created_utc"], record["updated_utc"],
                    ),
                )
                conn.commit()
        else:
            with self._lock, self._sqlite() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cross_language_resolution_projects(resolution_id,owner_ref,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?,?)",
                    (
                        record["resolution_id"], record["owner_ref"], _json(record), record["record_hash"],
                        record["created_utc"], record["updated_utc"],
                    ),
                )
        return record

    def create(self, req: CrossLanguageResolutionCreateRequest) -> dict[str, Any]:
        body = req.model_dump()
        actor_ref = body.pop("actor_ref")
        resolution_id = _id("resolution-", {**body, "owner_ref": actor_ref})
        try:
            return self.get(resolution_id)
        except ValueError:
            pass
        now = _now()
        record = {
            "schema": CROSS_LANGUAGE_RESOLUTION_SCHEMA,
            "resolution_id": resolution_id,
            "owner_ref": actor_ref,
            **body,
            "entity_mentions": [],
            "entity_candidates": [],
            "entity_resolutions": [],
            "toponym_mentions": [],
            "toponym_candidates": [],
            "toponym_resolutions": [],
            "alias_alignments": [],
            "review": {"state": "draft", "actor_ref": actor_ref, "note": "", "updated_utc": now},
            "created_utc": now,
            "updated_utc": now,
            "governance": {
                "original_script_preserved": True,
                "original_language_context_preserved": True,
                "candidate_generation_separate_from_confirmation": True,
                "confidence_is_descriptive_not_truth": True,
                "accepted_resolution_requires_human_review": True,
                "competing_candidates_preserved": True,
                "canonical_identity_promotion_is_external_governed_action": True,
                "automatic_identity_promotion": False,
                "automatic_truth_promotion": False,
                "automatic_remote_geocoding": False,
                "automatic_citation_resolution": False,
                "automatic_evidence_resolution": False,
            },
        }
        self._save(record)
        self._event(resolution_id, "cross-language-resolution.created", actor_ref, {
            "project_ref": body.get("project_ref", ""),
            "federation_ref": body.get("federation_ref", ""),
        })
        return self.get(resolution_id)

    def get(self, resolution_id: str) -> dict[str, Any]:
        if self.backend == "postgres":
            with self._postgres() as conn:
                row = conn.execute(
                    "SELECT record FROM sc_rl_cross_language_resolution_projects WHERE resolution_id=%s",
                    (resolution_id,),
                ).fetchone()
            if not row:
                raise ValueError("Cross-language resolution project not found.")
            return dict(row["record"])
        with self._lock, self._sqlite() as conn:
            row = conn.execute(
                "SELECT record_json FROM cross_language_resolution_projects WHERE resolution_id=?",
                (resolution_id,),
            ).fetchone()
        if not row:
            raise ValueError("Cross-language resolution project not found.")
        return json.loads(row["record_json"])

    def list(self, limit: int = 100, owner_ref: str = "") -> dict[str, Any]:
        limit = max(1, min(500, int(limit)))
        if self.backend == "postgres":
            with self._postgres() as conn:
                if owner_ref:
                    rows = conn.execute(
                        "SELECT record FROM sc_rl_cross_language_resolution_projects WHERE owner_ref=%s ORDER BY updated_utc DESC LIMIT %s",
                        (owner_ref, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT record FROM sc_rl_cross_language_resolution_projects ORDER BY updated_utc DESC LIMIT %s",
                        (limit,),
                    ).fetchall()
            items = [dict(row["record"]) for row in rows]
        else:
            with self._lock, self._sqlite() as conn:
                if owner_ref:
                    rows = conn.execute(
                        "SELECT record_json FROM cross_language_resolution_projects WHERE owner_ref=? ORDER BY updated_utc DESC LIMIT ?",
                        (owner_ref, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT record_json FROM cross_language_resolution_projects ORDER BY updated_utc DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
            items = [json.loads(row["record_json"]) for row in rows]
        return {"items": items, "count": len(items), "limit": limit, "owner_ref": owner_ref}

    def _append(self, resolution_id: str, key: str, id_key: str, prefix: str, body: dict[str, Any], event_type: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        record = self.get(resolution_id)
        actor_ref = body.pop("actor_ref")
        object_id = _id(prefix, body)
        item = {id_key: object_id, **body, **(extra or {}), "created_utc": _now()}
        if not any(existing.get(id_key) == object_id for existing in record[key]):
            record[key].append(item)
            self._save(record)
            self._event(resolution_id, event_type, actor_ref, {id_key: object_id})
        return self.get(resolution_id)

    @staticmethod
    def _require(record: dict[str, Any], key: str, id_key: str, value: str, label: str) -> dict[str, Any]:
        for item in record[key]:
            if item.get(id_key) == value:
                return item
        raise ValueError(f"{label} not found.")

    def add_entity_mention(self, resolution_id: str, req: EntityMentionAddRequest) -> dict[str, Any]:
        body = req.model_dump()
        body["transformation_refs"] = _uniq(body["transformation_refs"])
        return self._append(
            resolution_id, "entity_mentions", "mention_id", "entity-mention-", body,
            "cross-language-resolution.entity-mention-added",
            {
                "schema": ENTITY_MENTION_SCHEMA,
                "original_script_is_preserved": True,
                "translation_or_transliteration_is_not_identity": True,
            },
        )

    def add_entity_candidate(self, resolution_id: str, req: EntityCandidateAddRequest) -> dict[str, Any]:
        body = req.model_dump()
        record = self.get(resolution_id)
        self._require(record, "entity_mentions", "mention_id", body["mention_id"], "Entity mention")
        for key in ["native_labels", "language_profile_refs", "alias_refs", "source_evidence_refs"]:
            body[key] = _uniq(body[key])
        return self._append(
            resolution_id, "entity_candidates", "candidate_id", "entity-candidate-", body,
            "cross-language-resolution.entity-candidate-added",
            {
                "schema": ENTITY_CANDIDATE_SCHEMA,
                "candidate_is_not_confirmed_identity": True,
                "descriptive_score_is_not_probability_of_truth": True,
                "automatic_identity_promotion": False,
            },
        )

    def resolve_entity(self, resolution_id: str, req: EntityResolutionDecisionRequest) -> dict[str, Any]:
        body = req.model_dump()
        record = self.get(resolution_id)
        self._require(record, "entity_mentions", "mention_id", body["mention_id"], "Entity mention")
        candidate = self._require(record, "entity_candidates", "candidate_id", body["candidate_id"], "Entity candidate")
        if candidate.get("mention_id") != body["mention_id"]:
            raise ValueError("Entity candidate does not belong to the supplied mention.")
        if body["decision"] == "accepted":
            if not body["human_reviewed"]:
                raise ValueError("Accepted entity resolution requires human_reviewed=true.")
            if not body["reviewer_ref"].strip():
                raise ValueError("Accepted entity resolution requires reviewer_ref.")
        body["evidence_refs"] = _uniq(body["evidence_refs"])
        return self._append(
            resolution_id, "entity_resolutions", "resolution_decision_id", "entity-resolution-", body,
            "cross-language-resolution.entity-resolution-recorded",
            {
                "schema": ENTITY_RESOLUTION_SCHEMA,
                "canonical_identity_promoted": False,
                "core_promotion_requires_explicit_governed_action": True,
            },
        )

    def add_toponym_mention(self, resolution_id: str, req: ToponymMentionAddRequest) -> dict[str, Any]:
        body = req.model_dump()
        body["transformation_refs"] = _uniq(body["transformation_refs"])
        return self._append(
            resolution_id, "toponym_mentions", "mention_id", "toponym-mention-", body,
            "cross-language-resolution.toponym-mention-added",
            {
                "schema": TOPONYM_MENTION_SCHEMA,
                "original_script_is_preserved": True,
                "jurisdiction_and_temporal_context_are_evidence": True,
            },
        )

    def add_toponym_candidate(self, resolution_id: str, req: ToponymCandidateAddRequest) -> dict[str, Any]:
        body = req.model_dump()
        record = self.get(resolution_id)
        self._require(record, "toponym_mentions", "mention_id", body["mention_id"], "Toponym mention")
        for key in ["native_labels", "alias_refs", "source_evidence_refs"]:
            body[key] = _uniq(body[key])
        return self._append(
            resolution_id, "toponym_candidates", "candidate_id", "toponym-candidate-", body,
            "cross-language-resolution.toponym-candidate-added",
            {
                "schema": TOPONYM_CANDIDATE_SCHEMA,
                "candidate_is_not_confirmed_place": True,
                "coordinates_are_candidate_metadata_not_canonical_truth": True,
                "historical_and_political_ambiguity_must_be_preserved": True,
                "automatic_remote_geocoding": False,
            },
        )

    def resolve_toponym(self, resolution_id: str, req: ToponymResolutionDecisionRequest) -> dict[str, Any]:
        body = req.model_dump()
        record = self.get(resolution_id)
        self._require(record, "toponym_mentions", "mention_id", body["mention_id"], "Toponym mention")
        candidate = self._require(record, "toponym_candidates", "candidate_id", body["candidate_id"], "Toponym candidate")
        if candidate.get("mention_id") != body["mention_id"]:
            raise ValueError("Toponym candidate does not belong to the supplied mention.")
        if body["decision"] == "accepted":
            if not body["human_reviewed"]:
                raise ValueError("Accepted toponym resolution requires human_reviewed=true.")
            if not body["reviewer_ref"].strip():
                raise ValueError("Accepted toponym resolution requires reviewer_ref.")
        body["evidence_refs"] = _uniq(body["evidence_refs"])
        return self._append(
            resolution_id, "toponym_resolutions", "resolution_decision_id", "toponym-resolution-", body,
            "cross-language-resolution.toponym-resolution-recorded",
            {
                "schema": TOPONYM_RESOLUTION_SCHEMA,
                "canonical_place_promoted": False,
                "competing_candidates_preserved": bool(body.get("preserve_competing_candidates", True)),
                "core_promotion_requires_explicit_governed_action": True,
            },
        )

    def add_alias_alignment(self, resolution_id: str, req: AliasAlignmentAddRequest) -> dict[str, Any]:
        body = req.model_dump()
        body["transformation_refs"] = _uniq(body["transformation_refs"])
        return self._append(
            resolution_id, "alias_alignments", "alias_alignment_id", "alias-alignment-", body,
            "cross-language-resolution.alias-alignment-added",
            {
                "schema": ALIAS_ALIGNMENT_SCHEMA,
                "representation_is_provenanced": True,
                "representation_is_not_automatic_identity_equivalence": True,
            },
        )

    def lineage(self, resolution_id: str) -> dict[str, Any]:
        record = self.get(resolution_id)
        return {
            "schema": CROSS_LANGUAGE_RESOLUTION_SCHEMA,
            "resolution_id": resolution_id,
            "record_hash": record["record_hash"],
            "federation_ref": record.get("federation_ref", ""),
            "multilingual_research_ref": record.get("multilingual_research_ref", ""),
            "entity_mentions": len(record["entity_mentions"]),
            "entity_candidates": len(record["entity_candidates"]),
            "entity_resolutions": len(record["entity_resolutions"]),
            "toponym_mentions": len(record["toponym_mentions"]),
            "toponym_candidates": len(record["toponym_candidates"]),
            "toponym_resolutions": len(record["toponym_resolutions"]),
            "alias_alignments": len(record["alias_alignments"]),
            "governance": {
                "original_script_preserved": True,
                "candidate_generation_separate_from_confirmation": True,
                "accepted_resolution_requires_human_review": True,
                "confidence_is_descriptive_not_truth": True,
                "canonical_identity_promotion_is_external": True,
                "competing_toponym_candidates_preserved": True,
            },
        }

    def readiness(self, resolution_id: str) -> dict[str, Any]:
        record = self.get(resolution_id)
        entity_accepted = [x for x in record["entity_resolutions"] if x["decision"] == "accepted"]
        toponym_accepted = [x for x in record["toponym_resolutions"] if x["decision"] == "accepted"]
        return {
            "resolution_id": resolution_id,
            "entity_mentions": len(record["entity_mentions"]),
            "entity_candidates": len(record["entity_candidates"]),
            "accepted_entity_resolutions": len(entity_accepted),
            "toponym_mentions": len(record["toponym_mentions"]),
            "toponym_candidates": len(record["toponym_candidates"]),
            "accepted_toponym_resolutions": len(toponym_accepted),
            "human_review_gate_satisfied": all(x.get("human_reviewed") for x in entity_accepted + toponym_accepted),
            "canonical_promotion_performed": False,
            "ready_for_core_candidate_review": bool(entity_accepted or toponym_accepted),
        }

    def core_candidate(self, resolution_id: str) -> dict[str, Any]:
        record = self.get(resolution_id)
        accepted_entities = [x for x in record["entity_resolutions"] if x["decision"] == "accepted" and x.get("human_reviewed")]
        accepted_toponyms = [x for x in record["toponym_resolutions"] if x["decision"] == "accepted" and x.get("human_reviewed")]
        return {
            "schema": "sc-platform-core-cross-language-resolution-candidate/1.0",
            "source_product": "research-librarian",
            "source_release": "12.4.0",
            "resolution_id": resolution_id,
            "source_record_hash": record["record_hash"],
            "accepted_entity_resolution_refs": [x["resolution_decision_id"] for x in accepted_entities],
            "accepted_toponym_resolution_refs": [x["resolution_decision_id"] for x in accepted_toponyms],
            "alias_alignment_refs": [x["alias_alignment_id"] for x in record["alias_alignments"]],
            "promotion_requires_explicit_core_write": True,
            "automatic_canonical_identity_promotion": False,
            "automatic_truth_promotion": False,
            "provenance_required": True,
        }

    def set_state(self, resolution_id: str, req: CrossLanguageResolutionStateRequest) -> dict[str, Any]:
        record = self.get(resolution_id)
        record["review"] = {
            "state": req.state,
            "actor_ref": req.actor_ref,
            "note": req.note,
            "updated_utc": _now(),
        }
        self._save(record)
        self._event(resolution_id, "cross-language-resolution.state-changed", req.actor_ref, {"state": req.state})
        return self.get(resolution_id)

    def freeze_snapshot(self, req: CrossLanguageResolutionSnapshotRequest) -> dict[str, Any]:
        record = self.get(req.resolution_id)
        snapshot_body = {
            "schema": CROSS_LANGUAGE_RESOLUTION_SNAPSHOT_SCHEMA,
            "resolution_id": req.resolution_id,
            "label": req.label,
            "note": req.note,
            "actor_ref": req.actor_ref,
            "record": record,
            "created_utc": _now(),
            "governance": {
                "immutable_snapshot": True,
                "snapshot_does_not_promote_identity": True,
                "snapshot_preserves_competing_candidates": True,
            },
        }
        snapshot_hash = _sha(snapshot_body)
        snapshot_id = "resolution-snapshot-" + snapshot_hash[:32]
        snapshot = {"snapshot_id": snapshot_id, "snapshot_hash": snapshot_hash, **snapshot_body}
        if self.backend == "postgres":
            with self._postgres() as conn:
                conn.execute(
                    """INSERT INTO sc_rl_cross_language_resolution_snapshots(snapshot_id,resolution_id,snapshot_hash,record,created_utc)
VALUES(%s,%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING""",
                    (snapshot_id, req.resolution_id, snapshot_hash, Jsonb(snapshot), snapshot["created_utc"]),
                )
                conn.commit()
        else:
            with self._lock, self._sqlite() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO cross_language_resolution_snapshots(snapshot_id,resolution_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",
                    (snapshot_id, req.resolution_id, snapshot_hash, _json(snapshot), snapshot["created_utc"]),
                )
        self._event(req.resolution_id, "cross-language-resolution.snapshot-frozen", req.actor_ref, {"snapshot_id": snapshot_id})
        return snapshot


_store: CrossLanguageEntityToponymResolutionStore | None = None


def get_cross_language_entity_toponym_resolution_store() -> CrossLanguageEntityToponymResolutionStore:
    global _store
    if _store is None:
        _store = CrossLanguageEntityToponymResolutionStore()
    return _store
