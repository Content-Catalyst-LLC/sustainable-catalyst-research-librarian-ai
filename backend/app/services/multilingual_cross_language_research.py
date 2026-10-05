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
from ..contracts.multilingual_cross_language_research import *

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg = None
    dict_row = None
    Jsonb = None


def _json(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _sha(v: Any) -> str:
    return hashlib.sha256(_json(v).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, value: Any) -> str:
    return prefix + _sha(value)[:32]


def _uniq(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))


class MultilingualCrossLanguageResearchStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "multilingual_cross_language_research.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres multilingual research storage requires psycopg.")
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
CREATE TABLE IF NOT EXISTS multilingual_research_projects(
 multilingual_research_id TEXT PRIMARY KEY,
 owner_ref TEXT NOT NULL,
 record_json TEXT NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL,
 updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_multilingual_research_projects_owner
 ON multilingual_research_projects(owner_ref);
CREATE TABLE IF NOT EXISTS multilingual_research_events(
 event_id INTEGER PRIMARY KEY AUTOINCREMENT,
 multilingual_research_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 event_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_multilingual_research_events_project
 ON multilingual_research_events(multilingual_research_id);
CREATE TABLE IF NOT EXISTS multilingual_research_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 multilingual_research_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record_json TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_multilingual_research_snapshots_project
 ON multilingual_research_snapshots(multilingual_research_id);
""")

    def _migrate_postgres(self) -> None:
        with self._postgres(True) as c:
            for ddl in [
                """CREATE TABLE IF NOT EXISTS sc_rl_multilingual_research_projects(
 multilingual_research_id TEXT PRIMARY KEY,
 owner_ref TEXT NOT NULL,
 record JSONB NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_multilingual_research_projects_owner ON sc_rl_multilingual_research_projects(owner_ref)",
                """CREATE TABLE IF NOT EXISTS sc_rl_multilingual_research_events(
 event_id BIGSERIAL PRIMARY KEY,
 multilingual_research_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 payload JSONB NOT NULL,
 event_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_multilingual_research_events_project ON sc_rl_multilingual_research_events(multilingual_research_id)",
                """CREATE TABLE IF NOT EXISTS sc_rl_multilingual_research_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 multilingual_research_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record JSONB NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_multilingual_research_snapshots_project ON sc_rl_multilingual_research_snapshots(multilingual_research_id)",
            ]:
                c.execute(ddl)
            c.commit()

    def _event(self, rid: str, typ: str, actor: str, payload: dict[str, Any]) -> None:
        created = _now()
        h = _sha({
            "multilingual_research_id": rid,
            "event_type": typ,
            "actor_ref": actor,
            "payload": payload,
            "created_utc": created,
        })
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute(
                    "INSERT INTO sc_rl_multilingual_research_events(multilingual_research_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",
                    (rid, typ, actor, Jsonb(payload), h, created),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute(
                    "INSERT INTO multilingual_research_events(multilingual_research_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",
                    (rid, typ, actor, _json(payload), h, created),
                )

    def _save(self, rec: dict[str, Any]) -> dict[str, Any]:
        rec["updated_utc"] = _now()
        rec["record_hash"] = _sha({k: v for k, v in rec.items() if k != "record_hash"})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute(
                    """INSERT INTO sc_rl_multilingual_research_projects(multilingual_research_id,owner_ref,record,record_hash,created_utc,updated_utc)
VALUES(%s,%s,%s,%s,%s,%s)
ON CONFLICT(multilingual_research_id) DO UPDATE SET owner_ref=EXCLUDED.owner_ref,record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc""",
                    (
                        rec["multilingual_research_id"],
                        rec["owner_ref"],
                        Jsonb(rec),
                        rec["record_hash"],
                        rec["created_utc"],
                        rec["updated_utc"],
                    ),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute(
                    "INSERT OR REPLACE INTO multilingual_research_projects(multilingual_research_id,owner_ref,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?,?)",
                    (
                        rec["multilingual_research_id"],
                        rec["owner_ref"],
                        _json(rec),
                        rec["record_hash"],
                        rec["created_utc"],
                        rec["updated_utc"],
                    ),
                )
        return rec

    def create(self, req: MultilingualResearchCreateRequest) -> dict[str, Any]:
        body = req.model_dump()
        actor = body.pop("actor_ref")
        rid = _id("multilingual-", {**body, "owner_ref": actor})
        try:
            return self.get(rid)
        except ValueError:
            pass
        now = _now()
        rec = {
            "schema": MULTILINGUAL_RESEARCH_SCHEMA,
            "multilingual_research_id": rid,
            "owner_ref": actor,
            **body,
            "language_profiles": [],
            "source_texts": [],
            "derived_representations": [],
            "alignments": [],
            "query_plans": [],
            "retrieval_receipts": [],
            "review": {"state": "draft", "actor_ref": actor, "note": "", "updated_utc": now},
            "created_utc": now,
            "updated_utc": now,
            "governance": {
                "analyze_original_language_first": True,
                "translation_is_derived_representation": True,
                "transliteration_is_derived_representation": True,
                "every_transformation_requires_provenance": True,
                "source_language_identity_preserved": True,
                "platform_core_language_contract_authority": True,
                "automatic_translation": False,
                "automatic_transliteration": False,
                "automatic_semantic_equivalence": False,
                "automatic_entity_resolution": False,
                "automatic_citation_resolution": False,
                "automatic_evidence_resolution": False,
                "automatic_truth_promotion": False,
                "human_review_required": True,
            },
        }
        self._save(rec)
        self._event(rid, "multilingual-research.created", actor, {"project_ref": body.get("project_ref", "")})
        return self.get(rid)

    def get(self, rid: str) -> dict[str, Any]:
        if self.backend == "postgres":
            with self._postgres() as c:
                row = c.execute(
                    "SELECT record FROM sc_rl_multilingual_research_projects WHERE multilingual_research_id=%s",
                    (rid,),
                ).fetchone()
            if not row:
                raise ValueError("Multilingual research project not found.")
            return dict(row["record"])
        with self._lock, self._sqlite() as c:
            row = c.execute(
                "SELECT record_json FROM multilingual_research_projects WHERE multilingual_research_id=?",
                (rid,),
            ).fetchone()
        if not row:
            raise ValueError("Multilingual research project not found.")
        return json.loads(row["record_json"])

    def list(self, limit: int = 100, owner_ref: str = "") -> dict[str, Any]:
        limit = max(1, min(500, int(limit)))
        if self.backend == "postgres":
            with self._postgres() as c:
                if owner_ref:
                    rows = c.execute(
                        "SELECT record FROM sc_rl_multilingual_research_projects WHERE owner_ref=%s ORDER BY updated_utc DESC LIMIT %s",
                        (owner_ref, limit),
                    ).fetchall()
                else:
                    rows = c.execute(
                        "SELECT record FROM sc_rl_multilingual_research_projects ORDER BY updated_utc DESC LIMIT %s",
                        (limit,),
                    ).fetchall()
            items = [dict(r["record"]) for r in rows]
        else:
            with self._lock, self._sqlite() as c:
                if owner_ref:
                    rows = c.execute(
                        "SELECT record_json FROM multilingual_research_projects WHERE owner_ref=? ORDER BY updated_utc DESC LIMIT ?",
                        (owner_ref, limit),
                    ).fetchall()
                else:
                    rows = c.execute(
                        "SELECT record_json FROM multilingual_research_projects ORDER BY updated_utc DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
            items = [json.loads(r["record_json"]) for r in rows]
        return {"items": items, "count": len(items), "limit": limit, "owner_ref": owner_ref}

    def _append(
        self,
        rid: str,
        key: str,
        idkey: str,
        prefix: str,
        body: dict[str, Any],
        event_type: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rec = self.get(rid)
        actor = body.pop("actor_ref")
        oid = _id(prefix, body)
        item = {idkey: oid, **body, **(extra or {}), "created_utc": _now()}
        if not any(x.get(idkey) == oid for x in rec[key]):
            rec[key].append(item)
            self._save(rec)
            self._event(rid, event_type, actor, {idkey: oid})
        return self.get(rid)

    def add_language_profile(self, rid: str, req: LanguageProfileAddRequest) -> dict[str, Any]:
        body = req.model_dump()
        body["language_tag"] = body["language_tag"].strip()
        return self._append(
            rid,
            "language_profiles",
            "language_profile_id",
            "lang-",
            body,
            "language-profile.added",
            {"language_identity_is_descriptive_not_trust_score": True},
        )

    def add_source_text(self, rid: str, req: OriginalLanguageSourceTextAddRequest) -> dict[str, Any]:
        rec = self.get(rid)
        if req.language_profile_id not in {x["language_profile_id"] for x in rec["language_profiles"]}:
            raise ValueError("language_profile_id is not registered.")
        body = req.model_dump()
        body["extraction_lineage_refs"] = _uniq(body["extraction_lineage_refs"])
        return self._append(
            rid,
            "source_texts",
            "source_text_id",
            "source-text-",
            body,
            "original-language-source-text.added",
            {"original_language": True, "derived_representation": False, "source_text_preserved": True},
        )

    def add_derived_representation(self, rid: str, req: DerivedLanguageRepresentationAddRequest) -> dict[str, Any]:
        rec = self.get(rid)
        if req.source_text_id not in {x["source_text_id"] for x in rec["source_texts"]}:
            raise ValueError("source_text_id is not registered.")
        if req.target_language_profile_id not in {x["language_profile_id"] for x in rec["language_profiles"]}:
            raise ValueError("target_language_profile_id is not registered.")
        body = req.model_dump()
        body["transformation_refs"] = _uniq(body["transformation_refs"])
        return self._append(
            rid,
            "derived_representations",
            "derived_representation_id",
            "derived-",
            body,
            "derived-language-representation.added",
            {
                "derived_from_original": True,
                "source_text_remains_authoritative_representation": True,
                "semantic_equivalence_not_inferred": True,
                "transformation_provenance_preserved": True,
            },
        )

    def add_alignment(self, rid: str, req: TextAlignmentAddRequest) -> dict[str, Any]:
        rec = self.get(rid)
        if req.source_text_id not in {x["source_text_id"] for x in rec["source_texts"]}:
            raise ValueError("source_text_id is not registered.")
        derived = next(
            (x for x in rec["derived_representations"] if x["derived_representation_id"] == req.derived_representation_id),
            None,
        )
        if derived is None:
            raise ValueError("derived_representation_id is not registered.")
        if derived["source_text_id"] != req.source_text_id:
            raise ValueError("alignment source_text_id does not match derived representation lineage.")
        return self._append(
            rid,
            "alignments",
            "alignment_id",
            "alignment-",
            req.model_dump(),
            "text-alignment.added",
            {"semantic_equivalence_not_inferred": True, "alignment_is_provenance_not_truth": True},
        )

    def add_query_plan(self, rid: str, req: CrossLanguageQueryPlanAddRequest) -> dict[str, Any]:
        rec = self.get(rid)
        known = {x["language_profile_id"] for x in rec["language_profiles"]}
        missing = [x for x in [req.source_language_profile_id, *req.target_language_profile_ids] if x not in known]
        if missing:
            raise ValueError(f"query plan references unknown language profiles: {missing}")
        body = req.model_dump()
        body["target_language_profile_ids"] = _uniq(body["target_language_profile_ids"])
        body["derived_query_refs"] = _uniq(body["derived_query_refs"])
        body["representation_refs"] = _uniq(body["representation_refs"])
        return self._append(
            rid,
            "query_plans",
            "query_plan_id",
            "xquery-",
            body,
            "cross-language-query-plan.added",
            {
                "translation_execution_performed": False,
                "retrieval_execution_performed": False,
                "original_query_preserved": True,
            },
        )

    def add_retrieval_receipt(self, rid: str, req: CrossLanguageRetrievalReceiptAddRequest) -> dict[str, Any]:
        rec = self.get(rid)
        if req.query_plan_id not in {x["query_plan_id"] for x in rec["query_plans"]}:
            raise ValueError("query_plan_id is not registered.")
        known = {x["language_profile_id"] for x in rec["language_profiles"]}
        missing = [x for x in req.result_language_profile_ids if x not in known]
        if missing:
            raise ValueError(f"retrieval receipt references unknown language profiles: {missing}")
        body = req.model_dump()
        body["result_refs"] = _uniq(body["result_refs"])
        body["result_language_profile_ids"] = _uniq(body["result_language_profile_ids"])
        return self._append(
            rid,
            "retrieval_receipts",
            "retrieval_receipt_id",
            "xreceipt-",
            body,
            "cross-language-retrieval-receipt.added",
            {
                "receipt_is_observation_not_relevance_truth": True,
                "cross_language_results_require_review": True,
            },
        )

    def set_state(self, rid: str, req: MultilingualResearchStateRequest) -> dict[str, Any]:
        rec = self.get(rid)
        rec["review"] = {
            "state": req.state,
            "actor_ref": req.actor_ref,
            "note": req.note,
            "updated_utc": _now(),
        }
        self._save(rec)
        self._event(rid, "multilingual-research.state", req.actor_ref, {"state": req.state})
        return self.get(rid)

    def lineage(self, rid: str) -> dict[str, Any]:
        rec = self.get(rid)
        profile_map = {x["language_profile_id"]: x for x in rec["language_profiles"]}
        source_map = {x["source_text_id"]: x for x in rec["source_texts"]}
        return {
            "schema": MULTILINGUAL_RESEARCH_SCHEMA,
            "multilingual_research_id": rid,
            "record_hash": rec["record_hash"],
            "language_profiles": rec["language_profiles"],
            "source_texts": rec["source_texts"],
            "derived_representations": [
                {
                    **x,
                    "source_language_profile_id": source_map.get(x["source_text_id"], {}).get("language_profile_id", ""),
                    "target_language_profile": profile_map.get(x["target_language_profile_id"], {}),
                }
                for x in rec["derived_representations"]
            ],
            "alignments": rec["alignments"],
            "query_plans": rec["query_plans"],
            "retrieval_receipts": rec["retrieval_receipts"],
            "governance": {
                "original_language_precedes_derived_representations": True,
                "translation_and_transliteration_lineage_visible": True,
                "semantic_equivalence_not_inferred": True,
            },
        }

    def readiness(self, rid: str) -> dict[str, Any]:
        rec = self.get(rid)
        dims = {
            "objective_present": bool(str(rec.get("objective", "")).strip()),
            "language_profile_present": bool(rec["language_profiles"]),
            "original_language_source_present": bool(rec["source_texts"]),
            "original_language_first_policy": rec["governance"]["analyze_original_language_first"] is True,
            "transformation_provenance_policy": rec["governance"]["every_transformation_requires_provenance"] is True,
        }
        blockers = [k.replace("_", "-") for k, v in dims.items() if not v]
        return {
            "schema": MULTILINGUAL_RESEARCH_SCHEMA,
            "multilingual_research_id": rid,
            "ready_for_cross_language_research": not blockers,
            "dimensions": dims,
            "blockers": blockers,
            "governance": {"readiness_is_structural_not_translation_quality_judgment": True},
        }

    def core_candidate(self, rid: str) -> dict[str, Any]:
        rec = self.get(rid)
        return {
            "schema": "sc-research-librarian-multilingual-core-candidate/1.0",
            "multilingual_research_id": rid,
            "record_hash": rec["record_hash"],
            "language_profiles": rec["language_profiles"],
            "source_texts": rec["source_texts"],
            "derived_representations": rec["derived_representations"],
            "alignments": rec["alignments"],
            "query_plans": rec["query_plans"],
            "retrieval_receipts": rec["retrieval_receipts"],
            "platform_core_authority_required": True,
            "human_review_required": True,
            "automatic_core_write": False,
            "automatic_entity_resolution": False,
            "automatic_citation_resolution": False,
            "automatic_evidence_resolution": False,
            "automatic_truth_promotion": False,
        }

    def freeze_snapshot(self, req: MultilingualResearchSnapshotRequest) -> dict[str, Any]:
        rec = self.get(req.multilingual_research_id)
        payload = {
            "schema": MULTILINGUAL_RESEARCH_SNAPSHOT_SCHEMA,
            "multilingual_research_id": req.multilingual_research_id,
            "record": rec,
            "lineage": self.lineage(req.multilingual_research_id),
            "readiness": self.readiness(req.multilingual_research_id),
            "label": req.label,
            "note": req.note,
            "frozen_utc": _now(),
            "governance": {"snapshot_preserves_language_lineage_not_translation_quality_verdict": True},
        }
        h = _sha(payload)
        sid = "multilingualsnap-" + h[:32]
        payload.update({"snapshot_id": sid, "snapshot_hash": h})
        if self.backend == "postgres":
            with self._postgres() as c:
                c.execute(
                    "INSERT INTO sc_rl_multilingual_research_snapshots(snapshot_id,multilingual_research_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",
                    (sid, req.multilingual_research_id, h, Jsonb(payload)),
                )
                c.commit()
        else:
            with self._lock, self._sqlite() as c:
                c.execute(
                    "INSERT OR IGNORE INTO multilingual_research_snapshots(snapshot_id,multilingual_research_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",
                    (sid, req.multilingual_research_id, h, _json(payload), payload["frozen_utc"]),
                )
        self._event(
            req.multilingual_research_id,
            "snapshot.frozen",
            req.actor_ref,
            {"snapshot_id": sid, "snapshot_hash": h},
        )
        return payload


def multilingual_manifest() -> dict[str, Any]:
    return {
        "schema": MULTILINGUAL_RESEARCH_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.2.0",
        "name": "Multilingual & Cross-Language Research Intelligence",
        "runtime_authority": "python-fastapi-backend",
        "wordpress_required": False,
        "durable": True,
        "principles": {
            "analyze_original_language_first": True,
            "translation_is_derived_representation": True,
            "transliteration_is_derived_representation": True,
            "preserve_every_transformation": True,
            "preserve_language_script_variant_identity": True,
        },
        "objects": [
            "language-profile",
            "original-language-source-text",
            "derived-language-representation",
            "text-alignment",
            "cross-language-query-plan",
            "cross-language-retrieval-receipt",
            "provenance-snapshot",
        ],
        "scope": {
            "language_identity": True,
            "script_variant_identity": True,
            "translation_provenance": True,
            "transliteration_provenance": True,
            "alignment_provenance": True,
            "cross_language_query_planning": True,
            "cross_language_retrieval_receipts": True,
            "global_source_federation": False,
            "new_source_ingestion": False,
            "automatic_entity_resolution": False,
            "automatic_citation_resolution": False,
            "automatic_evidence_resolution": False,
        },
        "authority": {
            "platform_core_language_contract_authority": True,
            "librarian_research_context_authority": True,
            "source_text_original_language_preserved": True,
        },
        "governance": {
            "automatic_translation": False,
            "automatic_transliteration": False,
            "automatic_semantic_equivalence": False,
            "automatic_truth_promotion": False,
            "human_review_required": True,
        },
        "database_migration": "042_multilingual_cross_language_research_intelligence.sql",
        "next_boundary": "global-source-federation-original-language-research",
    }


def capabilities() -> dict[str, Any]:
    return {
        **multilingual_manifest(),
        "original_language_lineage": True,
        "derived_representation_lineage": True,
        "parallel_text_alignment": True,
        "cross_language_query_plans": True,
        "cross_language_retrieval_receipts": True,
        "immutable_snapshots": True,
        "core_candidates": True,
    }


_store = None


def get_multilingual_cross_language_research_store() -> MultilingualCrossLanguageResearchStore:
    global _store
    if _store is None:
        _store = MultilingualCrossLanguageResearchStore()
    return _store
