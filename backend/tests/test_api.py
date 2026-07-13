import os
from pathlib import Path
import shutil

TEST_DATA_DIR = Path("/tmp/sc-rl-tests-v630")
shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
os.environ["SC_RL_BACKEND_API_KEY"] = "test-key"
os.environ["SC_RL_DATA_DIR"] = str(TEST_DATA_DIR)

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == "6.3.0"


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
    assert body["manifest"]["schema_version"] == 3
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
