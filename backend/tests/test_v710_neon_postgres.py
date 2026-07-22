from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_v710_postgres_store_contract():
    source = (ROOT / "backend/app/postgres_store.py").read_text()
    assert "class PostgresKnowledgeStore" in source
    assert "sc_rl_generations" in source
    assert "sc_rl_sync_batches" in source
    assert "sc_rl_staging_records" in source
    assert "sc_rl_records" in source
    assert "sc_rl_chunks" in source
    assert "embedding vector" in source
    assert "active_generation_id" in source
    assert "ready-to-switch" in source
    assert "os.rename" not in source
    assert "BackgroundTasks" not in source


def test_v710_factory_and_environment_contract():
    config = (ROOT / "backend/app/config.py").read_text()
    store = (ROOT / "backend/app/store.py").read_text()
    render = (ROOT / "render.yaml").read_text()
    requirements = (ROOT / "backend/requirements.txt").read_text()
    assert 'SC_RL_DATABASE_BACKEND' in config
    assert 'DATABASE_URL' in config
    assert 'DIRECT_DATABASE_URL' in config
    assert 'PostgresKnowledgeStore' in store
    assert 'value: postgres' in render
    assert 'sync: false' in render
    assert 'psycopg[binary,pool]' in requirements
    assert 'pgvector' in requirements


def test_v710_database_diagnostics_and_wordpress_visibility():
    main = (ROOT / "backend/app/main.py").read_text()
    admin = (ROOT / "includes/class-sc-rl-v630-durable-index.php").read_text()
    assert '/v1/knowledge/database/diagnostics' in main
    assert 'Neon Postgres' in admin
    assert 'pgvector ready' in admin
    assert 'Durable database' in admin


def test_v710_free_tier_embedding_dimensions():
    config = (ROOT / "backend/app/config.py").read_text()
    provider = (ROOT / "backend/app/provider.py").read_text()
    render = (ROOT / "render.yaml").read_text()
    assert 'SC_RL_EMBEDDING_DIMENSIONS' in config
    assert 'output_dimensionality' in provider
    assert 'magnitude = math.sqrt' in provider
    assert 'value: "768"' in render
