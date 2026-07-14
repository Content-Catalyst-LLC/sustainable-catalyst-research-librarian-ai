from __future__ import annotations

import os
import uuid

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.main import app
from app.platform_handoffs import (
    CAPABILITIES_SCHEMA,
    COMPATIBILITY_SCHEMA,
    DELIVERY_SCHEMA,
    RECEIPT_SCHEMA,
    compatibility_report,
    validate_delivery_token,
    version_compatibility,
)

client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _sync_source() -> None:
    client.post(
        "/v1/knowledge/sync",
        headers=HEADERS,
        json={
            "mode": "upsert",
            "job_id": "v661-source-" + uuid.uuid4().hex,
            "records": [{
                "id": "post:v661",
                "title": "Cross Product Reliability",
                "url": "https://sustainablecatalyst.com/cross-product-reliability/",
                "summary": "Typed handoffs use version checks, delivery tokens, receipts, and immutable artifact returns.",
                "content": "Cross product reliability requires compatible destinations, bounded retries, idempotency, and provenance validation.",
            }],
        },
    )


def _prepare(key: str = "") -> dict:
    _sync_source()
    response = client.post(
        "/v1/handoffs/prepare",
        headers=HEADERS,
        json={
            "destination": "workbench",
            "question": "Calculate a reliability score using the Cross Product Reliability source.",
            "research_mode": "analyze",
            "session_id": "v661-session",
            "idempotency_key": key,
            "persist": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_capability_and_compatibility_contracts() -> None:
    capabilities = client.get("/v1/platform/capabilities", headers=HEADERS).json()
    compatibility = client.get("/v1/platform/compatibility", headers=HEADERS).json()
    assert capabilities["schema"] == CAPABILITIES_SCHEMA
    assert compatibility["schema"] == COMPATIBILITY_SCHEMA
    assert compatibility_report()["counts"]["unverified"] >= 1
    assert version_compatibility("3.9.9", "4.0.0", True, "https://example.test")["state"] == "incompatible"


def test_prepare_is_idempotent_and_has_delivery_token() -> None:
    key = "prepare-" + uuid.uuid4().hex
    first = _prepare(key)
    second = _prepare(key)
    assert first["handoff"]["handoff_id"] == second["handoff"]["handoff_id"]
    assert second["duplicate_event"] is True
    handoff = first["handoff"]
    assert handoff["delivery"]["schema"] == DELIVERY_SCHEMA
    assert validate_delivery_token(handoff)["ok"] is True


def test_retry_refreshes_token_and_uses_bounded_backoff() -> None:
    handoff = _prepare()["handoff"]
    original_token = handoff["delivery"]["token"]
    response = client.post(
        "/v1/handoffs/retry",
        headers=HEADERS,
        json={"handoff_id": handoff["handoff_id"], "reason": "destination-timeout", "idempotency_key": "retry-" + uuid.uuid4().hex},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["retry"]["attempt"] == 1
    assert body["retry"]["delay_seconds"] >= 5
    assert body["handoff"]["delivery"]["token"] != original_token
    assert body["handoff"]["validation"]["ok"] is True


def test_expired_or_rejected_delivery_can_refresh_token() -> None:
    handoff = _prepare()["handoff"]
    response = client.post(
        "/v1/handoffs/token/refresh",
        headers=HEADERS,
        json={"handoff_id": handoff["handoff_id"], "reason": "destination-requested-refresh"},
    )
    assert response.status_code == 200
    refreshed = response.json()["handoff"]
    assert refreshed["status"] == "token-refreshed"
    assert validate_delivery_token(refreshed)["ok"] is True


def test_receipt_is_validated_and_deduplicated() -> None:
    handoff = _prepare()["handoff"]
    receipt_id = "receipt-" + uuid.uuid4().hex
    payload = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "handoff_id": handoff["handoff_id"],
        "destination": "workbench",
        "status": "accepted",
        "handoff_fingerprint": handoff["provenance"]["payload_fingerprint"],
        "delivery_token": handoff["delivery"]["token"],
        "idempotency_key": receipt_id,
    }
    first = client.post("/v1/handoffs/receipts", headers=HEADERS, json=payload)
    second = client.post("/v1/handoffs/receipts", headers=HEADERS, json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate_event"] is True


def test_artifact_returns_are_idempotent_and_immutable() -> None:
    handoff = _prepare()["handoff"]
    artifact_id = "artifact-" + uuid.uuid4().hex
    key = "artifact-event-" + uuid.uuid4().hex
    payload = {
        "schema": "sc-research-artifact-return/1.0",
        "artifact_id": artifact_id,
        "handoff_id": handoff["handoff_id"],
        "destination": "workbench",
        "artifact_type": "calculation_report",
        "artifact": {"result": 0.98},
        "provenance": {"destination_version": "4.0.2"},
        "idempotency_key": key,
    }
    first = client.post("/v1/handoffs/artifacts/return", headers=HEADERS, json=payload)
    second = client.post("/v1/handoffs/artifacts/return", headers=HEADERS, json=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200
    assert second.json()["duplicate_event"] is True

    conflict = dict(payload)
    conflict["idempotency_key"] = "different-" + uuid.uuid4().hex
    conflict["artifact"] = {"result": 0.12}
    rejected = client.post("/v1/handoffs/artifacts/return", headers=HEADERS, json=conflict)
    assert rejected.status_code == 409
