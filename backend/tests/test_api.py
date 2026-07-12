import os

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")
os.environ.setdefault("SC_RL_DATA_DIR", "/tmp/sc-rl-tests")

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == "6.2.0"


def test_sync_requires_key() -> None:
    response = client.post("/v1/knowledge/sync", json={"records": [], "mode": "replace"})
    assert response.status_code == 401


def test_sync_and_retrieve() -> None:
    headers = {"X-SC-RL-Key": "test-key"}
    payload = {
        "mode": "replace",
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
    response = client.post("/v1/retrieve", headers=headers, json={"query": "Stability Analysis with Eigenvalues", "limit": 5})
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Stability Analysis with Eigenvalues"
