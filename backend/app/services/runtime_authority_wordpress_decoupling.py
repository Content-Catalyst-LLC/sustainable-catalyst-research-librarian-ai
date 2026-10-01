from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.runtime_authority_wordpress_decoupling import (
    RUNTIME_AUTHORITY_SCHEMA,
    RUNTIME_AUTHORITY_SNAPSHOT_SCHEMA,
    RuntimeAuthoritySnapshotRequest,
)

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None; dict_row=None; Jsonb=None

def _json(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

def _sha(v: Any) -> str:
    return hashlib.sha256(_json(v).encode()).hexdigest()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

PYTHON_RUNTIME_OWNS = [
    "service-bootstrap-and-health",
    "authenticated-research-api",
    "knowledge-index-and-retrieval-runtime",
    "research-state-and-project-runtime",
    "document-intelligence-and-source-identity",
    "durable-job-orchestration",
    "research-planning-and-intelligence-services",
    "unified-scholarly-ai-research-environment",
    "integrated-computational-research-scientist-environment",
    "wordpress-independent-persistence",
    "platform-core-client-orchestration",
]

WORDPRESS_ADAPTER_MAY_OWN = [
    "wordpress-shortcodes-and-page-embedding",
    "wordpress-admin-settings-surface",
    "wordpress-nonce-and-user-context-translation",
    "wordpress-to-backend-request-proxy",
    "legacy-wordpress-index-export-compatibility",
    "wordpress-presentation-assets",
]

WORDPRESS_MUST_NOT_OWN = [
    "canonical-research-state",
    "canonical-research-object-identity",
    "backend-job-state",
    "scientist-environment-state",
    "runtime-execution-authority",
    "platform-core-governance",
    "scientific-validity-judgment",
    "truth-promotion",
]

def runtime_authority_manifest() -> dict[str, Any]:
    return {
        "schema": RUNTIME_AUTHORITY_SCHEMA,
        "release": settings.release_version,
        "runtime_authority": "python-fastapi-backend",
        "python_runtime_authoritative": True,
        "wordpress_required_for_backend_boot": False,
        "wordpress_required_for_backend_health": False,
        "wordpress_required_for_research_api": False,
        "wordpress_required_for_persistence": False,
        "wordpress_role": "optional-thin-adapter",
        "python_runtime_owns": PYTHON_RUNTIME_OWNS,
        "wordpress_adapter_may_own": WORDPRESS_ADAPTER_MAY_OWN,
        "wordpress_must_not_own": WORDPRESS_MUST_NOT_OWN,
        "platform_core_role": "external-governance-authority-for-promoted-cross-product-objects",
        "specialist_runtime_role": "external-execution-authority-for-computation-and-experiments",
        "human_role": "researcher-controlled-interpretation-review-and-scholarly-judgment",
        "automatic_truth_promotion": False,
    }

def wordpress_adapter_contract() -> dict[str, Any]:
    return {
        "schema": "sc-research-librarian-wordpress-thin-adapter/1.0",
        "release": settings.release_version,
        "adapter_type": "optional-wordpress-interface",
        "backend_is_source_of_runtime_truth": True,
        "backend_health_source": "/health",
        "runtime_authority_source": "/v1/core/runtime-authority/manifest",
        "allowed_responsibilities": WORDPRESS_ADAPTER_MAY_OWN,
        "forbidden_responsibilities": WORDPRESS_MUST_NOT_OWN,
        "failure_behavior": {
            "wordpress_unavailable": "backend-remains-operational",
            "wordpress_proxy_failure": "surface-backend-unavailable-without-mutating-canonical-state",
            "backend_unavailable": "wordpress-may-render-interface-shell-but-must-not-claim-authoritative-runtime-success",
        },
        "compatibility": {
            "legacy_wordpress_routes_may_continue": True,
            "migration_is_incremental": True,
            "independent_web_app_target_supported": True,
        },
    }

def dependency_map() -> dict[str, Any]:
    return {
        "schema": RUNTIME_AUTHORITY_SCHEMA,
        "release": settings.release_version,
        "required_for_backend_runtime": [
            "python-3.12",
            "fastapi-service",
            "configured-persistence",
        ],
        "conditionally_required": [
            "platform-core-for-core-promotions-and-governed-cross-product-writes",
            "specialist-runtimes-for-requested-computational-execution",
            "configured-ai-provider-for-provider-backed-generation-only",
        ],
        "optional_interfaces": [
            "wordpress",
            "independent-web-app",
            "cli-or-api-client",
        ],
        "wordpress_dependency_class": "optional-interface-adapter",
        "wordpress_is_runtime_dependency": False,
    }

def independence_readiness() -> dict[str, Any]:
    manifest=runtime_authority_manifest()
    deps=dependency_map()
    checks={
        "python_runtime_authoritative": manifest["python_runtime_authoritative"] is True,
        "wordpress_not_required_for_boot": manifest["wordpress_required_for_backend_boot"] is False,
        "wordpress_not_required_for_health": manifest["wordpress_required_for_backend_health"] is False,
        "wordpress_not_required_for_api": manifest["wordpress_required_for_research_api"] is False,
        "wordpress_not_required_for_persistence": manifest["wordpress_required_for_persistence"] is False,
        "wordpress_classified_optional": deps["wordpress_dependency_class"]=="optional-interface-adapter",
        "wordpress_not_runtime_dependency": deps["wordpress_is_runtime_dependency"] is False,
        "independent_web_app_target_declared": wordpress_adapter_contract()["compatibility"]["independent_web_app_target_supported"] is True,
    }
    blockers=[k.replace("_","-") for k,v in checks.items() if not v]
    return {
        "schema": RUNTIME_AUTHORITY_SCHEMA,
        "release": settings.release_version,
        "ready_for_progressive_wordpress_decoupling": not blockers,
        "checks": checks,
        "blockers": blockers,
        "next_boundary": "independent-research-librarian-api-v1",
        "governance": {
            "readiness_certifies_architectural-dependency-separation-not-production-cutover": True,
            "wordpress-remains-supported-during-transition": True,
            "no-automatic-data-migration": True,
        },
    }

class RuntimeAuthorityCertificationStore:
    def __init__(self, sqlite_path: Path|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"runtime_authority_wordpress_decoupling.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None:
                raise RuntimeError("Postgres runtime-authority certification storage requires psycopg.")
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
    def _postgres(self,migration: bool=False)->Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row)
        c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self)->None:
        with self._lock,self._sqlite() as c:
            c.execute("""
CREATE TABLE IF NOT EXISTS runtime_authority_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 snapshot_hash TEXT NOT NULL,
 record_json TEXT NOT NULL,
 created_utc TEXT NOT NULL
)
""")

    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            c.execute("""
CREATE TABLE IF NOT EXISTS sc_rl_runtime_authority_snapshots(
 snapshot_id TEXT PRIMARY KEY,
 snapshot_hash TEXT NOT NULL,
 record JSONB NOT NULL,
 created_utc TIMESTAMPTZ NOT NULL DEFAULT now()
)
""")
            c.commit()

    def freeze_snapshot(self, req: RuntimeAuthoritySnapshotRequest)->dict[str,Any]:
        payload={
            "schema":RUNTIME_AUTHORITY_SNAPSHOT_SCHEMA,
            "manifest":runtime_authority_manifest(),
            "wordpress_adapter_contract":wordpress_adapter_contract(),
            "dependency_map":dependency_map(),
            "independence_readiness":independence_readiness(),
            "label":req.label,
            "note":req.note,
            "metadata":req.metadata,
            "actor_ref":req.actor_ref,
            "frozen_utc":_now(),
            "governance":{
                "snapshot-is-architecture-certification-not-cutover":True,
                "wordpress-remains-supported-interface":True,
                "backend-remains-authoritative":True,
            },
        }
        h=_sha(payload)
        sid="runtimeauthority-"+h[:32]
        payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute(
                    "INSERT INTO sc_rl_runtime_authority_snapshots(snapshot_id,snapshot_hash,record) VALUES(%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",
                    (sid,h,Jsonb(payload)),
                )
                c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute(
                    "INSERT OR IGNORE INTO runtime_authority_snapshots(snapshot_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?)",
                    (sid,h,_json(payload),payload["frozen_utc"]),
                )
        return payload

def capabilities()->dict[str,Any]:
    return {
        "schema":RUNTIME_AUTHORITY_SCHEMA,
        "release":settings.release_version,
        "milestone":"12.0.1",
        "durable":True,
        "python_runtime_authority":True,
        "wordpress_optional_interface":True,
        "wordpress_thin_adapter_contract":True,
        "runtime_dependency_map":True,
        "independence_readiness":True,
        "durable_certification_snapshot":True,
        "independent_web_app_target":True,
        "wordpress_required_for_backend_runtime":False,
        "automatic_data_migration":False,
        "automatic_cutover":False,
        "automatic_truth_promotion":False,
    }

_store=None
def get_runtime_authority_certification_store()->RuntimeAuthorityCertificationStore:
    global _store
    if _store is None:
        _store=RuntimeAuthorityCertificationStore()
    return _store
