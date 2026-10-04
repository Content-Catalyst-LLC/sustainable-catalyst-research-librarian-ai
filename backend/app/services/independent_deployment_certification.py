from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from ..config import settings
from ..store import store
from ..contracts.independent_deployment_certification import (
    INDEPENDENT_DEPLOYMENT_CERTIFICATION_SCHEMA,
    INDEPENDENT_DEPLOYMENT_REPORT_SCHEMA,
)
from .identity_session_access import get_identity_session_store
from .persistent_research_session_conversation import get_persistent_research_session_store
from .wordpress_state_migration import get_wordpress_state_migration_store, migration_manifest
from .independent_research_librarian_api import api_manifest, capabilities
from .independent_web_app import WEB_APP_ROOT, web_app_manifest
from .thin_wordpress_adapter import thin_wordpress_adapter_manifest

REQUIRED_INDEPENDENT_ROUTES=(
    "/health",
    "/research-librarian/",
    "/research-librarian/app-manifest.json",
    "/v1/research-librarian/manifest",
    "/v1/research-librarian/capabilities",
    "/v1/research-librarian/status",
    "/v1/research-librarian/retrieve",
    "/v1/research-librarian/projects",
    "/v1/research-librarian/sessions",
    "/v1/research-librarian/auth/manifest",
    "/v1/research-librarian/auth/login",
    "/v1/research-librarian/wordpress-migration/manifest",
    "/v1/research-librarian/wordpress-migration/resolve",
    "/v1/research-librarian/independence/manifest",
    "/v1/research-librarian/independence/report",
)

def _now()->str:
    return datetime.now(timezone.utc).isoformat()

def _json(value:Any)->str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)

def _sha(value:Any)->str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()

def certification_manifest()->dict[str,Any]:
    return {
        "schema":INDEPENDENT_DEPLOYMENT_CERTIFICATION_SCHEMA,
        "release":settings.release_version,
        "milestone":"12.0.8",
        "name":"Independent Deployment & WordPress-Failure Certification",
        "runtime_authority":"python-fastapi-backend",
        "wordpress_required":False,
        "certification_target":"wordpress-unreachable-or-absent",
        "certification_scope":[
            "service-health",
            "independent-api-v1",
            "independent-web-app",
            "backend-identity-and-session-authority",
            "persistent-research-sessions",
            "project-and-retrieval-api-surface",
            "wordpress-migration-ledger-continuity",
            "compatibility-alias-continuity",
            "thin-wordpress-adapter-fail-closed-semantics",
        ],
        "non_targets":[
            "postgres-failure",
            "platform-core-failure",
            "internet-provider-failure",
            "external-federated-provider-failure",
        ],
        "database_migration":None,
        "wordpress_adapter_policy":{
            "adapter_optional":True,
            "backend_does_not_call_wordpress_for_independent_operations":True,
            "adapter_failure_does_not_create_local_wordpress_research_authority":True,
            "adapter_failure_behavior":"fail-closed-no-wordpress-research-fallback",
        },
        "certification_method":{
            "static_contract_checks":True,
            "runtime_route_checks":True,
            "backend_store_readiness_checks":True,
            "web_app_asset_checks":True,
            "wordpress_dns_blackout_probe":True,
            "production_deploy_verifier":True,
            "certificate_fingerprint":True,
        },
        "governance":{
            "certification_does_not_modify_research_state":True,
            "certification_does_not_delete_legacy_wordpress_state":True,
            "certification_does_not_grant_access":True,
            "wordpress_remains_optional_compatibility_surface":True,
        },
        "next_boundary":"neural-research-intelligence-foundation",
    }

def _check(check_id:str,passed:bool,detail:str,critical:bool=True)->dict[str,Any]:
    return {
        "check_id":check_id,
        "passed":bool(passed),
        "critical":bool(critical),
        "detail":str(detail)[:2000],
    }

def certification_report(route_paths:set[str]|None=None)->dict[str,Any]:
    summary=store.summary()
    api=api_manifest()
    caps=capabilities()
    web=web_app_manifest()
    wp=thin_wordpress_adapter_manifest()
    migration=migration_manifest()
    identity=get_identity_session_store()
    sessions=get_persistent_research_session_store()
    migration_store=get_wordpress_state_migration_store()

    checks:list[dict[str,Any]]=[]

    checks.append(_check(
        "runtime-authority",
        api.get("runtime_authority")=="python-fastapi-backend",
        f"runtime_authority={api.get('runtime_authority','')}",
    ))
    checks.append(_check(
        "wordpress-not-required",
        api.get("wordpress_required") is False
        and web.get("wordpress_required") is False
        and migration.get("wordpress_required") is False,
        "Independent API, web app, and migration runtime all declare WordPress optional.",
    ))
    checks.append(_check(
        "database-ready",
        bool(summary.get("database_ready",True)) and bool(summary.get("database_identity_match",True)),
        f"backend={summary.get('database_backend',settings.database_backend)} identity_match={summary.get('database_identity_match',True)}",
    ))
    checks.append(_check(
        "identity-runtime",
        hasattr(identity,"identity_count"),
        f"identity_count={identity.identity_count()}",
    ))
    checks.append(_check(
        "persistent-session-runtime",
        getattr(sessions,"backend","") in {"postgres","sqlite"},
        f"session_backend={getattr(sessions,'backend','unknown')}",
    ))
    checks.append(_check(
        "migration-ledger-continuity",
        getattr(migration_store,"backend","") in {"postgres","sqlite"},
        f"migration_backend={getattr(migration_store,'backend','unknown')}",
    ))
    checks.append(_check(
        "web-app-assets",
        all((WEB_APP_ROOT/name).is_file() for name in ("index.html","app.css","app.js")),
        f"web_app_root={WEB_APP_ROOT}",
    ))
    checks.append(_check(
        "browser-secret-boundary",
        bool(web.get("authentication",{}).get("backend_api_key_embedded") is False)
        and bool(web.get("browser_state_policy",{}).get("embedded_backend_secret") is False),
        "Independent web app does not embed the backend integration key.",
    ))
    checks.append(_check(
        "thin-adapter-fail-closed",
        wp.get("proxy_policy",{}).get("backend_failure_behavior")=="fail-closed-no-wordpress-research-fallback"
        and wp.get("wordpress_runtime_authority") is False,
        str(wp.get("proxy_policy",{}).get("backend_failure_behavior","")),
    ))
    checks.append(_check(
        "migration-source-not-authority",
        migration.get("governance",{}).get("wordpress_is_source_not_authority") is True
        and migration.get("governance",{}).get("legacy_state_not_deleted") is True,
        "Migration compatibility preserves source evidence without restoring WordPress authority.",
    ))
    checks.append(_check(
        "independent-api-capability",
        caps.get("direct_backend_access") is True
        and caps.get("identity_sessions") is True
        and caps.get("persistent_research_sessions") is True,
        "Independent API exposes direct backend access, identity sessions, and persistent sessions.",
    ))

    if route_paths is not None:
        missing=sorted(set(REQUIRED_INDEPENDENT_ROUTES)-set(route_paths))
        checks.append(_check(
            "independent-route-surface",
            not missing,
            "all required routes present" if not missing else "missing="+",".join(missing),
        ))
    else:
        checks.append(_check(
            "independent-route-surface",
            True,
            "Route registration is evaluated by API/runtime deployment verifier.",
            critical=False,
        ))

    critical=[c for c in checks if c["critical"]]
    certified=all(c["passed"] for c in critical)
    report={
        "schema":INDEPENDENT_DEPLOYMENT_REPORT_SCHEMA,
        "release":settings.release_version,
        "milestone":"12.0.8",
        "certified":certified,
        "certification_target":"wordpress-unreachable-or-absent",
        "wordpress_required":False,
        "runtime_authority":"python-fastapi-backend",
        "database_backend":str(summary.get("database_backend",settings.database_backend)),
        "checks":checks,
        "check_count":len(checks),
        "critical_check_count":len(critical),
        "passed_count":sum(1 for c in checks if c["passed"]),
        "failed_count":sum(1 for c in checks if not c["passed"]),
        "generated_utc":_now(),
        "governance":{
            "read_only_certification":True,
            "research_state_modified":False,
            "legacy_wordpress_state_modified":False,
            "access_granted":False,
        },
        "next_boundary":"neural-research-intelligence-foundation",
    }
    fingerprint_payload={k:v for k,v in report.items() if k not in {"generated_utc","certificate_fingerprint"}}
    report["certificate_fingerprint"]=_sha(fingerprint_payload)
    return report
