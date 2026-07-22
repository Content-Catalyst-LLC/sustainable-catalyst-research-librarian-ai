from __future__ import annotations

import json
import os
import sys

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError as exc:
    raise SystemExit("Install backend/requirements.txt before running this check.") from exc

url = os.getenv("DIRECT_DATABASE_URL") or os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("Set DIRECT_DATABASE_URL or DATABASE_URL first.")

with psycopg.connect(url, row_factory=dict_row) as connection:
    row = connection.execute(
        """
        SELECT current_database() AS database_name,
               current_user AS database_user,
               pg_database_size(current_database()) AS database_bytes,
               EXISTS(SELECT 1 FROM pg_extension WHERE extname='vector') AS vector_enabled,
               to_regclass('public.sc_rl_generations') IS NOT NULL AS schema_installed
        """
    ).fetchone()

safe = {
    "ok": bool(row["vector_enabled"]),
    "database_name": row["database_name"],
    "database_user": row["database_user"],
    "database_megabytes": round(int(row["database_bytes"] or 0) / 1048576, 2),
    "vector_enabled": bool(row["vector_enabled"]),
    "schema_installed": bool(row["schema_installed"]),
}
print(json.dumps(safe, indent=2))
sys.exit(0 if safe["ok"] else 1)
