from __future__ import annotations

import os
import uuid

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.main import app
from app.workspace_promotion import build_workspace_packet, apply_promotion_receipt

client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _suffix() -> str:
    return uuid.uuid4().hex[:12]


def test_packet_preserves_provenance_and_excludes_rejected_by_default() -> None:
    source_a = {
        "object_id": "source-a",
        "object_type": "source",
        "title": "Official source",
        "owner_ref": "wp-user-1",
        "source_scope": "sustainable-catalyst-collection",
        "fingerprint": "a" * 64,
        "provenance": {"url": "https://example.org/a", "publisher": "Institution A"},
    }
    source_b = {
        "object_id": "source-b",
        "object_type": "source",
        "title": "Personal source",
        "owner_ref": "wp-user-1",
        "source_scope": "my-library",
        "fingerprint": "b" * 64,
        "provenance": {"url": "https://example.org/b", "publisher": "Institution B"},
    }
    state = {
        "object_states": [
            {"object_id": "source-b", "reading_state": "rejected", "contradiction_state": "none"},
        ],
        "open_questions": [{"question_id": "q1", "question": "What is missing?", "status": "open"}],
    }
    packet = build_workspace_packet(
        artifact_type="evidence-set",
        title="Evidence packet",
        owner_ref="wp-user-1",
        sources=[source_a, source_b],
        research_state=state,
    )
    assert packet["schema"] == "sc-workspace-research-handoff/1.0"
    assert packet["artifact_contract"] == "sc-workspace-evidence-set/1.0"
    assert [item["object_id"] for item in packet["sources"]] == ["source-a"]
    assert packet["sources"][0]["source_scope"] == "sustainable-catalyst-collection"
    assert packet["sources"][0]["owner_ref"] == "wp-user-1"
    assert packet["governance"]["promotion_is_not_publication"] is True
    assert packet["governance"]["workspace_may_not_silently_reclassify_source_scope"] is True
    assert packet["provenance"]["source_fingerprints"]["source-a"] == "a" * 64


def test_prepare_workspace_promotion_from_project_context_and_receipt_round_trip() -> None:
    suffix = _suffix()
    owner = f"wp-user-promotion-{suffix}"
    project = client.post("/v1/projects", headers=HEADERS, json={
        "title": f"Promotion project {suffix}",
        "objective": "Move governed research into Workspace.",
        "owner_ref": owner,
    })
    assert project.status_code == 200, project.text
    project_id = project.json()["project_id"]

    source = client.post("/v1/library/objects", headers=HEADERS, json={
        "title": "Promotable source",
        "owner_ref": owner,
        "source_scope": "my-library",
        "object_type": "source",
        "provenance": {"source_record_id": f"record-{suffix}", "publisher": "Test Institute", "url": "https://example.org/source"},
    })
    assert source.status_code == 200, source.text
    object_id = source.json()["object_id"]
    linked = client.post(f"/v1/library/objects/{object_id}/projects/{project_id}", headers=HEADERS)
    assert linked.status_code == 200, linked.text

    context = client.post("/v1/research/contexts", headers=HEADERS, json={
        "title": "Promotion context",
        "owner_ref": owner,
        "scopes": ["current-project"],
        "project_id": project_id,
        "selected_object_ids": [object_id],
        "active": True,
    })
    assert context.status_code == 200, context.text
    context_id = context.json()["context_id"]

    prepared = client.post("/v1/workspace/promotions/prepare", headers=HEADERS, json={
        "owner_ref": owner,
        "project_id": project_id,
        "context_id": context_id,
        "artifact_type": "notebook",
        "title": "Workspace research notebook",
        "selected_object_ids": [object_id],
        "notes": "Carry the unresolved questions forward.",
    })
    assert prepared.status_code == 200, prepared.text
    body = prepared.json()
    assert body["schema"] == "sc-workspace-artifact-promotion/1.0"
    assert body["status"] == "prepared"
    assert body["packet"]["artifact_type"] == "notebook"
    assert body["packet"]["project"]["project_id"] == project_id
    assert body["packet"]["research_context"]["context_id"] == context_id
    assert body["packet"]["sources"][0]["object_id"] == object_id

    wrong = client.post(f"/v1/workspace/promotions/{body['promotion_id']}/receipt", headers=HEADERS, json={
        "promotion_id": body["promotion_id"],
        "owner_ref": owner,
        "packet_fingerprint": "0" * 64,
        "status": "imported",
        "workspace_artifact_id": f"notebook-{suffix}",
    })
    assert wrong.status_code == 409

    receipt = client.post(f"/v1/workspace/promotions/{body['promotion_id']}/receipt", headers=HEADERS, json={
        "promotion_id": body["promotion_id"],
        "owner_ref": owner,
        "packet_fingerprint": body["packet_fingerprint"],
        "status": "imported",
        "workspace_artifact_id": f"notebook-{suffix}",
        "workspace_artifact_type": "notebook",
        "workspace_url": "https://sustainablecatalyst.com/workspace/",
        "actor_ref": owner,
    })
    assert receipt.status_code == 200, receipt.text
    imported = receipt.json()
    assert imported["status"] == "imported"
    assert imported["receipt"]["workspace_artifact_id"] == f"notebook-{suffix}"
    assert imported["receipt"]["governance"]["does_not_confirm_publication"] is True

    listing = client.get(f"/v1/workspace/promotions?owner_ref={owner}", headers=HEADERS)
    assert listing.status_code == 200, listing.text
    assert listing.json()["summary"]["by_status"]["imported"] >= 1

    backup = client.post(f"/v1/projects/{project_id}/backup", headers=HEADERS)
    assert backup.status_code == 200, backup.text
    promotions = backup.json()["payload"]["workspace_promotions"]
    assert any(item["promotion_id"] == body["promotion_id"] for item in promotions)


def test_room_member_can_promote_shared_room_evidence_without_reclassifying_it() -> None:
    suffix = _suffix()
    owner = f"wp-user-room-promotion-owner-{suffix}"
    collaborator = f"wp-user-room-promotion-collab-{suffix}"
    room = client.post("/v1/research/rooms", headers=HEADERS, json={"title": "Promotion room", "owner_ref": owner}).json()
    member = client.post(f"/v1/research/rooms/{room['room_id']}/members", headers=HEADERS, json={
        "room_id": room["room_id"], "member_ref": collaborator, "role": "researcher", "status": "active", "added_by_ref": owner,
    })
    assert member.status_code == 200, member.text
    source = client.post("/v1/library/objects", headers=HEADERS, json={
        "title": "Collaborator private source", "owner_ref": collaborator, "source_scope": "my-library", "object_type": "source",
    }).json()
    shared = client.post(f"/v1/research/rooms/{room['room_id']}/evidence", headers=HEADERS, json={
        "room_id": room["room_id"], "object_id": source["object_id"], "state": "included", "contributed_by_ref": collaborator,
    })
    assert shared.status_code == 200, shared.text

    prepared = client.post("/v1/workspace/promotions/prepare", headers=HEADERS, json={
        "owner_ref": collaborator,
        "room_id": room["room_id"],
        "artifact_type": "citation-pack",
        "title": "Room citation pack",
        "selected_object_ids": [source["object_id"]],
    })
    assert prepared.status_code == 200, prepared.text
    packet = prepared.json()["packet"]
    assert packet["research_context"]["room_id"] == room["room_id"]
    assert packet["sources"][0]["owner_ref"] == collaborator
    assert packet["sources"][0]["source_scope"] == "my-library"
    assert packet["room_collaboration"]["governance"]["individual_positions_remain_attributed"] is True

    denied = client.post("/v1/workspace/promotions/prepare", headers=HEADERS, json={
        "owner_ref": f"wp-user-outsider-{suffix}", "room_id": room["room_id"], "artifact_type": "notebook",
    })
    assert denied.status_code == 403
