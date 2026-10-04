from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
from typing import Any, Iterator
import uuid

from ..config import settings
from ..database_identity import validate_schema_name
from ..store import store as research_store
from ..platform_v7 import normalize_project
from ..contracts.persistent_research_session_conversation import (
    ResearchSessionCreateRequest,
    ResearchSessionTurnAddRequest,
)
from ..contracts.wordpress_state_migration import (
    WORDPRESS_STATE_MIGRATION_SCHEMA,
    WORDPRESS_MIGRATION_CANDIDATE_SCHEMA,
    WORDPRESS_MIGRATION_RECEIPT_SCHEMA,
    WORDPRESS_COMPATIBILITY_ALIAS_SCHEMA,
    WordPressMigrationPrepareRequest,
    WordPressMigrationApplyRequest,
)
from .persistent_research_session_conversation import get_persistent_research_session_store

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None
    dict_row=None
    Jsonb=None

SUPPORTED_TYPES=(
    "project",
    "research-context",
    "research-room",
    "library-object",
    "persistent-session",
    "persistent-turn",
    "compatibility-record",
)
APPLY_ORDER={
    "project":10,
    "library-object":20,
    "research-room":30,
    "research-context":40,
    "persistent-session":50,
    "persistent-turn":60,
    "compatibility-record":90,
}
SECRET_KEY_PATTERN=re.compile(r"(?:^|[_-])(password|passwd|secret|token|api[_-]?key|private[_-]?key|nonce)(?:$|[_-])",re.I)
IDENTITY_REF_PATTERN=re.compile(r"^identity:[A-Za-z0-9._:-]{1,220}$")

def _json(value:Any)->str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)

def _sha(value:Any)->str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()

def _now()->str:
    return datetime.now(timezone.utc).isoformat()

def _safe_slug(value:str,limit:int=48)->str:
    clean=re.sub(r"[^A-Za-z0-9._:-]+","-",str(value or "")).strip("-._:")[:limit]
    return clean or "legacy"

def _site_key(source_site:str)->str:
    return hashlib.sha256(source_site.strip().lower().encode("utf-8")).hexdigest()[:12]

def _canonical_target_id(source_site:str,source_type:str,legacy_id:str)->str:
    prefixes={
        "project":"project-wp",
        "research-context":"context-wp",
        "research-room":"room-wp",
        "library-object":"object-wp",
        "persistent-session":"session-wp",
        "persistent-turn":"turn-wp",
        "compatibility-record":"compat-wp",
    }
    digest=hashlib.sha256(f"{source_site}|{source_type}|{legacy_id}".encode("utf-8")).hexdigest()[:24]
    return f"{prefixes[source_type]}-{digest}"

def _contains_secret_key(value:Any)->bool:
    if isinstance(value,dict):
        for key,item in value.items():
            if SECRET_KEY_PATTERN.search(str(key)):
                return True
            if _contains_secret_key(item):
                return True
    elif isinstance(value,list):
        return any(_contains_secret_key(x) for x in value)
    return False

def _bounded_payload(value:dict[str,Any])->dict[str,Any]:
    encoded=_json(value)
    if len(encoded.encode("utf-8"))>262144:
        raise ValueError("Migration candidate payload exceeds 256 KiB.")
    return value

def migration_manifest()->dict[str,Any]:
    return {
        "schema":WORDPRESS_STATE_MIGRATION_SCHEMA,
        "release":settings.release_version,
        "milestone":"12.0.7",
        "name":"WordPress State Migration & Compatibility Layer",
        "runtime_authority":"python-fastapi-backend",
        "wordpress_required":False,
        "migration_mode":"explicit-prepare-apply",
        "automatic_migration":False,
        "supported_source_types":list(SUPPORTED_TYPES),
        "classification_states":[
            "migratable","duplicate","conflict","blocked-owner-map",
            "blocked-secret-bearing","unsupported"
        ],
        "idempotency":{
            "deterministic_candidate_fingerprint":True,
            "deterministic_target_ids":True,
            "durable_receipts":True,
            "durable_compatibility_aliases":True,
            "rerun_safe":True,
        },
        "governance":{
            "wordpress_is_source_not_authority":True,
            "migration_requires_explicit_apply":True,
            "conflicts_fail_closed":True,
            "secret_bearing_payloads_blocked":True,
            "legacy_state_not_deleted":True,
            "unsupported_state_retained_as_inventory_evidence":True,
            "compatibility_aliases_do_not_grant_access":True,
            "owner_mapping_is_explicit":True,
        },
        "next_boundary":"neural-research-intelligence-foundation",
    }

class WordPressStateMigrationStore:
    def __init__(self,sqlite_path:Path|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"wordpress_state_migration.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres WordPress migration storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True)
            self._migrate_sqlite()

    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None)
        c.row_factory=sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()

    @contextmanager
    def _postgres(self,migration:bool=False)->Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row)
        c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self)->None:
        with self._lock,self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS wordpress_migration_runs(
 run_id TEXT PRIMARY KEY,source_site TEXT NOT NULL,source_instance TEXT NOT NULL DEFAULT '',
 actor_ref TEXT NOT NULL DEFAULT '',inventory_hash TEXT NOT NULL,state TEXT NOT NULL,
 candidate_count INTEGER NOT NULL DEFAULT 0,migratable_count INTEGER NOT NULL DEFAULT 0,
 duplicate_count INTEGER NOT NULL DEFAULT 0,conflict_count INTEGER NOT NULL DEFAULT 0,
 blocked_count INTEGER NOT NULL DEFAULT 0,compatibility_count INTEGER NOT NULL DEFAULT 0,
 applied_count INTEGER NOT NULL DEFAULT 0,failed_count INTEGER NOT NULL DEFAULT 0,
 record_json TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wp_migration_runs_site
 ON wordpress_migration_runs(source_site,created_utc);
CREATE TABLE IF NOT EXISTS wordpress_migration_candidates(
 candidate_id TEXT PRIMARY KEY,run_id TEXT NOT NULL,source_site TEXT NOT NULL,
 source_type TEXT NOT NULL,legacy_id TEXT NOT NULL,owner_key TEXT NOT NULL DEFAULT '',
 parent_legacy_id TEXT NOT NULL DEFAULT '',fingerprint TEXT NOT NULL,
 classification TEXT NOT NULL,target_type TEXT NOT NULL DEFAULT '',
 target_id TEXT NOT NULL DEFAULT '',record_json TEXT NOT NULL,created_utc TEXT NOT NULL,
 FOREIGN KEY(run_id) REFERENCES wordpress_migration_runs(run_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_wp_migration_candidates_run
 ON wordpress_migration_candidates(run_id,classification,source_type);
CREATE INDEX IF NOT EXISTS idx_wp_migration_candidates_legacy
 ON wordpress_migration_candidates(source_site,source_type,legacy_id);
CREATE TABLE IF NOT EXISTS wordpress_migration_receipts(
 receipt_id TEXT PRIMARY KEY,run_id TEXT NOT NULL,candidate_id TEXT NOT NULL,
 source_site TEXT NOT NULL,source_type TEXT NOT NULL,legacy_id TEXT NOT NULL,
 fingerprint TEXT NOT NULL,outcome TEXT NOT NULL,target_type TEXT NOT NULL DEFAULT '',
 target_id TEXT NOT NULL DEFAULT '',record_json TEXT NOT NULL,created_utc TEXT NOT NULL,
 UNIQUE(candidate_id,fingerprint)
);
CREATE TABLE IF NOT EXISTS wordpress_compatibility_aliases(
 alias_id TEXT PRIMARY KEY,source_site TEXT NOT NULL,source_type TEXT NOT NULL,
 legacy_id TEXT NOT NULL,fingerprint TEXT NOT NULL,target_type TEXT NOT NULL,
 target_id TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,record_json TEXT NOT NULL,
 created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL,
 UNIQUE(source_site,source_type,legacy_id)
);
CREATE INDEX IF NOT EXISTS idx_wp_compat_alias_target
 ON wordpress_compatibility_aliases(target_type,target_id);
""")

    def _migrate_postgres(self)->None:
        ddl=[
"""CREATE TABLE IF NOT EXISTS sc_rl_wordpress_migration_runs(
 run_id TEXT PRIMARY KEY,source_site TEXT NOT NULL,source_instance TEXT NOT NULL DEFAULT '',
 actor_ref TEXT NOT NULL DEFAULT '',inventory_hash TEXT NOT NULL,state TEXT NOT NULL,
 candidate_count INTEGER NOT NULL DEFAULT 0,migratable_count INTEGER NOT NULL DEFAULT 0,
 duplicate_count INTEGER NOT NULL DEFAULT 0,conflict_count INTEGER NOT NULL DEFAULT 0,
 blocked_count INTEGER NOT NULL DEFAULT 0,compatibility_count INTEGER NOT NULL DEFAULT 0,
 applied_count INTEGER NOT NULL DEFAULT 0,failed_count INTEGER NOT NULL DEFAULT 0,
 record JSONB NOT NULL DEFAULT '{}'::jsonb,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())""",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_migration_runs_site ON sc_rl_wordpress_migration_runs(source_site,created_utc DESC)",
"""CREATE TABLE IF NOT EXISTS sc_rl_wordpress_migration_candidates(
 candidate_id TEXT PRIMARY KEY,run_id TEXT NOT NULL,source_site TEXT NOT NULL,
 source_type TEXT NOT NULL,legacy_id TEXT NOT NULL,owner_key TEXT NOT NULL DEFAULT '',
 parent_legacy_id TEXT NOT NULL DEFAULT '',fingerprint TEXT NOT NULL,classification TEXT NOT NULL,
 target_type TEXT NOT NULL DEFAULT '',target_id TEXT NOT NULL DEFAULT '',record JSONB NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 FOREIGN KEY(run_id) REFERENCES sc_rl_wordpress_migration_runs(run_id) ON DELETE CASCADE)""",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_migration_candidates_run ON sc_rl_wordpress_migration_candidates(run_id,classification,source_type)",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_migration_candidates_legacy ON sc_rl_wordpress_migration_candidates(source_site,source_type,legacy_id)",
"""CREATE TABLE IF NOT EXISTS sc_rl_wordpress_migration_receipts(
 receipt_id TEXT PRIMARY KEY,run_id TEXT NOT NULL,candidate_id TEXT NOT NULL,
 source_site TEXT NOT NULL,source_type TEXT NOT NULL,legacy_id TEXT NOT NULL,
 fingerprint TEXT NOT NULL,outcome TEXT NOT NULL,target_type TEXT NOT NULL DEFAULT '',
 target_id TEXT NOT NULL DEFAULT '',record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(candidate_id,fingerprint))""",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_migration_receipts_run ON sc_rl_wordpress_migration_receipts(run_id,created_utc DESC)",
"""CREATE TABLE IF NOT EXISTS sc_rl_wordpress_compatibility_aliases(
 alias_id TEXT PRIMARY KEY,source_site TEXT NOT NULL,source_type TEXT NOT NULL,
 legacy_id TEXT NOT NULL,fingerprint TEXT NOT NULL,target_type TEXT NOT NULL,target_id TEXT NOT NULL,
 active BOOLEAN NOT NULL DEFAULT TRUE,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_utc TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(source_site,source_type,legacy_id))""",
"CREATE INDEX IF NOT EXISTS idx_sc_rl_wp_compatibility_alias_target ON sc_rl_wordpress_compatibility_aliases(target_type,target_id)",
        ]
        with self._lock,self._postgres(True) as c:
            for statement in ddl:c.execute(statement)
            c.commit()

    def _alias(self,source_site:str,source_type:str,legacy_id:str)->dict[str,Any]|None:
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute(
                    "SELECT record FROM sc_rl_wordpress_compatibility_aliases WHERE source_site=%s AND source_type=%s AND legacy_id=%s AND active=TRUE",
                    (source_site,source_type,legacy_id),
                ).fetchone()
                return dict(row["record"]) if row else None
        with self._sqlite() as c:
            row=c.execute(
                "SELECT record_json FROM wordpress_compatibility_aliases WHERE source_site=? AND source_type=? AND legacy_id=? AND active=1",
                (source_site,source_type,legacy_id),
            ).fetchone()
            return json.loads(str(row["record_json"])) if row else None

    def resolve(self,source_site:str,source_type:str,legacy_id:str)->dict[str,Any]|None:
        return self._alias(source_site,source_type,legacy_id)

    def _mapped_owner(self,owner_key:str,owner_map:dict[str,str],actor_ref:str)->str:
        owner_key=str(owner_key or "")
        if owner_key and owner_key in owner_map:
            candidate=str(owner_map[owner_key])[:220]
            return candidate if IDENTITY_REF_PATTERN.fullmatch(candidate) else ""
        if not owner_key and actor_ref:
            candidate=str(actor_ref)[:220]
            return candidate if IDENTITY_REF_PATTERN.fullmatch(candidate) else ""
        return ""

    def _classification(
        self,source_site:str,source_type:str,legacy_id:str,fingerprint:str,
        owner_key:str,owner_map:dict[str,str],actor_ref:str,payload:dict[str,Any]
    )->tuple[str,str]:
        if source_type not in SUPPORTED_TYPES:
            return "unsupported","unsupported-source-type"
        if _contains_secret_key(payload):
            return "blocked-secret-bearing","secret-like-key-present"
        existing=self._alias(source_site,source_type,legacy_id)
        if existing:
            if str(existing.get("fingerprint") or "")==fingerprint:
                return "duplicate","existing-compatible-alias"
            return "conflict","existing-alias-fingerprint-differs"
        if source_type!="compatibility-record" and not self._mapped_owner(owner_key,owner_map,actor_ref):
            return "blocked-owner-map","explicit-owner-map-required"
        if source_type=="persistent-turn" and not str(payload.get("content") or "").strip():
            return "unsupported","empty-turn-content"
        return "migratable","ready"

    def prepare(self,req:WordPressMigrationPrepareRequest)->dict[str,Any]:
        source_site=req.source_site.strip()
        raw_inventory=[
            {
                "source_type":c.source_type,
                "legacy_id":c.legacy_id,
                "owner_key":c.owner_key,
                "parent_legacy_id":c.parent_legacy_id,
                "source_locator":c.source_locator,
                "payload":_bounded_payload(c.payload),
            }
            for c in req.candidates
        ]
        computed_inventory_hash=_sha(raw_inventory)
        if req.inventory_hash and req.inventory_hash!=computed_inventory_hash:
            raise ValueError("WordPress inventory hash does not match the submitted candidate inventory.")

        run_seed={
            "source_site":source_site,
            "source_instance":req.source_instance,
            "inventory_hash":computed_inventory_hash,
            "candidate_count":len(raw_inventory),
        }
        run_id="wp-migration-"+_sha(run_seed)[:32]
        now=_now()
        candidates=[]
        counts={
            "candidate_count":0,"migratable_count":0,"duplicate_count":0,
            "conflict_count":0,"blocked_count":0,"compatibility_count":0,
        }

        for item in raw_inventory:
            fp=_sha({
                "source_site":source_site,
                "source_type":item["source_type"],
                "legacy_id":item["legacy_id"],
                "owner_key":item["owner_key"],
                "parent_legacy_id":item["parent_legacy_id"],
                "payload":item["payload"],
            })
            candidate_id="wpc-"+fp[:32]
            classification,reason=self._classification(
                source_site,item["source_type"],item["legacy_id"],fp,
                item["owner_key"],req.owner_map,req.actor_ref,item["payload"]
            )
            target_id=_canonical_target_id(source_site,item["source_type"],item["legacy_id"])
            target_type=item["source_type"]
            if item["source_type"]=="persistent-turn":
                target_type="persistent-turn"
            record={
                "schema":WORDPRESS_MIGRATION_CANDIDATE_SCHEMA,
                "candidate_id":candidate_id,
                "run_id":run_id,
                "source_site":source_site,
                "source_instance":req.source_instance,
                **item,
                "fingerprint":fp,
                "classification":classification,
                "classification_reason":reason,
                "target_type":target_type,
                "target_id":target_id,
                "mapped_owner_ref":self._mapped_owner(item["owner_key"],req.owner_map,req.actor_ref),
                "prepared_utc":now,
                "governance":{
                    "explicit_apply_required":True,
                    "wordpress_is_source_not_authority":True,
                    "compatibility_alias_grants_access":False,
                },
            }
            candidates.append(record)
            counts["candidate_count"]+=1
            if classification=="migratable":counts["migratable_count"]+=1
            elif classification=="duplicate":counts["duplicate_count"]+=1
            elif classification=="conflict":counts["conflict_count"]+=1
            elif classification.startswith("blocked") or classification=="unsupported":counts["blocked_count"]+=1
            if item["source_type"]=="compatibility-record":counts["compatibility_count"]+=1

        run={
            "schema":WORDPRESS_STATE_MIGRATION_SCHEMA,
            "run_id":run_id,
            "release":settings.release_version,
            "source_site":source_site,
            "source_instance":req.source_instance,
            "actor_ref":req.actor_ref,
            "owner_map":req.owner_map,
            "inventory_hash":computed_inventory_hash,
            "state":"prepared",
            **counts,
            "applied_count":0,
            "failed_count":0,
            "note":req.note,
            "created_utc":now,
            "updated_utc":now,
            "governance":{
                "automatic_apply":False,
                "conflicts_fail_closed":True,
                "legacy_state_deleted":False,
            },
        }
        self._save_prepared(run,candidates)
        return {"run":run,"candidates":candidates}

    def _save_prepared(self,run:dict[str,Any],candidates:list[dict[str,Any]])->None:
        if self.backend=="postgres":
            with self._lock,self._postgres() as c:
                c.execute(
                    """INSERT INTO sc_rl_wordpress_migration_runs(
 run_id,source_site,source_instance,actor_ref,inventory_hash,state,candidate_count,migratable_count,
 duplicate_count,conflict_count,blocked_count,compatibility_count,applied_count,failed_count,record,
 created_utc,updated_utc)
 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
 ON CONFLICT(run_id) DO UPDATE SET record=EXCLUDED.record,updated_utc=EXCLUDED.updated_utc""",
                    (
                        run["run_id"],run["source_site"],run["source_instance"],run["actor_ref"],
                        run["inventory_hash"],run["state"],run["candidate_count"],run["migratable_count"],
                        run["duplicate_count"],run["conflict_count"],run["blocked_count"],
                        run["compatibility_count"],run["applied_count"],run["failed_count"],
                        Jsonb(run),run["created_utc"],run["updated_utc"],
                    ),
                )
                c.execute("DELETE FROM sc_rl_wordpress_migration_candidates WHERE run_id=%s",(run["run_id"],))
                for x in candidates:
                    c.execute(
                        """INSERT INTO sc_rl_wordpress_migration_candidates(
 candidate_id,run_id,source_site,source_type,legacy_id,owner_key,parent_legacy_id,fingerprint,
 classification,target_type,target_id,record,created_utc)
 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            x["candidate_id"],x["run_id"],x["source_site"],x["source_type"],x["legacy_id"],
                            x["owner_key"],x["parent_legacy_id"],x["fingerprint"],x["classification"],
                            x["target_type"],x["target_id"],Jsonb(x),x["prepared_utc"],
                        ),
                    )
                c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute(
                    """INSERT OR REPLACE INTO wordpress_migration_runs(
 run_id,source_site,source_instance,actor_ref,inventory_hash,state,candidate_count,migratable_count,
 duplicate_count,conflict_count,blocked_count,compatibility_count,applied_count,failed_count,record_json,
 created_utc,updated_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        run["run_id"],run["source_site"],run["source_instance"],run["actor_ref"],
                        run["inventory_hash"],run["state"],run["candidate_count"],run["migratable_count"],
                        run["duplicate_count"],run["conflict_count"],run["blocked_count"],
                        run["compatibility_count"],run["applied_count"],run["failed_count"],_json(run),
                        run["created_utc"],run["updated_utc"],
                    ),
                )
                c.execute("DELETE FROM wordpress_migration_candidates WHERE run_id=?",(run["run_id"],))
                for x in candidates:
                    c.execute(
                        """INSERT INTO wordpress_migration_candidates(
 candidate_id,run_id,source_site,source_type,legacy_id,owner_key,parent_legacy_id,fingerprint,
 classification,target_type,target_id,record_json,created_utc)
 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            x["candidate_id"],x["run_id"],x["source_site"],x["source_type"],x["legacy_id"],
                            x["owner_key"],x["parent_legacy_id"],x["fingerprint"],x["classification"],
                            x["target_type"],x["target_id"],_json(x),x["prepared_utc"],
                        ),
                    )

    def get_run(self,run_id:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c:
                row=c.execute("SELECT record FROM sc_rl_wordpress_migration_runs WHERE run_id=%s",(run_id,)).fetchone()
                if not row:raise ValueError("Migration run not found.")
                run=dict(row["record"])
                rows=c.execute(
                    "SELECT record FROM sc_rl_wordpress_migration_candidates WHERE run_id=%s ORDER BY source_type,legacy_id",
                    (run_id,),
                ).fetchall()
                candidates=[dict(x["record"]) for x in rows]
        else:
            with self._sqlite() as c:
                row=c.execute("SELECT record_json FROM wordpress_migration_runs WHERE run_id=?",(run_id,)).fetchone()
                if not row:raise ValueError("Migration run not found.")
                run=json.loads(str(row["record_json"]))
                rows=c.execute(
                    "SELECT record_json FROM wordpress_migration_candidates WHERE run_id=? ORDER BY source_type,legacy_id",
                    (run_id,),
                ).fetchall()
                candidates=[json.loads(str(x["record_json"])) for x in rows]
        return {"run":run,"candidates":candidates}

    def _resolve_target(self,source_site:str,source_type:str,legacy_id:str)->str:
        alias=self._alias(source_site,source_type,legacy_id)
        return str(alias.get("target_id") or "") if alias else ""

    def _map_reference(self,source_site:str,source_type:str,value:str)->str:
        raw=str(value or "")
        if not raw:return ""
        return self._resolve_target(source_site,source_type,raw) or raw

    def _apply_candidate(self,x:dict[str,Any])->tuple[str,str]:
        source_site=x["source_site"]
        source_type=x["source_type"]
        target_id=x["target_id"]
        owner_ref=x.get("mapped_owner_ref") or ""
        payload=dict(x.get("payload") or {})
        provenance={
            "migration_schema":WORDPRESS_STATE_MIGRATION_SCHEMA,
            "source_site":source_site,
            "source_locator":x.get("source_locator") or "",
            "legacy_id":x["legacy_id"],
            "source_fingerprint":x["fingerprint"],
            "migrated_utc":_now(),
        }

        if source_type=="project":
            source=dict(payload)
            source["project_id"]=target_id
            source["owner_ref"]=owner_ref
            source["governance"]={
                **(source.get("governance") if isinstance(source.get("governance"),dict) else {}),
                "wordpress_migration":provenance,
                "wordpress_is_not_authority":True,
            }
            project=normalize_project(source)
            research_store.save_research_project(project)
            return "project",str(project["project_id"])

        if source_type=="library-object":
            now=_now()
            obj={
                **payload,
                "object_id":target_id,
                "owner_ref":owner_ref,
                "created_utc":str(payload.get("created_utc") or now),
                "updated_utc":now,
                "provenance":{
                    **(payload.get("provenance") if isinstance(payload.get("provenance"),dict) else {}),
                    "wordpress_migration":provenance,
                },
            }
            obj["fingerprint"]=_sha({k:v for k,v in obj.items() if k!="fingerprint"})
            research_store.save_library_object(obj)
            return "library-object",target_id

        if source_type=="research-room":
            now=_now()
            room={
                **payload,
                "room_id":target_id,
                "owner_ref":owner_ref,
                "project_id":self._map_reference(source_site,"project",str(payload.get("project_id") or "")),
                "created_utc":str(payload.get("created_utc") or now),
                "updated_utc":now,
                "migration_provenance":provenance,
            }
            room["fingerprint"]=_sha({k:v for k,v in room.items() if k!="fingerprint"})
            research_store.save_research_room(room)
            return "research-room",target_id

        if source_type=="research-context":
            now=_now()
            context={
                **payload,
                "context_id":target_id,
                "owner_ref":owner_ref,
                "project_id":self._map_reference(source_site,"project",str(payload.get("project_id") or "")),
                "room_id":self._map_reference(source_site,"research-room",str(payload.get("room_id") or "")),
                "created_utc":str(payload.get("created_utc") or now),
                "updated_utc":now,
                "migration_provenance":provenance,
            }
            context["fingerprint"]=_sha({k:v for k,v in context.items() if k!="fingerprint"})
            research_store.save_research_context(context)
            return "research-context",target_id

        if source_type=="persistent-session":
            session_store=get_persistent_research_session_store()
            req=ResearchSessionCreateRequest(
                title=str(payload.get("title") or "Migrated WordPress research session")[:500],
                client_ref=owner_ref,
                project_id=self._map_reference(source_site,"project",str(payload.get("project_id") or "")),
                scientist_environment_id=str(payload.get("scientist_environment_id") or "")[:255],
                research_context_ref=self._map_reference(source_site,"research-context",str(payload.get("research_context_ref") or "")),
                metadata={
                    **(payload.get("metadata") if isinstance(payload.get("metadata"),dict) else {}),
                    "wordpress_migration":provenance,
                },
            )
            session=session_store.create(req,requested_session_id=target_id)
            return "persistent-session",str(session["session_id"])

        if source_type=="persistent-turn":
            if not x.get("parent_legacy_id"):
                raise ValueError("Persistent-turn migration requires parent_legacy_id.")
            session_id=self._resolve_target(source_site,"persistent-session",x["parent_legacy_id"])
            if not session_id:
                raise ValueError("Parent persistent session has not been migrated.")
            role=str(payload.get("role") or "research-note")
            if role not in {"user","assistant","system","tool","research-note"}:
                role="research-note"
            req=ResearchSessionTurnAddRequest(
                role=role,
                content=str(payload.get("content") or "")[:100000],
                source_refs=[str(v)[:2000] for v in (payload.get("source_refs") or [])][:5000],
                evidence_refs=[str(v)[:2000] for v in (payload.get("evidence_refs") or [])][:5000],
                artifact_refs=[str(v)[:2000] for v in (payload.get("artifact_refs") or [])][:5000],
                answer_trace_ref=str(payload.get("answer_trace_ref") or "")[:2000],
                provider=str(payload.get("provider") or "")[:255],
                model=str(payload.get("model") or "")[:255],
                provenance={
                    **(payload.get("provenance") if isinstance(payload.get("provenance"),dict) else {}),
                    "wordpress_migration":provenance,
                },
                metadata=payload.get("metadata") if isinstance(payload.get("metadata"),dict) else {},
            )
            turn=get_persistent_research_session_store().add_turn(
                session_id,req,requested_turn_id=target_id
            )
            return "persistent-turn",str(turn["turn_id"])

        if source_type=="compatibility-record":
            return "compatibility-record",target_id

        raise ValueError("Unsupported migration candidate type.")

    def _save_alias_and_receipt(
        self,x:dict[str,Any],run_id:str,outcome:str,target_type:str,target_id:str,note:str=""
    )->dict[str,Any]:
        now=_now()
        alias_id="wpa-"+_sha([x["source_site"],x["source_type"],x["legacy_id"]])[:32]
        alias={
            "schema":WORDPRESS_COMPATIBILITY_ALIAS_SCHEMA,
            "alias_id":alias_id,
            "source_site":x["source_site"],
            "source_type":x["source_type"],
            "legacy_id":x["legacy_id"],
            "fingerprint":x["fingerprint"],
            "target_type":target_type,
            "target_id":target_id,
            "active":True,
            "created_utc":now,
            "updated_utc":now,
            "governance":{
                "alias_grants_access":False,
                "alias_is_not_identity":True,
                "wordpress_is_not_authority":True,
            },
        }
        receipt_id="wpr-"+_sha([run_id,x["candidate_id"],x["fingerprint"],target_id])[:32]
        receipt={
            "schema":WORDPRESS_MIGRATION_RECEIPT_SCHEMA,
            "receipt_id":receipt_id,
            "run_id":run_id,
            "candidate_id":x["candidate_id"],
            "source_site":x["source_site"],
            "source_type":x["source_type"],
            "legacy_id":x["legacy_id"],
            "fingerprint":x["fingerprint"],
            "outcome":outcome,
            "target_type":target_type,
            "target_id":target_id,
            "note":note,
            "created_utc":now,
        }
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(
                    """INSERT INTO sc_rl_wordpress_compatibility_aliases(
 alias_id,source_site,source_type,legacy_id,fingerprint,target_type,target_id,active,record,created_utc,updated_utc)
 VALUES(%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s,%s)
 ON CONFLICT(source_site,source_type,legacy_id) DO UPDATE SET
 fingerprint=EXCLUDED.fingerprint,target_type=EXCLUDED.target_type,target_id=EXCLUDED.target_id,
 active=TRUE,record=EXCLUDED.record,updated_utc=EXCLUDED.updated_utc""",
                    (
                        alias_id,alias["source_site"],alias["source_type"],alias["legacy_id"],
                        alias["fingerprint"],alias["target_type"],alias["target_id"],Jsonb(alias),now,now,
                    ),
                )
                c.execute(
                    """INSERT INTO sc_rl_wordpress_migration_receipts(
 receipt_id,run_id,candidate_id,source_site,source_type,legacy_id,fingerprint,outcome,
 target_type,target_id,record,created_utc)
 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
 ON CONFLICT(candidate_id,fingerprint) DO NOTHING""",
                    (
                        receipt_id,run_id,x["candidate_id"],x["source_site"],x["source_type"],x["legacy_id"],
                        x["fingerprint"],outcome,target_type,target_id,Jsonb(receipt),now,
                    ),
                )
                c.commit()
        else:
            with self._sqlite() as c:
                c.execute(
                    """INSERT INTO wordpress_compatibility_aliases(
 alias_id,source_site,source_type,legacy_id,fingerprint,target_type,target_id,active,record_json,created_utc,updated_utc)
 VALUES(?,?,?,?,?,?,?,1,?,?,?)
 ON CONFLICT(source_site,source_type,legacy_id) DO UPDATE SET
 fingerprint=excluded.fingerprint,target_type=excluded.target_type,target_id=excluded.target_id,
 active=1,record_json=excluded.record_json,updated_utc=excluded.updated_utc""",
                    (
                        alias_id,alias["source_site"],alias["source_type"],alias["legacy_id"],
                        alias["fingerprint"],alias["target_type"],alias["target_id"],_json(alias),now,now,
                    ),
                )
                c.execute(
                    """INSERT OR IGNORE INTO wordpress_migration_receipts(
 receipt_id,run_id,candidate_id,source_site,source_type,legacy_id,fingerprint,outcome,
 target_type,target_id,record_json,created_utc) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        receipt_id,run_id,x["candidate_id"],x["source_site"],x["source_type"],x["legacy_id"],
                        x["fingerprint"],outcome,target_type,target_id,_json(receipt),now,
                    ),
                )
        return receipt

    def apply(self,run_id:str,req:WordPressMigrationApplyRequest)->dict[str,Any]:
        if not req.confirm:
            raise ValueError("Migration apply requires confirm=true.")
        bundle=self.get_run(run_id)
        run=bundle["run"]
        if int(run.get("conflict_count") or 0)>0:
            raise ValueError("Migration run contains conflicts and cannot be applied until re-prepared.")
        selected=set(req.candidate_ids or [])
        candidates=[
            x for x in bundle["candidates"]
            if x.get("classification") in {"migratable","duplicate"}
            and (not selected or x["candidate_id"] in selected)
        ]
        candidates.sort(key=lambda x:(APPLY_ORDER.get(x["source_type"],999),x["legacy_id"]))
        receipts=[]
        failures=[]
        for x in candidates:
            existing=self._alias(x["source_site"],x["source_type"],x["legacy_id"])
            if existing and str(existing.get("fingerprint") or "")==x["fingerprint"]:
                receipts.append(
                    self._save_alias_and_receipt(
                        x,run_id,"duplicate-idempotent",
                        str(existing.get("target_type") or x["target_type"]),
                        str(existing.get("target_id") or x["target_id"]),
                        req.note,
                    )
                )
                continue
            try:
                target_type,target_id=self._apply_candidate(x)
                receipts.append(self._save_alias_and_receipt(x,run_id,"applied",target_type,target_id,req.note))
            except Exception as exc:
                failures.append({
                    "candidate_id":x["candidate_id"],
                    "source_type":x["source_type"],
                    "legacy_id":x["legacy_id"],
                    "error":str(exc)[:1000],
                })

        final_state="applied-with-failures" if failures else (
            "applied-with-blocked" if int(run.get("blocked_count") or 0)>0 else "applied"
        )
        updated={
            **run,
            "state":final_state,
            "applied_count":len(receipts),
            "failed_count":len(failures),
            "updated_utc":_now(),
            "apply_note":req.note,
            "legacy_state_deleted":False,
        }
        self._update_run(updated)
        return {"run":updated,"receipts":receipts,"failures":failures}

    def _update_run(self,run:dict[str,Any])->None:
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(
                    """UPDATE sc_rl_wordpress_migration_runs SET state=%s,applied_count=%s,failed_count=%s,
 record=%s,updated_utc=%s WHERE run_id=%s""",
                    (
                        run["state"],run["applied_count"],run["failed_count"],Jsonb(run),
                        run["updated_utc"],run["run_id"],
                    ),
                );c.commit()
        else:
            with self._sqlite() as c:
                c.execute(
                    """UPDATE wordpress_migration_runs SET state=?,applied_count=?,failed_count=?,
 record_json=?,updated_utc=? WHERE run_id=?""",
                    (
                        run["state"],run["applied_count"],run["failed_count"],_json(run),
                        run["updated_utc"],run["run_id"],
                    ),
                )

    def recent_runs(self,source_site:str="",limit:int=50)->list[dict[str,Any]]:
        limit=max(1,min(200,int(limit)))
        if self.backend=="postgres":
            with self._postgres() as c:
                if source_site:
                    rows=c.execute(
                        "SELECT record FROM sc_rl_wordpress_migration_runs WHERE source_site=%s ORDER BY created_utc DESC LIMIT %s",
                        (source_site,limit),
                    ).fetchall()
                else:
                    rows=c.execute(
                        "SELECT record FROM sc_rl_wordpress_migration_runs ORDER BY created_utc DESC LIMIT %s",
                        (limit,),
                    ).fetchall()
                return [dict(x["record"]) for x in rows]
        with self._sqlite() as c:
            if source_site:
                rows=c.execute(
                    "SELECT record_json FROM wordpress_migration_runs WHERE source_site=? ORDER BY created_utc DESC LIMIT ?",
                    (source_site,limit),
                ).fetchall()
            else:
                rows=c.execute(
                    "SELECT record_json FROM wordpress_migration_runs ORDER BY created_utc DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [json.loads(str(x["record_json"])) for x in rows]

    def capabilities(self)->dict[str,Any]:
        return {
            **migration_manifest(),
            "backend":self.backend,
            "receipt_store":"durable",
            "alias_store":"durable",
            "migration_table_version":"040",
        }

_STORE:WordPressStateMigrationStore|None=None
_STORE_LOCK=threading.Lock()

def get_wordpress_state_migration_store()->WordPressStateMigrationStore:
    global _STORE
    if _STORE is None:
        with _STORE_LOCK:
            if _STORE is None:_STORE=WordPressStateMigrationStore()
    return _STORE
