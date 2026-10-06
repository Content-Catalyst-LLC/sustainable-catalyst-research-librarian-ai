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
from ..contracts.global_source_federation_original_language import *

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


class GlobalSourceFederationOriginalLanguageStore:
    def __init__(self, sqlite_path: Path | None = None) -> None:
        self.backend = "postgres" if settings.database_backend == "postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path = sqlite_path or (settings.data_dir / "global_source_federation_original_language.sqlite3")
        self.database_schema = validate_schema_name(settings.database_schema)
        self._lock = threading.RLock()
        if self.backend == "postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres global source federation storage requires psycopg.")
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
CREATE TABLE IF NOT EXISTS global_source_federation_projects(
 federation_id TEXT PRIMARY KEY,
 owner_ref TEXT NOT NULL,
 record_json TEXT NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL,
 updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_global_source_federation_projects_owner
 ON global_source_federation_projects(owner_ref);
CREATE TABLE IF NOT EXISTS global_source_federation_events(
 event_id INTEGER PRIMARY KEY AUTOINCREMENT,
 federation_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 payload_json TEXT NOT NULL,
 event_hash TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_global_source_federation_events_project
 ON global_source_federation_events(federation_id);
CREATE TABLE IF NOT EXISTS global_source_federation_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 federation_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record_json TEXT NOT NULL,
 created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_global_source_federation_snapshots_project
 ON global_source_federation_snapshots(federation_id);
""")

    def _migrate_postgres(self) -> None:
        with self._postgres(True) as conn:
            for ddl in [
                """CREATE TABLE IF NOT EXISTS sc_rl_global_source_federation_projects(
 federation_id TEXT PRIMARY KEY,
 owner_ref TEXT NOT NULL,
 record JSONB NOT NULL,
 record_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_global_source_federation_projects_owner ON sc_rl_global_source_federation_projects(owner_ref)",
                """CREATE TABLE IF NOT EXISTS sc_rl_global_source_federation_events(
 event_id BIGSERIAL PRIMARY KEY,
 federation_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 actor_ref TEXT NOT NULL,
 payload JSONB NOT NULL,
 event_hash TEXT NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_global_source_federation_events_project ON sc_rl_global_source_federation_events(federation_id)",
                """CREATE TABLE IF NOT EXISTS sc_rl_global_source_federation_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 federation_id TEXT NOT NULL,
 snapshot_hash TEXT NOT NULL,
 record JSONB NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_global_source_federation_snapshots_project ON sc_rl_global_source_federation_snapshots(federation_id)",
            ]:
                conn.execute(ddl)
            conn.commit()

    def _event(self, federation_id: str, event_type: str, actor_ref: str, payload: dict[str, Any]) -> None:
        created = _now()
        event_hash = _sha({
            "federation_id": federation_id,
            "event_type": event_type,
            "actor_ref": actor_ref,
            "payload": payload,
            "created_utc": created,
        })
        if self.backend == "postgres":
            with self._postgres() as conn:
                conn.execute(
                    "INSERT INTO sc_rl_global_source_federation_events(federation_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",
                    (federation_id, event_type, actor_ref, Jsonb(payload), event_hash, created),
                )
                conn.commit()
        else:
            with self._lock, self._sqlite() as conn:
                conn.execute(
                    "INSERT INTO global_source_federation_events(federation_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",
                    (federation_id, event_type, actor_ref, _json(payload), event_hash, created),
                )

    def _save(self, record: dict[str, Any]) -> dict[str, Any]:
        record["updated_utc"] = _now()
        record["record_hash"] = _sha({k: v for k, v in record.items() if k != "record_hash"})
        if self.backend == "postgres":
            with self._postgres() as conn:
                conn.execute(
                    """INSERT INTO sc_rl_global_source_federation_projects(federation_id,owner_ref,record,record_hash,created_utc,updated_utc)
VALUES(%s,%s,%s,%s,%s,%s)
ON CONFLICT(federation_id) DO UPDATE SET owner_ref=EXCLUDED.owner_ref,record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc""",
                    (
                        record["federation_id"], record["owner_ref"], Jsonb(record), record["record_hash"],
                        record["created_utc"], record["updated_utc"],
                    ),
                )
                conn.commit()
        else:
            with self._lock, self._sqlite() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO global_source_federation_projects(federation_id,owner_ref,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?,?)",
                    (
                        record["federation_id"], record["owner_ref"], _json(record), record["record_hash"],
                        record["created_utc"], record["updated_utc"],
                    ),
                )
        return record

    def create(self, req: GlobalSourceFederationCreateRequest) -> dict[str, Any]:
        body = req.model_dump()
        actor_ref = body.pop("actor_ref")
        federation_id = _id("federation-", {**body, "owner_ref": actor_ref})
        try:
            return self.get(federation_id)
        except ValueError:
            pass
        now = _now()
        record = {
            "schema": GLOBAL_SOURCE_FEDERATION_SCHEMA,
            "federation_id": federation_id,
            "owner_ref": actor_ref,
            **body,
            "federated_sources": [],
            "original_language_acquisitions": [],
            "ingestion_receipts": [],
            "source_trust_preferences": [],
            "query_plans": [],
            "retrieval_receipts": [],
            "review": {"state": "draft", "actor_ref": actor_ref, "note": "", "updated_utc": now},
            "created_utc": now,
            "updated_utc": now,
            "governance": {
                "original_language_is_primary_representation": True,
                "translation_remains_derived_representation": True,
                "source_quality_separate_from_user_trust": True,
                "preserve_source_institution_jurisdiction": True,
                "preserve_acquisition_and_transformation_lineage": True,
                "knowledge_library_or_connector_ingestion_authority": True,
                "librarian_records_ingestion_receipts": True,
                "librarian_executes_arbitrary_remote_crawling": False,
                "automatic_source_trust": False,
                "automatic_entity_resolution": False,
                "automatic_toponym_resolution": False,
                "automatic_citation_resolution": False,
                "automatic_evidence_resolution": False,
                "automatic_truth_promotion": False,
                "human_review_required": True,
            },
        }
        self._save(record)
        self._event(federation_id, "global-source-federation.created", actor_ref, {"project_ref": body.get("project_ref", "")})
        return self.get(federation_id)

    def get(self, federation_id: str) -> dict[str, Any]:
        if self.backend == "postgres":
            with self._postgres() as conn:
                row = conn.execute(
                    "SELECT record FROM sc_rl_global_source_federation_projects WHERE federation_id=%s",
                    (federation_id,),
                ).fetchone()
            if not row:
                raise ValueError("Global source federation project not found.")
            return dict(row["record"])
        with self._lock, self._sqlite() as conn:
            row = conn.execute(
                "SELECT record_json FROM global_source_federation_projects WHERE federation_id=?",
                (federation_id,),
            ).fetchone()
        if not row:
            raise ValueError("Global source federation project not found.")
        return json.loads(row["record_json"])

    def list(self, limit: int = 100, owner_ref: str = "") -> dict[str, Any]:
        limit = max(1, min(500, int(limit)))
        if self.backend == "postgres":
            with self._postgres() as conn:
                if owner_ref:
                    rows = conn.execute(
                        "SELECT record FROM sc_rl_global_source_federation_projects WHERE owner_ref=%s ORDER BY updated_utc DESC LIMIT %s",
                        (owner_ref, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT record FROM sc_rl_global_source_federation_projects ORDER BY updated_utc DESC LIMIT %s",
                        (limit,),
                    ).fetchall()
            items = [dict(row["record"]) for row in rows]
        else:
            with self._lock, self._sqlite() as conn:
                if owner_ref:
                    rows = conn.execute(
                        "SELECT record_json FROM global_source_federation_projects WHERE owner_ref=? ORDER BY updated_utc DESC LIMIT ?",
                        (owner_ref, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT record_json FROM global_source_federation_projects ORDER BY updated_utc DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
            items = [json.loads(row["record_json"]) for row in rows]
        return {"items": items, "count": len(items), "limit": limit, "owner_ref": owner_ref}

    def _append(self, federation_id: str, key: str, id_key: str, prefix: str, body: dict[str, Any], event_type: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        record = self.get(federation_id)
        actor_ref = body.pop("actor_ref")
        object_id = _id(prefix, body)
        item = {id_key: object_id, **body, **(extra or {}), "created_utc": _now()}
        if not any(existing.get(id_key) == object_id for existing in record[key]):
            record[key].append(item)
            self._save(record)
            self._event(federation_id, event_type, actor_ref, {id_key: object_id})
        return self.get(federation_id)

    def add_source(self, federation_id: str, req: FederatedSourceAddRequest) -> dict[str, Any]:
        body = req.model_dump()
        body["language_profile_refs"] = _uniq(body["language_profile_refs"])
        body["collection_refs"] = _uniq(body["collection_refs"])
        return self._append(
            federation_id, "federated_sources", "federated_source_id", "fsource-", body, "federated-source.added",
            {"schema": FEDERATED_SOURCE_SCHEMA, "quality_signals_are_descriptive_not_trust": True, "user_trust_not_inferred": True},
        )

    def add_original_language_acquisition(self, federation_id: str, req: OriginalLanguageAcquisitionAddRequest) -> dict[str, Any]:
        record = self.get(federation_id)
        if req.federated_source_id not in {x["federated_source_id"] for x in record["federated_sources"]}:
            raise ValueError("federated_source_id is not registered.")
        body = req.model_dump()
        body["extraction_lineage_refs"] = _uniq(body["extraction_lineage_refs"])
        return self._append(
            federation_id, "original_language_acquisitions", "acquisition_id", "acq-", body, "original-language-acquisition.added",
            {
                "schema": ORIGINAL_LANGUAGE_ACQUISITION_SCHEMA,
                "original_language": True,
                "derived_representation": False,
                "source_content_preserved": True,
                "translation_not_substituted_for_source": True,
            },
        )

    def add_ingestion_receipt(self, federation_id: str, req: SourceIngestionReceiptAddRequest) -> dict[str, Any]:
        record = self.get(federation_id)
        if req.acquisition_id not in {x["acquisition_id"] for x in record["original_language_acquisitions"]}:
            raise ValueError("acquisition_id is not registered.")
        body = req.model_dump()
        body["transformation_refs"] = _uniq(body["transformation_refs"])
        return self._append(
            federation_id, "ingestion_receipts", "ingestion_receipt_id", "ingest-", body, "source-ingestion-receipt.added",
            {"schema": SOURCE_INGESTION_RECEIPT_SCHEMA, "receipt_is_provenance_not_quality_verdict": True, "ingestion_execution_may_be_external": True},
        )

    def set_source_trust_preference(self, federation_id: str, req: SourceTrustPreferenceAddRequest) -> dict[str, Any]:
        record = self.get(federation_id)
        if req.federated_source_id not in {x["federated_source_id"] for x in record["federated_sources"]}:
            raise ValueError("federated_source_id is not registered.")
        body = req.model_dump()
        actor_ref = body.pop("actor_ref")
        preference_id = _id("trust-", {"user_ref": body["user_ref"], "federated_source_id": body["federated_source_id"]})
        item = {
            "schema": SOURCE_TRUST_PREFERENCE_SCHEMA,
            "source_trust_preference_id": preference_id,
            **body,
            "quality_signals_unchanged": True,
            "user_preference_not_source_quality": True,
            "updated_utc": _now(),
        }
        record["source_trust_preferences"] = [
            existing for existing in record["source_trust_preferences"]
            if not (existing.get("user_ref") == body["user_ref"] and existing.get("federated_source_id") == body["federated_source_id"])
        ] + [item]
        self._save(record)
        self._event(federation_id, "source-trust-preference.set", actor_ref, {"source_trust_preference_id": preference_id, "preference": body["preference"]})
        return self.get(federation_id)

    def add_query_plan(self, federation_id: str, req: FederationQueryPlanAddRequest) -> dict[str, Any]:
        record = self.get(federation_id)
        known = {x["federated_source_id"] for x in record["federated_sources"]}
        missing = [x for x in req.target_federated_source_ids if x not in known]
        if missing:
            raise ValueError(f"query plan references unknown federated sources: {missing}")
        body = req.model_dump()
        body["target_federated_source_ids"] = _uniq(body["target_federated_source_ids"])
        body["target_language_profile_refs"] = _uniq(body["target_language_profile_refs"])
        body["derived_query_refs"] = _uniq(body["derived_query_refs"])
        return self._append(
            federation_id, "query_plans", "query_plan_id", "fquery-", body, "federation-query-plan.added",
            {"schema": FEDERATION_QUERY_PLAN_SCHEMA, "original_query_preserved": True, "remote_execution_performed_by_recording_method": False},
        )

    def add_retrieval_receipt(self, federation_id: str, req: FederationRetrievalReceiptAddRequest) -> dict[str, Any]:
        record = self.get(federation_id)
        if req.query_plan_id not in {x["query_plan_id"] for x in record["query_plans"]}:
            raise ValueError("query_plan_id is not registered.")
        known = {x["federated_source_id"] for x in record["federated_sources"]}
        missing = [x for x in req.result_federated_source_ids if x not in known]
        if missing:
            raise ValueError(f"retrieval receipt references unknown federated sources: {missing}")
        body = req.model_dump()
        body["result_refs"] = _uniq(body["result_refs"])
        body["result_federated_source_ids"] = _uniq(body["result_federated_source_ids"])
        body["result_language_profile_refs"] = _uniq(body["result_language_profile_refs"])
        return self._append(
            federation_id, "retrieval_receipts", "retrieval_receipt_id", "freceipt-", body, "federation-retrieval-receipt.added",
            {"schema": FEDERATION_RETRIEVAL_RECEIPT_SCHEMA, "receipt_is_observation_not_relevance_truth": True, "source_trust_not_inferred_from_retrieval": True},
        )

    def set_state(self, federation_id: str, req: GlobalSourceFederationStateRequest) -> dict[str, Any]:
        record = self.get(federation_id)
        record["review"] = {"state": req.state, "actor_ref": req.actor_ref, "note": req.note, "updated_utc": _now()}
        self._save(record)
        self._event(federation_id, "global-source-federation.state", req.actor_ref, {"state": req.state})
        return self.get(federation_id)

    def lineage(self, federation_id: str) -> dict[str, Any]:
        record = self.get(federation_id)
        source_map = {x["federated_source_id"]: x for x in record["federated_sources"]}
        acquisitions = [{**item, "source": source_map.get(item["federated_source_id"], {})} for item in record["original_language_acquisitions"]]
        return {
            "schema": GLOBAL_SOURCE_FEDERATION_SCHEMA,
            "federation_id": federation_id,
            "record_hash": record["record_hash"],
            "federated_sources": record["federated_sources"],
            "original_language_acquisitions": acquisitions,
            "ingestion_receipts": record["ingestion_receipts"],
            "query_plans": record["query_plans"],
            "retrieval_receipts": record["retrieval_receipts"],
            "source_quality_signals": [{"federated_source_id": x["federated_source_id"], "quality_signals": x.get("quality_signals", {})} for x in record["federated_sources"]],
            "user_trust_preferences": record["source_trust_preferences"],
            "governance": {
                "source_quality_and_user_trust_are_separate": True,
                "original_language_precedes_derived_representations": True,
                "entity_resolution_not_performed": True,
                "citation_resolution_not_performed": True,
                "evidence_resolution_not_performed": True,
            },
        }

    def readiness(self, federation_id: str) -> dict[str, Any]:
        record = self.get(federation_id)
        return {
            "schema": GLOBAL_SOURCE_FEDERATION_SCHEMA,
            "federation_id": federation_id,
            "ready_for_global_source_research": len(record["federated_sources"]) > 0,
            "source_count": len(record["federated_sources"]),
            "original_language_acquisition_count": len(record["original_language_acquisitions"]),
            "ingestion_receipt_count": len(record["ingestion_receipts"]),
            "query_plan_count": len(record["query_plans"]),
            "retrieval_receipt_count": len(record["retrieval_receipts"]),
            "trust_preference_count": len(record["source_trust_preferences"]),
            "governance": {
                "readiness_is_structural_not_source_quality_judgment": True,
                "readiness_is_not_user_trust_decision": True,
            },
        }

    def multilingual_candidate(self, federation_id: str) -> dict[str, Any]:
        record = self.get(federation_id)
        return {
            "schema": "sc-research-librarian-multilingual-federation-candidate/1.0",
            "federation_id": federation_id,
            "multilingual_research_ref": record.get("multilingual_research_ref", ""),
            "original_language_acquisition_refs": [x["acquisition_id"] for x in record["original_language_acquisitions"]],
            "language_profile_refs": _uniq([x.get("language_profile_ref", "") for x in record["original_language_acquisitions"]]),
            "automatic_multilingual_write": False,
            "automatic_translation": False,
            "automatic_alignment": False,
        }

    def core_candidate(self, federation_id: str) -> dict[str, Any]:
        record = self.get(federation_id)
        return {
            "schema": "sc-research-librarian-global-source-federation-core-candidate/1.0",
            "federation_id": federation_id,
            "source_refs": [x["source_ref"] for x in record["federated_sources"]],
            "source_ids": [x["federated_source_id"] for x in record["federated_sources"]],
            "record_hash": record["record_hash"],
            "platform_core_authority_required": True,
            "automatic_core_write": False,
            "automatic_entity_resolution": False,
            "automatic_toponym_resolution": False,
            "automatic_citation_resolution": False,
            "automatic_evidence_resolution": False,
            "automatic_truth_promotion": False,
        }

    def freeze_snapshot(self, req: GlobalSourceFederationSnapshotRequest) -> dict[str, Any]:
        record = self.get(req.federation_id)
        payload = {
            "schema": GLOBAL_SOURCE_FEDERATION_SNAPSHOT_SCHEMA,
            "federation": record,
            "lineage": self.lineage(req.federation_id),
            "readiness": self.readiness(req.federation_id),
            "label": req.label,
            "note": req.note,
            "frozen_utc": _now(),
            "governance": {
                "snapshot_preserves_source_and_language_lineage_not_truth_verdict": True,
                "snapshot_preserves_quality_trust_separation": True,
            },
        }
        snapshot_hash = _sha(payload)
        snapshot_id = "federationsnap-" + snapshot_hash[:32]
        payload.update({"snapshot_id": snapshot_id, "snapshot_hash": snapshot_hash})
        if self.backend == "postgres":
            with self._postgres() as conn:
                conn.execute(
                    "INSERT INTO sc_rl_global_source_federation_snapshots(snapshot_id,federation_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",
                    (snapshot_id, req.federation_id, snapshot_hash, Jsonb(payload)),
                )
                conn.commit()
        else:
            with self._lock, self._sqlite() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO global_source_federation_snapshots(snapshot_id,federation_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",
                    (snapshot_id, req.federation_id, snapshot_hash, _json(payload), payload["frozen_utc"]),
                )
        self._event(req.federation_id, "snapshot.frozen", req.actor_ref, {"snapshot_id": snapshot_id, "snapshot_hash": snapshot_hash})
        return payload


def federation_manifest() -> dict[str, Any]:
    return {
        "schema": GLOBAL_SOURCE_FEDERATION_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.3.0",
        "name": "Global Source Federation & Original-Language Research",
        "runtime_authority": "python-fastapi-backend",
        "wordpress_required": False,
        "durable": True,
        "principles": {
            "original_language_is_primary_representation": True,
            "translation_is_derived_representation": True,
            "source_quality_separate_from_user_trust": True,
            "preserve_institution_jurisdiction_language_identity": True,
            "preserve_acquisition_transformation_provenance": True,
        },
        "objects": [
            "federated-source", "original-language-acquisition", "source-ingestion-receipt",
            "source-trust-preference", "federation-query-plan", "federation-retrieval-receipt",
            "provenance-snapshot",
        ],
        "scope": {
            "global_source_federation": True,
            "original_language_source_research": True,
            "governed_source_ingestion": True,
            "new_source_ingestion": True,
            "source_quality_signals": True,
            "user_source_trust_preferences": True,
            "source_quality_trust_separation": True,
            "cross_language_query_planning": True,
            "federated_retrieval_receipts": True,
            "automatic_remote_crawling": False,
            "automatic_entity_resolution": False,
            "automatic_toponym_resolution": False,
            "automatic_citation_resolution": False,
            "automatic_evidence_resolution": False,
        },
        "authority": {
            "knowledge_library_or_connector_ingestion_authority": True,
            "librarian_research_context_authority": True,
            "platform_core_contract_and_provenance_authority": True,
            "source_original_language_preserved": True,
        },
        "governance": {
            "automatic_source_trust": False,
            "automatic_translation": False,
            "automatic_semantic_equivalence": False,
            "automatic_truth_promotion": False,
            "human_review_required": True,
        },
        "database_migration": "043_global_source_federation_original_language_research.sql",
        "next_boundary": "cross-language-entity-toponym-resolution",
    }


def capabilities() -> dict[str, Any]:
    return {
        **federation_manifest(),
        "global_source_registry": True,
        "original_language_acquisition_lineage": True,
        "ingestion_receipts": True,
        "source_quality_signals": True,
        "user_trust_preferences": True,
        "quality_trust_separation": True,
        "federation_query_plans": True,
        "federation_retrieval_receipts": True,
        "multilingual_candidates": True,
        "core_candidates": True,
        "immutable_snapshots": True,
    }


_store = None


def get_global_source_federation_original_language_store() -> GlobalSourceFederationOriginalLanguageStore:
    global _store
    if _store is None:
        _store = GlobalSourceFederationOriginalLanguageStore()
    return _store
