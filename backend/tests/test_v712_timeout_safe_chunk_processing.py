from pathlib import Path

from app.postgres_store import adaptive_chunk_batch_limit

ROOT = Path(__file__).resolve().parents[2]


def test_adaptive_chunk_batch_limit_shrinks_slow_steps_and_grows_carefully():
    assert adaptive_chunk_batch_limit(8, 25, minimum=1, maximum=10, target_seconds=20) == 4
    assert adaptive_chunk_batch_limit(5, 4, minimum=1, maximum=10, target_seconds=20) == 6
    assert adaptive_chunk_batch_limit(1, 50, minimum=1, maximum=10, target_seconds=20) == 1
    assert adaptive_chunk_batch_limit(10, 2, minimum=1, maximum=10, target_seconds=20) == 10
    assert adaptive_chunk_batch_limit(6, 1, minimum=1, maximum=10, target_seconds=20, timed_out=True) == 3


def test_v712_backend_contract():
    config = (ROOT / "backend/app/config.py").read_text()
    store = (ROOT / "backend/app/postgres_store.py").read_text()
    migration = (ROOT / "backend/migrations/003_timeout_safe_chunk_processing.sql").read_text()
    render = (ROOT / "render.yaml").read_text()
    assert 'SC_RL_POSTGRES_ACTIVATION_CHUNK_RECORD_BATCH_LIMIT", 5' in config
    assert "jsonb_to_recordset" in store
    assert "connection.commit()" in store
    assert "pg_try_advisory_lock" in store
    assert "last_step_duration_ms" in store
    assert "chunk_batch_limit" in migration
    assert 'value: "5"' in render


def test_v712_wordpress_timeout_reconciliation_contract():
    module = (ROOT / "includes/class-sc-rl-v630-durable-index.php").read_text()
    assert "is_backend_timeout_error" in module
    assert "backend_activation_progressed" in module
    assert "backend_timeout_poll_only" in module
    assert "A chunk request exceeded the WordPress timeout" in module
    assert "Current chunk batch" in module
    assert "Timeout recoveries" in module
