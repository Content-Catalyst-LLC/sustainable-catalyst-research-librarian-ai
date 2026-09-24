from __future__ import annotations

import os
import uuid

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.main import app
from app.research_state import normalize_activity, normalize_object_state, normalize_open_question, prompt_research_state, summarize_research_state

client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _suffix() -> str:
    return uuid.uuid4().hex[:12]


def test_state_contracts_are_workflow_memory_not_evidence() -> None:
    owner = "wp-user-state-contract"
    activity = normalize_activity({"owner_ref": owner, "event_type": "search", "query": "What remains unresolved?"})
    state = normalize_object_state({"owner_ref": owner, "object_id": "object-1", "reading_state": "rejected", "contradiction_state": "flagged"})
    question = normalize_open_question({"owner_ref": owner, "question": "Which source resolves the discrepancy?"})
    summary = summarize_research_state([activity], [state], [question], owner_ref=owner)
    prompt = prompt_research_state(summary)

    assert activity["governance"]["not_evidence"] is True
    assert state["governance"]["rejection_is_not_source_deletion"] is True
    assert question["governance"]["open_question_is_not_fact"] is True
    assert summary["governance"]["state_is_not_evidence"] is True
    assert prompt["schema"] == "sc-research-state-prompt/1.0"
    assert prompt["rejected_object_ids"] == ["object-1"]
    assert prompt["flagged_contradiction_object_ids"] == ["object-1"]
    assert "not factual evidence" in prompt["boundary_note"]


def test_api_persists_reading_state_questions_and_activity_by_context() -> None:
    suffix = _suffix()
    owner = f"wp-user-v740-{suffix}"
    project = client.post("/v1/projects", headers=HEADERS, json={"title": f"State project {suffix}", "owner_ref": owner}).json()
    source = client.post("/v1/library/objects", headers=HEADERS, json={
        "title": "State source",
        "owner_ref": owner,
        "source_scope": "my-library",
        "object_type": "source",
        "provenance": {"source_record_id": f"record-{suffix}"},
    }).json()
    client.post(f"/v1/library/objects/{source['object_id']}/projects/{project['project_id']}", headers=HEADERS)
    context = client.post("/v1/research/contexts", headers=HEADERS, json={
        "title": "Persistent state",
        "owner_ref": owner,
        "project_id": project["project_id"],
        "scopes": ["my-library", "current-project"],
        "active": True,
    }).json()

    state_response = client.post("/v1/research/object-states", headers=HEADERS, json={
        "owner_ref": owner,
        "project_id": project["project_id"],
        "context_id": context["context_id"],
        "object_id": source["object_id"],
        "reading_state": "reviewed",
        "contradiction_state": "flagged",
        "note": "Methods conflict with another record.",
    })
    assert state_response.status_code == 200, state_response.text
    assert state_response.json()["reading_state"] == "reviewed"

    question_response = client.post("/v1/research/questions", headers=HEADERS, json={
        "owner_ref": owner,
        "project_id": project["project_id"],
        "context_id": context["context_id"],
        "question": "What evidence would resolve the methods conflict?",
        "linked_object_ids": [source["object_id"]],
    })
    assert question_response.status_code == 200, question_response.text
    assert question_response.json()["status"] == "open"

    activity_response = client.post("/v1/research/activity", headers=HEADERS, json={
        "owner_ref": owner,
        "project_id": project["project_id"],
        "context_id": context["context_id"],
        "event_type": "search",
        "query": "Compare methods",
    })
    assert activity_response.status_code == 200, activity_response.text

    summary = client.get(f"/v1/research/state/summary?context_id={context['context_id']}", headers=HEADERS)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["schema"] == "sc-research-state-summary/1.0"
    assert body["counts"]["reading_states"]["reviewed"] == 1
    assert body["counts"]["contradiction_states"]["flagged"] == 1
    assert len(body["open_questions"]) == 1
    assert any(item["query"] == "Compare methods" for item in body["recent_searches"])


def test_rejected_object_is_remembered_but_deprioritized_for_context_retrieval() -> None:
    suffix = _suffix()
    owner = f"wp-user-v740-reject-{suffix}"
    source = client.post("/v1/library/objects", headers=HEADERS, json={
        "title": "Rejected context source",
        "owner_ref": owner,
        "source_scope": "my-library",
        "object_type": "source",
        "provenance": {"source_record_id": f"missing-record-{suffix}"},
    }).json()
    context = client.post("/v1/research/contexts", headers=HEADERS, json={"title": "Rejected state", "owner_ref": owner, "scopes": ["my-library"], "active": True}).json()
    client.post("/v1/research/object-states", headers=HEADERS, json={
        "owner_ref": owner,
        "context_id": context["context_id"],
        "object_id": source["object_id"],
        "reading_state": "rejected",
    })
    resolved = client.get(f"/v1/research/contexts/{context['context_id']}/resolve", headers=HEADERS).json()
    response = client.post("/v1/ask", headers=HEADERS, json={
        "question": "What evidence is available?",
        "research_context": resolved["prompt_context"],
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert source["object_id"] in body["research_state"]["rejected_object_ids"]
    assert body["retrieval_diagnostics"]["research_context_retrieval"]["rejected_context_objects_deprioritized"] == 1
    summary = client.get(f"/v1/research/state/summary?context_id={context['context_id']}", headers=HEADERS).json()
    assert any(item["query"] == "What evidence is available?" for item in summary["recent_searches"])


def test_project_backup_carries_research_state() -> None:
    suffix = _suffix()
    owner = f"wp-user-v740-backup-{suffix}"
    project = client.post("/v1/projects", headers=HEADERS, json={"title": f"Backup state {suffix}", "owner_ref": owner}).json()
    source = client.post("/v1/library/objects", headers=HEADERS, json={"title": "Backup source", "owner_ref": owner, "source_scope": "my-library"}).json()
    client.post(f"/v1/library/objects/{source['object_id']}/projects/{project['project_id']}", headers=HEADERS)
    client.post("/v1/research/object-states", headers=HEADERS, json={"owner_ref": owner, "project_id": project["project_id"], "object_id": source["object_id"], "reading_state": "reading"})
    client.post("/v1/research/questions", headers=HEADERS, json={"owner_ref": owner, "project_id": project["project_id"], "question": "What should I read next?"})
    client.post("/v1/research/activity", headers=HEADERS, json={"owner_ref": owner, "project_id": project["project_id"], "event_type": "search", "query": "Reading sequence"})

    backup = client.post(f"/v1/projects/{project['project_id']}/backup", headers=HEADERS, json={})
    assert backup.status_code == 200, backup.text
    payload = backup.json()["payload"]
    assert payload["object_states"]
    assert payload["open_questions"]
    assert payload["research_activity"]

    dry = client.post("/v1/platform/backups/import", headers=HEADERS, json={"envelope": backup.json(), "dry_run": True})
    assert dry.status_code == 200, dry.text
    counts = dry.json()["counts"]
    assert counts["object_states"] >= 1
    assert counts["open_questions"] >= 1
    assert counts["research_activity"] >= 1


def test_platform_api_advertises_v740_research_state_contracts() -> None:
    body = client.get("/v1/platform/api", headers=HEADERS).json()
    assert body["version"] == "9.1.0"
    assert body["schema"] == "sc-connected-research-api/2.0"
    assert "research-state" in body["resources"]
    assert "open-questions" in body["resources"]
    assert body["research_state"]["workflow_memory_only"] is True
    assert body["research_state"]["not_evidence"] is True


def test_context_objects_without_explicit_state_are_visible_as_derived_unread() -> None:
    suffix = _suffix()
    owner = f"wp-user-v740-unread-{suffix}"
    source = client.post("/v1/library/objects", headers=HEADERS, json={
        "title": "Unread context source",
        "owner_ref": owner,
        "source_scope": "my-library",
        "object_type": "source",
    }).json()
    context = client.post("/v1/research/contexts", headers=HEADERS, json={
        "title": "Unread context",
        "owner_ref": owner,
        "scopes": ["my-library"],
        "active": True,
    }).json()

    body = client.get(f"/v1/research/state/summary?context_id={context['context_id']}", headers=HEADERS).json()
    unread = [item for item in body["review_queue"] if item["object_id"] == source["object_id"]]
    assert len(unread) == 1
    assert unread[0]["reading_state"] == "unread"
    assert unread[0]["derived_unread"] is True
    assert unread[0]["object_title"] == "Unread context source"
