from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.models import EvidenceCitation, RetrievedSource
from app.platform_handoffs import (
    ARTIFACT_SCHEMA,
    HANDOFF_SCHEMA,
    ROUTE_SCHEMA,
    available_capabilities,
    infer_destination,
    prepare_handoff,
    validate_handoff,
)


client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _source() -> RetrievedSource:
    return RetrievedSource(
        id="post:660",
        title="Energy Systems Modeling",
        url="https://sustainablecatalyst.com/energy-systems-modeling/",
        summary="A source-aware introduction to energy systems modeling.",
        score=99.0,
        citation_label="SC1",
        section="Model boundaries",
        passage="Models should expose variables, assumptions, units, and validation boundaries.",
        retrieval_reasons=["exact-title", "bm25-section"],
    )


def _evidence() -> EvidenceCitation:
    return EvidenceCitation(
        id="SC1",
        record_id="post:660",
        title="Energy Systems Modeling",
        url="https://sustainablecatalyst.com/energy-systems-modeling/",
        section="Model boundaries",
        passage="Models should expose variables, assumptions, units, and validation boundaries.",
    )


def test_capability_catalog_exposes_connected_products() -> None:
    capabilities = available_capabilities()
    assert {"workbench", "decision_studio", "site_intelligence", "lab", "feature_suggestions"}.issubset(capabilities)
    assert all(item["contract"] == HANDOFF_SCHEMA for item in capabilities.values())


def test_destination_inference_is_typed() -> None:
    assert infer_destination("Calculate and graph this equation", "analyze") == "workbench"
    assert infer_destination("Compare options and prepare a decision packet", "decision") == "decision_studio"
    assert infer_destination("Compare climate indicators for Kenya", "subject") == "site_intelligence"
    assert infer_destination("Design a laboratory experiment and validation protocol", "subject") == "lab"


def test_workbench_handoff_is_versioned_and_validated() -> None:
    handoff = prepare_handoff(
        "workbench",
        "Calculate P = VI and graph the result in W.",
        "analyze",
        "session-660",
        [_source()],
        [_evidence()],
        assumptions=["Voltage is supplied by the user."],
    )
    assert handoff["schema"] == HANDOFF_SCHEMA
    assert handoff["route"]["schema"] == ROUTE_SCHEMA
    assert handoff["payload"]["contract"] == "sc-workbench-task/1.0"
    assert "P = VI" in handoff["payload"]["equations"]
    assert handoff["provenance"]["payload_fingerprint"]
    assert validate_handoff(handoff)["ok"] is True


def test_tampered_handoff_fails_fingerprint_validation() -> None:
    handoff = prepare_handoff("decision_studio", "Compare two infrastructure options.", "decision", "session-660", [_source()], [_evidence()])
    handoff["question"] = "Tampered question"
    validation = validate_handoff(handoff)
    assert validation["ok"] is False
    assert any("fingerprint" in error.lower() for error in validation["errors"])


def test_capabilities_endpoint() -> None:
    response = client.get("/v1/platform/capabilities", headers=HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "7.1.1"
    assert "workbench" in body["available"]
    assert body["schema"] == "sc-platform-capabilities/1.1"


def test_prepare_validate_and_return_artifact_round_trip() -> None:
    client.post(
        "/v1/knowledge/sync",
        headers=HEADERS,
        json={
            "mode": "upsert",
            "job_id": "platform-handoff-source",
            "records": [
                {
                    "id": "post:660",
                    "title": "Energy Systems Modeling",
                    "url": "https://sustainablecatalyst.com/energy-systems-modeling/",
                    "summary": "A source-aware introduction to energy systems modeling.",
                    "content": "Models should expose variables, assumptions, units, and validation boundaries.",
                }
            ],
        },
    )
    prepared = client.post(
        "/v1/handoffs/prepare",
        headers=HEADERS,
        json={
            "destination": "workbench",
            "question": "Calculate P = VI using the Energy Systems Modeling source.",
            "research_mode": "analyze",
            "session_id": "platform-round-trip",
            "persist": True,
        },
    )
    assert prepared.status_code == 200
    handoff = prepared.json()["handoff"]
    assert handoff["validation"]["ok"] is True

    validated = client.post("/v1/handoffs/validate", headers=HEADERS, json={"payload": handoff})
    assert validated.status_code == 200
    assert validated.json()["ok"] is True

    artifact_id = "artifact-" + uuid.uuid4().hex
    returned = client.post(
        "/v1/handoffs/artifacts/return",
        headers=HEADERS,
        json={
            "schema": ARTIFACT_SCHEMA,
            "artifact_id": artifact_id,
            "handoff_id": handoff["handoff_id"],
            "destination": "workbench",
            "artifact_type": "calculation_report",
            "artifact": {"result": "P = 120 W", "inputs": {"V": 12, "I": 10}},
            "provenance": {"destination_version": "test"},
        },
    )
    assert returned.status_code == 200
    artifact = returned.json()["artifact"]
    assert artifact["provenance"]["research_librarian_handoff_fingerprint"] == handoff["provenance"]["payload_fingerprint"]
    assert artifact["provenance"]["chain"][-1] == "research_librarian_return"

    listed = client.get("/v1/handoffs/artifacts", headers=HEADERS)
    assert listed.status_code == 200
    assert any(item["artifact_id"] == artifact_id for item in listed.json()["artifacts"])
