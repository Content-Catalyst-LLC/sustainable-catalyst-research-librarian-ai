from __future__ import annotations

"""Fail-closed Postgres configuration and database identity helpers.

No secret values are exposed. The connection fingerprint is derived only from
endpoint, database, role, schema, and the Neon branch/project identifiers that
Postgres makes available at runtime.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit


_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_schema_name(value: str) -> str:
    schema = (value or "public").strip()
    if not _SCHEMA_RE.fullmatch(schema):
        raise RuntimeError(
            "SC_RL_DATABASE_SCHEMA must be a simple PostgreSQL identifier "
            "containing letters, numbers, and underscores."
        )
    return schema


def _normalized_endpoint(host: str) -> str:
    host = (host or "").strip().lower().rstrip(".")
    if not host:
        return ""
    labels = host.split(".")
    labels[0] = labels[0].replace("-pooler", "")
    return ".".join(labels)


def _endpoint_id(host: str) -> str:
    normalized = _normalized_endpoint(host)
    return normalized.split(".", 1)[0] if normalized else ""


@dataclass(frozen=True)
class ConfiguredDatabaseTarget:
    role: str
    host: str
    normalized_host: str
    endpoint_id: str
    database: str
    user: str
    schema: str
    pooled: bool
    sslmode: str
    fingerprint: str

    def public_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["label"] = f"postgres://{self.host}/{self.database}" if self.host else "postgres://not-configured"
        return payload


def parse_database_target(url: str, *, role: str, schema: str) -> ConfiguredDatabaseTarget:
    value = (url or "").strip()
    if not value:
        raise RuntimeError(f"{role} Postgres connection URL is missing.")
    parsed = urlsplit(value)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError(f"{role} connection URL must use the postgresql:// scheme.")
    host = (parsed.hostname or "").strip().lower()
    database = unquote((parsed.path or "").lstrip("/").split("/", 1)[0]).strip()
    user = unquote(parsed.username or "").strip()
    if not host or not database or not user:
        raise RuntimeError(f"{role} connection URL must include a hostname, database, and role.")
    normalized_host = _normalized_endpoint(host)
    query = parse_qs(parsed.query)
    sslmode = str((query.get("sslmode") or [""])[0]).strip().lower()
    identity = {
        "endpoint": normalized_host,
        "database": database,
        "user": user,
        "schema": schema,
    }
    fingerprint = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ConfiguredDatabaseTarget(
        role=role,
        host=host,
        normalized_host=normalized_host,
        endpoint_id=_endpoint_id(host),
        database=database,
        user=user,
        schema=schema,
        pooled="-pooler" in host,
        sslmode=sslmode,
        fingerprint=fingerprint,
    )


def configured_identity(runtime_url: str, direct_url: str, schema: str) -> dict[str, Any]:
    clean_schema = validate_schema_name(schema)
    runtime = parse_database_target(runtime_url, role="Runtime", schema=clean_schema)
    direct = parse_database_target(direct_url, role="Migration", schema=clean_schema)
    mismatches: list[str] = []
    if runtime.normalized_host != direct.normalized_host:
        mismatches.append("endpoint")
    if runtime.database != direct.database:
        mismatches.append("database")
    if runtime.user != direct.user:
        mismatches.append("role")
    if runtime.schema != direct.schema:
        mismatches.append("schema")
    if mismatches:
        raise RuntimeError(
            "DATABASE_URL and DIRECT_DATABASE_URL do not identify the same Neon database "
            f"({', '.join(mismatches)} mismatch)."
        )
    return {
        "runtime": runtime,
        "direct": direct,
        "configured_fingerprint": runtime.fingerprint,
        "identity_match": True,
        "runtime_pooled": runtime.pooled,
        "direct_pooled": direct.pooled,
    }


def live_database_identity(connection: Any, configured: ConfiguredDatabaseTarget) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT current_database() AS database_name,
               current_user AS database_user,
               current_schema() AS database_schema,
               current_setting('search_path') AS search_path,
               current_setting('neon.branch_id', true) AS branch_id,
               current_setting('neon.project_id', true) AS project_id,
               version() AS postgres_version,
               EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector') AS vector_enabled
        """
    ).fetchone()
    branch_id = str(row.get("branch_id") or "")
    project_id = str(row.get("project_id") or "")
    identity = {
        "endpoint": configured.normalized_host,
        "database": str(row.get("database_name") or ""),
        "user": str(row.get("database_user") or ""),
        "schema": str(row.get("database_schema") or ""),
        "branch_id": branch_id,
        "project_id": project_id,
    }
    fingerprint = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        **identity,
        "host": configured.host,
        "normalized_host": configured.normalized_host,
        "endpoint_id": configured.endpoint_id,
        "pooled": configured.pooled,
        "sslmode": configured.sslmode,
        "search_path": str(row.get("search_path") or ""),
        "postgres_version": str(row.get("postgres_version") or "").split(",")[0],
        "vector_enabled": bool(row.get("vector_enabled")),
        "configured_fingerprint": configured.fingerprint,
        "live_fingerprint": fingerprint,
    }


def compare_live_identities(runtime: dict[str, Any], direct: dict[str, Any]) -> dict[str, Any]:
    comparable = ("normalized_host", "database", "user", "schema")
    mismatches = [key for key in comparable if str(runtime.get(key) or "") != str(direct.get(key) or "")]
    runtime_branch = str(runtime.get("branch_id") or "")
    direct_branch = str(direct.get("branch_id") or "")
    if runtime_branch and direct_branch and runtime_branch != direct_branch:
        mismatches.append("branch_id")
    runtime_project = str(runtime.get("project_id") or "")
    direct_project = str(direct.get("project_id") or "")
    if runtime_project and direct_project and runtime_project != direct_project:
        mismatches.append("project_id")
    return {
        "identity_match": not mismatches,
        "identity_mismatches": mismatches,
    }
