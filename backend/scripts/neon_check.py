from __future__ import annotations

"""Password-free Neon identity and migration readiness check for v7.1.1.

Run from the repository root or backend directory after setting DATABASE_URL,
DIRECT_DATABASE_URL, and optionally SC_RL_DATABASE_SCHEMA. The script never
prints credentials or complete connection strings.
"""

import json
import os
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError as exc:
    raise SystemExit("Install backend/requirements.txt before running this check.") from exc

from app.database_identity import (
    compare_live_identities,
    configured_identity,
    live_database_identity,
    validate_schema_name,
)

runtime_url = os.getenv("DATABASE_URL", "").strip()
direct_url = os.getenv("DIRECT_DATABASE_URL", "").strip()
schema = validate_schema_name(os.getenv("SC_RL_DATABASE_SCHEMA", "public"))

if not runtime_url:
    raise SystemExit("DATABASE_URL is missing. Use the pooled Neon connection string.")
if not direct_url:
    raise SystemExit("DIRECT_DATABASE_URL is missing. Use the direct Neon connection string.")

configured = configured_identity(runtime_url, direct_url, schema)


def inspect(url: str, target: object) -> tuple[dict[str, object], dict[str, bool]]:
    with psycopg.connect(url, row_factory=dict_row) as connection:
        connection.execute(f'SET search_path TO "{schema}"')
        identity = live_database_identity(connection, target)
        tables: dict[str, bool] = {}
        for table in ("sc_rl_meta", "sc_rl_generations", "sc_rl_records", "sc_rl_chunks"):
            row = connection.execute("SELECT to_regclass(%s) IS NOT NULL AS present", (f"{schema}.{table}",)).fetchone()
            tables[table] = bool(row["present"])
        return identity, tables


runtime, runtime_tables = inspect(runtime_url, configured["runtime"])
direct, direct_tables = inspect(direct_url, configured["direct"])
comparison = compare_live_identities(runtime, direct)
vector_ready = bool(runtime.get("vector_enabled")) and bool(direct.get("vector_enabled"))
migrations_ready = all(runtime_tables.values()) and all(direct_tables.values())
ready = bool(comparison["identity_match"] and vector_ready and migrations_ready)

safe = {
    "ok": ready,
    "backend": "postgres",
    "schema": schema,
    "identity_match": bool(comparison["identity_match"]),
    "identity_mismatches": comparison["identity_mismatches"],
    "configured_fingerprint": configured["configured_fingerprint"],
    "runtime": {
        "endpoint_id": runtime.get("endpoint_id", ""),
        "database": runtime.get("database", ""),
        "user": runtime.get("user", ""),
        "schema": runtime.get("schema", ""),
        "branch_id": runtime.get("branch_id", ""),
        "project_id": runtime.get("project_id", ""),
        "pooled": runtime.get("pooled", False),
        "vector_enabled": runtime.get("vector_enabled", False),
        "live_fingerprint": runtime.get("live_fingerprint", ""),
        "tables": runtime_tables,
    },
    "migration": {
        "endpoint_id": direct.get("endpoint_id", ""),
        "database": direct.get("database", ""),
        "user": direct.get("user", ""),
        "schema": direct.get("schema", ""),
        "branch_id": direct.get("branch_id", ""),
        "project_id": direct.get("project_id", ""),
        "pooled": direct.get("pooled", False),
        "vector_enabled": direct.get("vector_enabled", False),
        "live_fingerprint": direct.get("live_fingerprint", ""),
        "tables": direct_tables,
    },
    "migration_ready": migrations_ready,
    "vector_ready": vector_ready,
}
print(json.dumps(safe, indent=2, sort_keys=True))
sys.exit(0 if ready else 1)
