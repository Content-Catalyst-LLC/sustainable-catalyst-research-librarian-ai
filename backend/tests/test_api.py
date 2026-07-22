import os
from pathlib import Path
import shutil

TEST_DATA_DIR = Path("/tmp/sc-rl-tests-v631")
shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
os.environ["SC_RL_BACKEND_API_KEY"] = "test-key"
os.environ["SC_RL_DATA_DIR"] = str(TEST_DATA_DIR)

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == "7.1.0"


def test_sync_requires_key() -> None:
    response = client.post("/v1/knowledge/sync", json={"records": [], "mode": "replace"})
    assert response.status_code == 401


def test_sync_and_retrieve() -> None:
    headers = {"X-SC-RL-Key": "test-key"}
    payload = {
        "mode": "replace",
        "job_id": "api-sync-1",
        "source_site": "https://sustainablecatalyst.com",
        "records": [
            {
                "id": "post:1",
                "title": "Stability Analysis with Eigenvalues",
                "url": "https://sustainablecatalyst.com/stability-analysis-with-eigenvalues/",
                "slug": "stability-analysis-with-eigenvalues",
                "summary": "A systems modeling article about eigenvalue stability.",
                "series": "Linear Algebra for Systems Modeling",
            }
        ],
    }
    response = client.post("/v1/knowledge/sync", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1
    assert response.json()["rejected"] == 0
    response = client.post("/v1/retrieve", headers=headers, json={"query": "Stability Analysis with Eigenvalues", "limit": 5})
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Stability Analysis with Eigenvalues"


def test_manifest_and_runtime_snapshots() -> None:
    headers = {"X-SC-RL-Key": "test-key"}
    manifest = client.get("/v1/knowledge/manifest", headers=headers)
    assert manifest.status_code == 200
    body = manifest.json()
    assert body["manifest"]["storage_engine"] == "sqlite"
    assert body["manifest"]["schema_version"] == 12
    snapshots = client.get("/v1/knowledge/snapshots", headers=headers)
    assert snapshots.status_code == 200
    assert isinstance(snapshots.json()["snapshots"], list)


def test_sync_rejects_batch_index_beyond_batch_count() -> None:
    headers = {"X-SC-RL-Key": "test-key"}
    response = client.post(
        "/v1/knowledge/sync",
        headers=headers,
        json={
            "mode": "replace",
            "job_id": "invalid-batch-position",
            "batch_index": 2,
            "batch_count": 1,
            "records": [],
        },
    )
    assert response.status_code == 422


def test_startup_status_is_exposed() -> None:
    response = client.get("/startup")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "7.1.0"
    assert body["startup_state"] in {"warming", "ready"}
    assert 0 <= body["startup_progress"] <= 100


def test_sync_isolates_invalid_record() -> None:
    headers = {"X-SC-RL-Key": "test-key"}
    response = client.post(
        "/v1/knowledge/sync",
        headers=headers,
        json={
            "mode": "upsert",
            "job_id": "api-isolated-rejection",
            "records": [
                {
                    "id": "valid-record",
                    "title": "Valid Record",
                    "url": "https://sustainablecatalyst.com/valid-record/",
                },
                {
                    "id": "invalid-record",
                    "title": "",
                    "url": "https://sustainablecatalyst.com/invalid-record/",
                },
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["committed"] is True
    assert body["rejected"] == 1
    assert body["state"] == "completed-with-rejections"
    assert body["rejected_records"][0]["id"] == "invalid-record"


def test_snapshot_validation_and_maintenance_endpoints() -> None:
    headers = {"X-SC-RL-Key": "test-key"}
    validation = client.get("/v1/knowledge/snapshots/validate", headers=headers)
    assert validation.status_code == 200
    assert "invalid_count" in validation.json()
    maintenance = client.post(
        "/v1/knowledge/maintenance",
        headers=headers,
        json={"max_age_seconds": 300, "purge_staging": True},
    )
    assert maintenance.status_code == 200
    assert "repaired_jobs" in maintenance.json()


def test_hybrid_explain_returns_evidence_and_diagnostics() -> None:
    headers = {"X-SC-RL-Key": "test-key"}
    response = client.post(
        "/v1/retrieve/explain",
        headers=headers,
        json={"query": "Stability Analysis with Eigenvalues", "limit": 5, "include_diagnostics": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["matches"]
    assert body["evidence"][0]["id"] == "SC1"
    assert body["diagnostics"]["retrieval_mode"].startswith("exact-title+bm25")


def test_embedding_status_is_available_without_provider_call() -> None:
    headers = {"X-SC-RL-Key": "test-key"}
    response = client.get("/v1/knowledge/embeddings/status", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "7.1.0"
    assert "semantic_coverage" in body
