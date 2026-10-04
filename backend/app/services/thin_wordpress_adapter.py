from __future__ import annotations

from typing import Any

from ..config import settings
from ..contracts.thin_wordpress_adapter import (
    ALL_OPERATIONS,
    READ_OPERATIONS,
    WRITE_OPERATIONS,
    THIN_WORDPRESS_ADAPTER_SCHEMA,
    THIN_WORDPRESS_ADAPTER_CONTEXT_SCHEMA,
)

def thin_wordpress_adapter_manifest() -> dict[str, Any]:
    return {
        "schema": THIN_WORDPRESS_ADAPTER_SCHEMA,
        "actor_context_schema": THIN_WORDPRESS_ADAPTER_CONTEXT_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.0.6",
        "adapter_type": "optional-wordpress-presentation-proxy",
        "backend_authoritative": True,
        "wordpress_required": False,
        "wordpress_runtime_authority": False,
        "wordpress_identity_authority": False,
        "wordpress_session_authority": False,
        "wordpress_canonical_research_state": False,
        "wordpress_canonical_conversation_state": False,
        "wordpress_canonical_project_state": False,
        "wordpress_canonical_evidence_state": False,
        "backend_authentication": "server-side-integration-key",
        "browser_backend_key_exposure": False,
        "wordpress_actor_context": "provenance-hint-not-backend-identity",
        "proxy_policy": {
            "arbitrary_paths_allowed": False,
            "arbitrary_hosts_allowed": False,
            "arbitrary_methods_allowed": False,
            "fixed_operation_allowlist": True,
            "read_operations": list(READ_OPERATIONS),
            "write_operations": list(WRITE_OPERATIONS),
            "all_operations": list(ALL_OPERATIONS),
            "backend_failure_behavior": "fail-closed-no-wordpress-research-fallback",
        },
        "wordpress_storage_policy": {
            "connection_configuration_only": True,
            "canonical_research_state": False,
            "canonical_sessions": False,
            "canonical_turns": False,
            "canonical_projects": False,
            "canonical_evidence": False,
        },
        "next_boundary": "wordpress-state-migration-compatibility-layer",
    }

def thin_wordpress_adapter_capabilities() -> dict[str, Any]:
    m=thin_wordpress_adapter_manifest()
    return {
        "schema": THIN_WORDPRESS_ADAPTER_SCHEMA,
        "release": settings.release_version,
        "milestone": "12.0.6",
        "enabled": True,
        "wordpress_required": False,
        "backend_authoritative": True,
        "fixed_operation_allowlist": True,
        "operation_count": len(ALL_OPERATIONS),
        "read_operation_count": len(READ_OPERATIONS),
        "write_operation_count": len(WRITE_OPERATIONS),
        "backend_failure_behavior": m["proxy_policy"]["backend_failure_behavior"],
        "next_boundary": m["next_boundary"],
    }
