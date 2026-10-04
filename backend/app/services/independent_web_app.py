from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import settings

WEB_APP_SCHEMA = "sc-research-librarian-independent-web-app/1.1"
WEB_APP_RUNTIME_SCHEMA = "sc-research-librarian-independent-web-app-runtime/1.1"

WEB_APP_PREFIX = "/research-librarian"
WEB_APP_ENTRY = f"{WEB_APP_PREFIX}/"
WEB_APP_ASSETS = f"{WEB_APP_PREFIX}/assets"
WEB_APP_ROOT = Path(__file__).resolve().parents[1] / "webapp"

def web_app_manifest() -> dict[str, Any]:
    return {
        "schema": WEB_APP_SCHEMA,
        "runtime_schema": WEB_APP_RUNTIME_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.0.6",
        "name": "Sustainable Catalyst Research Librarian",
        "entry_path": WEB_APP_ENTRY,
        "asset_path": WEB_APP_ASSETS,
        "api_base": "/v1/research-librarian",
        "health_path": "/health",
        "runtime_authority": "python-fastapi-backend",
        "wordpress_required": False,
        "canonical_state_location": "python-postgres-backend",
        "browser_state_policy": {
            "canonical_research_state_in_browser": False,
            "local_storage_used": False,
            "session_storage_used": False,
            "embedded_backend_secret": False,
            "backend_api_key_used_by_web_app": False,
            "identity_cookie_http_only": True,
            "identity_cookie_same_site": "strict",
            "identity_cookie_secure": bool(settings.identity_cookie_secure),
        },
        "authentication": {
            "mode": "backend-identity-session",
            "login_path": "/v1/research-librarian/auth/login",
            "logout_path": "/v1/research-librarian/auth/logout",
            "me_path": "/v1/research-librarian/auth/me",
            "cookie_name": settings.identity_cookie_name,
            "cookie_http_only": True,
            "cookie_same_site": "strict",
            "backend_api_key_embedded": False,
            "key_embedded_in_app": False,
            "production_user_identity": True,
            "role_based_access": True,
        },
        "capabilities": {
            "service_status": True,
            "api_manifest": True,
            "retrieval": True,
            "project_browser": True,
            "persistent_session_browser": True,
            "identity_owned_sessions": True,
            "session_creation": True,
            "turn_browser": True,
            "manual_research_notes": True,
            "source_evidence_display": True,
            "scientist_environment_linkage": True,
            "responsive_shell": True,
            "offline_error_state": True,
            "wordpress_dependency": False,
            "end_user_login": True,
            "session_revocation": True,
        },
        "governance": {
            "web_app_is_not_runtime_authority": True,
            "web_app_is_not_identity_authority": True,
            "backend_is_identity_authority": True,
            "web_app_does_not_promote_truth": True,
            "web_app_does_not_store_canonical_evidence": True,
            "research_operations_use_backend_contracts": True,
        },
        "next_boundary": "wordpress-state-migration-compatibility-layer",
    }

def web_app_capabilities() -> dict[str, Any]:
    m=web_app_manifest()
    return {
        "schema": WEB_APP_RUNTIME_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.0.6",
        "entry_path": m["entry_path"],
        "api_base": m["api_base"],
        "wordpress_required": False,
        "standalone_browser_shell": True,
        "persistent_backend_sessions": True,
        "identity_sessions": True,
        "identity_owned_research_sessions": True,
        "browser_canonical_state": False,
        "embedded_secret": False,
        "backend_api_key_used_by_web_app": False,
    }
