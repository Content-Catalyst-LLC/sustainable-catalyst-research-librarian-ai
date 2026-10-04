from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading, time
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..store import store
from ..advanced_retrieval import advanced_retrieve_with_diagnostics
from ..retrieval import evidence_from_matches, retrieve_with_diagnostics
from ..provider import embeddings_configured, generate_embedding
from ..governance import source_governance
from ..platform_v7 import normalize_project
from ..services.integrated_computational_research_scientist_environment import (
    get_integrated_computational_research_scientist_environment_store,
)
from ..services.runtime_authority_wordpress_decoupling import (
    runtime_authority_manifest,
    independence_readiness,
)
from ..contracts.independent_research_librarian_api import (
    INDEPENDENT_API_SCHEMA,
    INDEPENDENT_API_ENVELOPE_SCHEMA,
    INDEPENDENT_API_SNAPSHOT_SCHEMA,
    IndependentRetrievalRequest,
    IndependentAPIContractSnapshotRequest,
)

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None; dict_row=None; Jsonb=None

API_PREFIX="/v1/research-librarian"
API_VERSION="v1"

def _json(v: Any)->str:
    return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)

def _sha(v: Any)->str:
    return hashlib.sha256(_json(v).encode()).hexdigest()

def _now()->str:
    return datetime.now(timezone.utc).isoformat()

def envelope(data: Any, *, ok: bool=True, resource: str="", meta: dict[str,Any]|None=None)->dict[str,Any]:
    return {
        "schema":INDEPENDENT_API_ENVELOPE_SCHEMA,
        "api_version":API_VERSION,
        "release":settings.release_version,
        "ok":bool(ok),
        "resource":resource,
        "data":data,
        "meta":dict(meta or {}),
    }

def api_manifest()->dict[str,Any]:
    routes=[
        {"method":"GET","path":f"{API_PREFIX}/manifest","resource":"api-manifest"},
        {"method":"GET","path":f"{API_PREFIX}/capabilities","resource":"api-capabilities"},
        {"method":"GET","path":f"{API_PREFIX}/status","resource":"service-status"},
        {"method":"POST","path":f"{API_PREFIX}/retrieve","resource":"retrieval"},
        {"method":"GET","path":f"{API_PREFIX}/projects","resource":"project-list"},
        {"method":"POST","path":f"{API_PREFIX}/projects","resource":"project"},
        {"method":"GET","path":f"{API_PREFIX}/projects/{{project_id}}","resource":"project"},
        {"method":"GET","path":f"{API_PREFIX}/projects/{{project_id}}/investigations","resource":"investigation-list"},
        {"method":"GET","path":f"{API_PREFIX}/scientist-environments/{{scientist_environment_id}}","resource":"scientist-environment"},
        {"method":"GET","path":f"{API_PREFIX}/scientist-environments/{{scientist_environment_id}}/dossier","resource":"scientist-dossier"},
        {"method":"GET","path":f"{API_PREFIX}/runtime-authority","resource":"runtime-authority"},
        {"method":"GET","path":f"{API_PREFIX}/sessions","resource":"research-session-list"},
        {"method":"POST","path":f"{API_PREFIX}/sessions","resource":"research-session"},
        {"method":"GET","path":f"{API_PREFIX}/sessions/{{session_id}}","resource":"research-session"},
        {"method":"GET","path":f"{API_PREFIX}/sessions/{{session_id}}/turns","resource":"research-session-turn-list"},
        {"method":"POST","path":f"{API_PREFIX}/sessions/{{session_id}}/turns","resource":"research-session-turn"},
        {"method":"POST","path":f"{API_PREFIX}/sessions/{{session_id}}/context","resource":"research-session-context"},
        {"method":"POST","path":f"{API_PREFIX}/sessions/{{session_id}}/state","resource":"research-session-state"},
        {"method":"POST","path":f"{API_PREFIX}/sessions/{{session_id}}/reset","resource":"research-session-reset"},
        {"method":"GET","path":f"{API_PREFIX}/sessions/{{session_id}}/summary","resource":"research-session-summary"},
        {"method":"POST","path":f"{API_PREFIX}/sessions/{{session_id}}/snapshots/freeze","resource":"research-session-snapshot"},
        {"method":"POST","path":f"{API_PREFIX}/contract-snapshots/freeze","resource":"api-contract-snapshot"},
    ]
    return {
        "schema":INDEPENDENT_API_SCHEMA,
        "api_version":API_VERSION,
        "release":settings.release_version,
        "base_path":API_PREFIX,
        "runtime_authority":"python-fastapi-backend",
        "wordpress_required":False,
        "wordpress_role":"optional-thin-adapter",
        "authentication":{
            "scheme":"backend-key-or-identity-session-v1",
            "header":"X-SC-RL-Key",
            "identity_runtime":"12.0.5",
            "identity_session_cookie":settings.identity_cookie_name,
            "browser_cookie_http_only":True,
        },
        "response_envelope":INDEPENDENT_API_ENVELOPE_SCHEMA,
        "route_count":len(routes),
        "routes":routes,
        "stability":{
            "versioned_prefix":True,
            "backward_compatible_additions_within_v1":True,
            "breaking_changes_require_new_api_version":True,
            "legacy_backend_routes_remain_supported":True,
        },
        "scope":{
            "retrieval":True,
            "projects":True,
            "investigations_read":True,
            "scientist_environment_read":True,
            "runtime_authority":True,
            "persistent_conversations":True,
            "independent_web_app":True,
            "identity_sessions":True,
            "identity_owned_research_sessions":True,
            "thin_wordpress_adapter":True,
            "wordpress_state_migration":True,
                                    },
        "next_boundary":"independent-deployment-wordpress-failure-certification",
    }

def status_payload()->dict[str,Any]:
    summary=store.summary()
    return {
        "service":"Sustainable Catalyst Research Librarian AI",
        "release":settings.release_version,
        "api_version":API_VERSION,
        "runtime_authority":"python-fastapi-backend",
        "wordpress_required":False,
        "database_backend":str(summary.get("database_backend",settings.database_backend)),
        "database_ready":bool(summary.get("database_ready",True)),
        "database_identity_match":bool(summary.get("database_identity_match",True)),
        "indexed_records":int(summary.get("total_records",0)),
        "indexed_titles":int(summary.get("indexed_titles",0)),
        "index_version":int(summary.get("index_version",0)),
        "checksum":str(summary.get("checksum","")),
        "independence_readiness":independence_readiness(),
    }

async def retrieve_payload(req: IndependentRetrievalRequest)->dict[str,Any]:
    config=store.retrieval_config()
    records=store.records()
    chunks=store.chunks()
    query_embedding=None
    semantic_error=""
    embedding_latency_ms=0.0
    embedding_status=store.embedding_status()

    if (
        req.include_semantic
        and settings.semantic_enabled
        and settings.semantic_query_embeddings
        and int(embedding_status.get("embedded_chunks",0))>0
        and embeddings_configured()
    ):
        started=time.perf_counter()
        try:
            query_embedding=await generate_embedding(req.query,"RETRIEVAL_QUERY")
        except RuntimeError as exc:
            semantic_error=str(exc)[:500]
        embedding_latency_ms=(time.perf_counter()-started)*1000

    if req.advanced:
        matches,diagnostics=advanced_retrieve_with_diagnostics(
            req.query,records,chunks,req.limit,query_embedding,config,req.filters,
            advanced_enabled=True,
            max_queries_override=req.max_queries,
            candidate_pool_override=req.candidate_pool,
        )
    else:
        matches,diagnostics=retrieve_with_diagnostics(
            req.query,records,chunks,req.limit,query_embedding,config
        )

    policy=store.governance_policy()
    matches,source_review=source_governance(matches,records,store.source_review_map(),policy)
    matches=matches[:req.limit]
    diagnostics["source_governance"]=source_review
    diagnostics["governance_policy_profile"]=policy.get("profile","")
    diagnostics["semantic_error"]=semantic_error
    diagnostics["semantic_coverage"]=embedding_status.get("semantic_coverage",0.0)
    diagnostics["embedding_latency_ms"]=round(embedding_latency_ms,3)

    data={
        "query":req.query,
        "matches":[x.model_dump() for x in matches],
        "evidence":[x.model_dump() for x in evidence_from_matches(matches)],
    }
    if req.include_diagnostics:
        data["diagnostics"]=diagnostics
    return data

def list_projects(limit:int=100,owner_ref:str="")->dict[str,Any]:
    items=store.research_projects(limit=limit,owner_ref=owner_ref)
    return {"items":items,"count":len(items),"limit":limit,"owner_ref":owner_ref}

def create_project(payload:dict[str,Any])->dict[str,Any]:
    return store.save_research_project(normalize_project(payload))

def get_project(project_id:str)->dict[str,Any]:
    project=store.research_project(project_id)
    if not project:
        raise ValueError("Research project not found.")
    return project

def project_investigations(project_id:str,limit:int=100)->dict[str,Any]:
    if not store.research_project(project_id):
        raise ValueError("Research project not found.")
    items=store.research_investigations(project_id,limit=limit)
    return {"project_id":project_id,"items":items,"count":len(items),"limit":limit}

def scientist_environment(scientist_environment_id:str)->dict[str,Any]:
    return get_integrated_computational_research_scientist_environment_store().get(scientist_environment_id)

def scientist_dossier(scientist_environment_id:str)->dict[str,Any]:
    return get_integrated_computational_research_scientist_environment_store().dossier(scientist_environment_id)

def runtime_authority_payload()->dict[str,Any]:
    return {
        "manifest":runtime_authority_manifest(),
        "independence_readiness":independence_readiness(),
    }

class IndependentAPIContractSnapshotStore:
    def __init__(self,sqlite_path:Path|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"independent_research_librarian_api.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres independent API contract storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True)
            self._migrate_sqlite()

    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
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
            c.execute("""
CREATE TABLE IF NOT EXISTS independent_api_contract_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 snapshot_hash TEXT NOT NULL,
 record_json TEXT NOT NULL,
 created_utc TEXT NOT NULL
)
""")

    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            c.execute("""
CREATE TABLE IF NOT EXISTS sc_rl_independent_api_contract_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 snapshot_hash TEXT NOT NULL,
 record JSONB NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)
""")
            c.commit()

    def freeze(self,req:IndependentAPIContractSnapshotRequest)->dict[str,Any]:
        payload={
            "schema":INDEPENDENT_API_SNAPSHOT_SCHEMA,
            "manifest":api_manifest(),
            "label":req.label,
            "note":req.note,
            "metadata":req.metadata,
            "actor_ref":req.actor_ref,
            "frozen_utc":_now(),
            "governance":{
                "snapshot-is-api-contract-record":True,
                "snapshot-does-not-create-client-identity":True,
                "snapshot-does-not-authorize-access":True,
                "wordpress-not-required":True,
            },
        }
        h=_sha(payload); sid="api-v1-"+h[:32]
        payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(
                    "INSERT INTO sc_rl_independent_api_contract_snapshots(snapshot_id,snapshot_hash,record) VALUES(%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",
                    (sid,h,Jsonb(payload)),
                ); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute(
                    "INSERT OR IGNORE INTO independent_api_contract_snapshots(snapshot_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?)",
                    (sid,h,_json(payload),payload["frozen_utc"]),
                )
        return payload

def capabilities()->dict[str,Any]:
    m=api_manifest()
    return {
        "schema":INDEPENDENT_API_SCHEMA,
        "release":settings.release_version,
        "milestone":"12.0.7",
        "api_version":"v1",
        "base_path":API_PREFIX,
        "stable_response_envelope":True,
        "direct_backend_access":True,
        "wordpress_required":False,
        "retrieval_api":True,
        "project_api":True,
        "scientist_environment_api":True,
        "runtime_authority_api":True,
        "contract_snapshots":True,
        "persistent_research_sessions":True,
        "persistent_conversations":True,
        "independent_web_app":True,
        "identity_sessions":True,
        "thin_wordpress_adapter":True,
        "wordpress_state_migration":True,
        "breaking_changes_require_new_api_version":True,
        "route_count":m["route_count"],
        "automatic_truth_promotion":False,
    }

_contract_store=None
def get_independent_api_contract_snapshot_store()->IndependentAPIContractSnapshotStore:
    global _contract_store
    if _contract_store is None:
        _contract_store=IndependentAPIContractSnapshotStore()
    return _contract_store
