from pathlib import Path

import pytest

from app.database_identity import configured_identity, parse_database_target, validate_schema_name

ROOT = Path(__file__).resolve().parents[2]


RUNTIME_URL = "postgresql://research:secret@ep-blue-river-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
DIRECT_URL = "postgresql://research:secret@ep-blue-river.us-east-2.aws.neon.tech/neondb?sslmode=require"


def test_pooled_and_direct_neon_urls_share_identity_without_secrets():
    identity = configured_identity(RUNTIME_URL, DIRECT_URL, "public")
    runtime = identity["runtime"]
    direct = identity["direct"]
    assert identity["identity_match"] is True
    assert runtime.pooled is True
    assert direct.pooled is False
    assert runtime.normalized_host == direct.normalized_host
    assert runtime.endpoint_id == "ep-blue-river"
    assert "secret" not in runtime.public_dict()["label"]
    assert runtime.fingerprint == direct.fingerprint


def test_mismatched_neon_database_is_rejected():
    with pytest.raises(RuntimeError, match="same Neon database"):
        configured_identity(RUNTIME_URL, DIRECT_URL.replace("/neondb", "/otherdb"), "public")


def test_invalid_schema_is_rejected():
    with pytest.raises(RuntimeError, match="SC_RL_DATABASE_SCHEMA"):
        validate_schema_name("public; DROP TABLE x")


def test_v711_fail_closed_factory_and_identity_contract():
    config = (ROOT / "backend/app/config.py").read_text()
    store = (ROOT / "backend/app/store.py").read_text()
    postgres = (ROOT / "backend/app/postgres_store.py").read_text()
    main = (ROOT / "backend/app/main.py").read_text()
    assert "SC_RL_DATABASE_FAIL_CLOSED" in config
    assert "SC_RL_DATABASE_SCHEMA" in config
    assert "Neon connection variables are configured but the selected database backend is SQLite" in store
    assert "Runtime and migration Postgres connections resolve to different database identities" in postgres
    assert "committed-empty" in postgres
    assert "database_fingerprint" in postgres
    assert "verifying-active-generation" in postgres
    assert "/v1/knowledge/database/identity" in main
    neon_check = (ROOT / "backend/scripts/neon_check.py").read_text()
    assert "DIRECT_DATABASE_URL is missing" in neon_check
    assert "identity_match" in neon_check
    assert "configured_fingerprint" in neon_check


def test_v711_wordpress_replays_committed_empty_state():
    module = (ROOT / "includes/class-sc-rl-v630-durable-index.php").read_text()
    assert "sc_rl_v711_neon_identity_not_ready" in module
    assert "neon-committed-empty-or-identity-mismatch" in module
    assert "database_fingerprint" in module
    assert "Neon database identity" in module
    assert "active index is empty" in module


def test_v711_migration_and_manifest_contract():
    migration = (ROOT / "backend/migrations/002_fail_closed_neon_identity.sql").read_text()
    manifest = (ROOT / "data/research_librarian_fail_closed_neon_manifest_v7.1.2.json").read_text()
    docs = (ROOT / "docs/V711_FAIL_CLOSED_NEON_ACTIVATION_DATABASE_IDENTITY.md").read_text()
    assert "database_fingerprint" in migration
    assert '"version": "7.1.2"' in manifest
    assert "committed-empty" in docs


def test_committed_empty_transaction_is_replayed_not_activated():
    from app.postgres_store import PostgresKnowledgeStore

    store = object.__new__(PostgresKnowledgeStore)
    store.sync_job_status = lambda _job_id: {
        "exists": True,
        "committed": False,
        "needs_full_replay": True,
        "state": "committed-empty",
        "batch_count": 24,
        "received_batch_count": 24,
        "received_batches": list(range(1, 25)),
        "missing_batches": [],
    }
    result = PostgresKnowledgeStore.reconcile_sync_job(store, "legacy-job", 24)
    assert result["reconciliation_action"] == "replay-all"
    assert result["transaction_state"] == "committed-empty"
    assert result["complete_for_expected_count"] is False
