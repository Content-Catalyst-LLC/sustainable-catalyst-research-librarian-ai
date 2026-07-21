from __future__ import annotations

import json
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.provider import credential_diagnostics
from app.store import KnowledgeStore


def _headers() -> dict[str, str]:
    return {"X-SC-RL-Key": settings.api_key}


def test_provider_diagnostics_never_exposes_secret() -> None:
    result = credential_diagnostics()
    assert result["credential_source"] == "SC_RL_GEMINI_API_KEY"
    assert "gemini_api_key" not in result
    if settings.gemini_api_key:
        assert settings.gemini_api_key not in str(result)


def test_provider_diagnostics_endpoint() -> None:
    response = TestClient(app).get("/v1/provider/diagnostics", headers=_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "7.0.6"
    assert payload["credential_source"] == "SC_RL_GEMINI_API_KEY"


def test_embedding_status_treats_stale_model_vector_as_pending(tmp_path) -> None:
    store = KnowledgeStore(tmp_path / "repair.sqlite3")
    with store._connection() as connection:
        connection.execute(
            "INSERT INTO records(id,title,url,payload,content_hash,updated_utc) VALUES(?,?,?,?,?,?)",
            ("record-1", "Record 1", "https://example.com/record-1", "{}", "record-hash-1", "2026-07-20T00:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO retrieval_chunks(chunk_id,record_id,heading,page,passage,position,content_hash,embedding_model,embedding_json,updated_utc) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("chunk-1", "record-1", "Heading", None, "Passage", 0, "hash-1", "old-model", json.dumps([0.1, 0.2]), "2026-07-20T00:00:00+00:00"),
        )
    status = store.embedding_status()
    assert status["indexed_chunks"] == 1
    assert status["embedded_chunks"] == 0
    assert status["pending_chunks"] == 1
