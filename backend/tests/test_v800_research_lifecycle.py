from __future__ import annotations

import os
import uuid

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.main import app
from app.research_lifecycle import LIFECYCLE_SCHEMA, LIFECYCLE_CHECKPOINT_SCHEMA, lifecycle_catalog

client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _suffix() -> str:
    return uuid.uuid4().hex[:12]


def _project_context(owner: str, suffix: str):
    project = client.post("/v1/projects", headers=HEADERS, json={
        "title": f"Lifecycle project {suffix}",
        "objective": "Evaluate a bounded research question with inspectable evidence and uncertainty.",
        "owner_ref": owner,
    })
    assert project.status_code == 200, project.text
    project = project.json()
    context = client.post("/v1/research/contexts", headers=HEADERS, json={
        "title": f"Lifecycle context {suffix}",
        "owner_ref": owner,
        "scopes": ["current-project"],
        "project_id": project["project_id"],
        "active": True,
    })
    assert context.status_code == 200, context.text
    return project, context.json()


def test_lifecycle_catalog_is_explicit_and_non_automatic() -> None:
    catalog = lifecycle_catalog()
    assert catalog["stage_order"] == ["frame", "discover", "evaluate", "organize", "collaborate", "synthesize", "promote", "preserve"]
    assert catalog["governance"]["human_confirmed_transitions"] is True
    assert catalog["governance"]["automatic_stage_advancement"] is False
    assert catalog["governance"]["lifecycle_state_is_not_evidence"] is True


def test_lifecycle_creation_summary_transition_and_checkpoint() -> None:
    suffix = _suffix()
    owner = f"wp-user-lifecycle-{suffix}"
    project, context = _project_context(owner, suffix)
    q = client.post("/v1/research/questions", headers=HEADERS, json={
        "owner_ref": owner, "project_id": project["project_id"], "context_id": context["context_id"],
        "question": "Which evidence would change the working conclusion?",
    })
    assert q.status_code == 200, q.text

    created = client.post("/v1/research/lifecycles", headers=HEADERS, json={
        "owner_ref": owner, "project_id": project["project_id"], "context_id": context["context_id"],
        "title": "Primary research lifecycle",
    })
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["schema"] == LIFECYCLE_SCHEMA
    assert body["current_stage"] == "frame"
    assert body["summary"]["stage_readiness"]["frame"]["ready"] is True
    assert body["summary"]["governance"]["readiness_does_not_advance_stage"] is True
    lifecycle_id = body["lifecycle_id"]

    denied = client.post(f"/v1/research/lifecycles/{lifecycle_id}/transition", headers=HEADERS, json={
        "owner_ref": owner, "actor_ref": owner, "target_stage": "discover", "confirmed": False,
    })
    assert denied.status_code == 422

    moved = client.post(f"/v1/research/lifecycles/{lifecycle_id}/transition", headers=HEADERS, json={
        "owner_ref": owner, "actor_ref": owner, "target_stage": "discover", "reason": "Begin bounded discovery.", "confirmed": True,
    })
    assert moved.status_code == 200, moved.text
    assert moved.json()["current_stage"] == "discover"
    assert moved.json()["transition"]["metadata"]["explicit_confirmation"] is True

    checkpoint = client.post(f"/v1/research/lifecycles/{lifecycle_id}/checkpoint", headers=HEADERS, json={
        "owner_ref": owner, "actor_ref": owner, "note": "Discovery starting point.",
    })
    assert checkpoint.status_code == 200, checkpoint.text
    cp = checkpoint.json()["checkpoint"]
    assert cp["schema"] == LIFECYCLE_CHECKPOINT_SCHEMA
    assert len(cp["fingerprint"]) == 64
    assert cp["governance"]["immutable_snapshot"] is True

    detail = client.get(f"/v1/research/lifecycles/{lifecycle_id}?owner_ref={owner}", headers=HEADERS)
    assert detail.status_code == 200
    assert any(e["event_type"] == "stage-transition" for e in detail.json()["events"])
    assert any(c["checkpoint_id"] == cp["checkpoint_id"] for c in detail.json()["checkpoints"])


def test_lifecycle_owner_boundary_and_context_derived_project() -> None:
    suffix = _suffix()
    owner = f"wp-user-lifecycle-owner-{suffix}"
    outsider = f"wp-user-lifecycle-outsider-{suffix}"
    project, context = _project_context(owner, suffix)
    created = client.post("/v1/research/lifecycles", headers=HEADERS, json={
        "owner_ref": owner, "context_id": context["context_id"], "title": "Context-derived lifecycle",
    })
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["summary"]["signals"]["project_present"] is True
    assert body["summary"]["signals"]["project_objective"] is True
    denied = client.get(f"/v1/research/lifecycles/{body['lifecycle_id']}?owner_ref={outsider}", headers=HEADERS)
    assert denied.status_code == 403


def test_project_backup_contains_lifecycle_lineage() -> None:
    suffix = _suffix()
    owner = f"wp-user-lifecycle-backup-{suffix}"
    project, context = _project_context(owner, suffix)
    created = client.post("/v1/research/lifecycles", headers=HEADERS, json={
        "owner_ref": owner, "project_id": project["project_id"], "context_id": context["context_id"], "title": "Backup lifecycle",
    })
    assert created.status_code == 200
    lifecycle_id = created.json()["lifecycle_id"]
    cp = client.post(f"/v1/research/lifecycles/{lifecycle_id}/checkpoint", headers=HEADERS, json={"owner_ref": owner, "actor_ref": owner, "note": "Backup checkpoint"})
    assert cp.status_code == 200
    backup = client.post(f"/v1/projects/{project['project_id']}/backup", headers=HEADERS)
    assert backup.status_code == 200, backup.text
    rows = backup.json()["payload"]["research_lifecycles"]
    row = next(item for item in rows if item["lifecycle"]["lifecycle_id"] == lifecycle_id)
    assert row["events"]
    assert row["checkpoints"]
