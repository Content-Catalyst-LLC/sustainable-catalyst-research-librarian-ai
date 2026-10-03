from __future__ import annotations
from pathlib import Path
from typing import Any
from ..config import settings
from ..contracts.independent_web_app import (
    INDEPENDENT_WEB_APP_SCHEMA,
    INDEPENDENT_WEB_APP_RUNTIME_SCHEMA,
)

WEB_APP_PREFIX = "/research-librarian"
WEB_APP_ENTRY = f"{WEB_APP_PREFIX}/"
WEB_APP_ASSETS = f"{WEB_APP_PREFIX}/assets"
WEB_APP_ROOT = Path(__file__).resolve().parents[1] / "webapp"

def web_app_manifest() -> dict[str, Any]:
    return {
        "schema": INDEPENDENT_WEB_APP_SCHEMA,
        "runtime_schema": INDEPENDENT_WEB_APP_RUNTIME_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.0.4",
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
            "cookie_auth_used": False,
            "embedded_backend_secret": False,
            "api_key_persistence": False,
            "api_key_memory_only": True,
        },
        "authentication": {
            "mode": "operator-key-bridge",
            "header": "X-SC-RL-Key",
            "key_embedded_in_app": False,
            "key_persisted_in_browser": False,
            "production_user_identity": False,
            "identity_transition_planned": "v12.0.5",
        },
        "capabilities": {
            "service_status": True,
            "api_manifest": True,
            "retrieval": True,
            "project_browser": True,
            "persistent_session_browser": True,
            "session_creation": True,
            "turn_browser": True,
            "manual_research_notes": True,
            "source_evidence_display": True,
            "scientist_environment_linkage": True,
            "responsive_shell": True,
            "offline_error_state": True,
            "wordpress_dependency": False,
            "end_user_login": False,
        },
        "governance": {
            "web_app_is_not_runtime_authority": True,
            "web_app_does_not_promote_truth": True,
            "web_app_does_not_store_canonical_evidence": True,
            "research_operations_use_backend_contracts": True,
        },
        "next_boundary": "identity-session-access-runtime",
    }

def web_app_capabilities() -> dict[str, Any]:
    manifest = web_app_manifest()
    return {
        "schema": INDEPENDENT_WEB_APP_RUNTIME_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.0.4",
        "entry_path": manifest["entry_path"],
        "api_base": manifest["api_base"],
        "wordpress_required": False,
        "standalone_browser_shell": True,
        "persistent_backend_sessions": True,
        "browser_canonical_state": False,
        "embedded_secret": False,
        "identity_sessions": False,
    }
