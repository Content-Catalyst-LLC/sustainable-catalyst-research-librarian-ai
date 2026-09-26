from __future__ import annotations

import os
import uuid

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.main import app
from app.collaboration import (
    normalize_room,
    normalize_member,
    normalize_room_evidence_state,
    normalize_room_question,
    normalize_room_disagreement,
    build_room_synthesis,
    prompt_room_synthesis,
)

client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _suffix() -> str:
    return uuid.uuid4().hex[:12]


def _room(owner: str, suffix: str, project_id: str = "") -> dict:
    response = client.post("/v1/research/rooms", headers=HEADERS, json={
        "title": f"Collaborative room {suffix}",
        "objective": "Compare evidence without erasing participant attribution.",
        "owner_ref": owner,
        "project_id": project_id,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_collaboration_contracts_keep_shared_state_attributed_and_not_evidence() -> None:
    room = normalize_room({"owner_ref": "wp-user-owner", "title": "Room"})
    owner = normalize_member({"room_id": room["room_id"], "member_ref": "wp-user-owner", "role": "owner"})
    evidence = normalize_room_evidence_state({"room_id": room["room_id"], "object_id": "object-1", "state": "included", "contributed_by_ref": "wp-user-owner"})
    question = normalize_room_question({"room_id": room["room_id"], "question": "What remains unresolved?", "created_by_ref": "wp-user-owner"})
    disagreement = normalize_room_disagreement({
        "room_id": room["room_id"],
        "statement": "The methods support different interpretations.",
        "created_by_ref": "wp-user-owner",
        "positions": [{"participant_ref": "wp-user-owner", "position": "Treat the estimates as non-equivalent."}],
    })
    synthesis = build_room_synthesis(room, [owner], [evidence], [question], [disagreement], [], [])
    prompt = prompt_room_synthesis(synthesis)

    assert room["governance"]["individual_and_shared_state_separate"] is True
    assert evidence["governance"]["room_inclusion_is_not_truth_judgment"] is True
    assert disagreement["governance"]["participant_positions_remain_attributed"] is True
    assert synthesis["governance"]["not_factual_verification"] is True
    assert prompt["schema"] == "sc-research-room-prompt/1.0"
    assert prompt["open_disagreements"][0]["positions"][0]["participant_ref"] == "wp-user-owner"
    assert "not verified evidence" in prompt["boundary_note"]


def test_room_membership_shared_evidence_questions_disagreements_and_synthesis() -> None:
    suffix = _suffix()
    owner = f"wp-user-room-owner-{suffix}"
    collaborator = f"wp-user-room-collab-{suffix}"
    room = _room(owner, suffix)

    member = client.post(f"/v1/research/rooms/{room['room_id']}/members", headers=HEADERS, json={
        "room_id": room["room_id"],
        "member_ref": collaborator,
        "display_name": "Collaborator",
        "role": "researcher",
        "status": "active",
        "added_by_ref": owner,
    })
    assert member.status_code == 200, member.text

    source = client.post("/v1/library/objects", headers=HEADERS, json={
        "title": "Collaborator source",
        "owner_ref": collaborator,
        "source_scope": "my-library",
        "object_type": "source",
        "provenance": {"source_record_id": f"room-record-{suffix}"},
    }).json()

    shared = client.post(f"/v1/research/rooms/{room['room_id']}/evidence", headers=HEADERS, json={
        "room_id": room["room_id"],
        "object_id": source["object_id"],
        "state": "included",
        "note": "Shared for comparison.",
        "contributed_by_ref": collaborator,
    })
    assert shared.status_code == 200, shared.text
    assert shared.json()["library_object"]["owner_ref"] == collaborator
    assert shared.json()["library_object"]["source_scope"] == "my-library"
    assert room["room_id"] in shared.json()["library_object"]["relationships"]["room_ids"]

    question = client.post(f"/v1/research/rooms/{room['room_id']}/questions", headers=HEADERS, json={
        "room_id": room["room_id"],
        "question": "Which methodology explains the difference?",
        "created_by_ref": collaborator,
    })
    assert question.status_code == 200, question.text

    disagreement = client.post(f"/v1/research/rooms/{room['room_id']}/disagreements", headers=HEADERS, json={
        "room_id": room["room_id"],
        "statement": "The team has two interpretations of the source.",
        "created_by_ref": owner,
        "linked_object_ids": [source["object_id"]],
        "positions": [{"participant_ref": owner, "position": "Interpretation A"}],
    })
    assert disagreement.status_code == 200, disagreement.text
    disagreement_id = disagreement.json()["disagreement_id"]

    second_position = client.post(f"/v1/research/rooms/{room['room_id']}/disagreements", headers=HEADERS, json={
        "disagreement_id": disagreement_id,
        "room_id": room["room_id"],
        "statement": "The team has two interpretations of the source.",
        "created_by_ref": collaborator,
        "linked_object_ids": [source["object_id"]],
        "positions": [{"participant_ref": collaborator, "position": "Interpretation B"}],
    })
    assert second_position.status_code == 200, second_position.text
    assert [p["participant_ref"] for p in second_position.json()["positions"]] == [owner, collaborator]

    impersonation = client.post(f"/v1/research/rooms/{room['room_id']}/disagreements", headers=HEADERS, json={
        "disagreement_id": disagreement_id,
        "room_id": room["room_id"],
        "statement": "The team has two interpretations of the source.",
        "created_by_ref": collaborator,
        "positions": [{"participant_ref": owner, "position": "Pretend to speak for owner"}],
    })
    assert impersonation.status_code == 403

    synthesis = client.get(f"/v1/research/rooms/{room['room_id']}/synthesis?member_ref={owner}", headers=HEADERS)
    assert synthesis.status_code == 200, synthesis.text
    body = synthesis.json()
    assert body["schema"] == "sc-research-room-synthesis/1.0"
    assert body["counts"]["members"] == 2
    assert body["counts"]["evidence_states"]["included"] == 1
    assert len(body["open_questions"]) == 1
    assert len(body["open_disagreements"]) == 1
    assert body["open_disagreements"][0]["positions"][1]["participant_ref"] == collaborator
    assert body["prompt_context"]["boundary_note"].startswith("Research Room data is collaborative workflow metadata")


def test_room_context_resolves_cross_member_sources_and_carries_room_prompt_into_ask() -> None:
    suffix = _suffix()
    owner = f"wp-user-room-context-owner-{suffix}"
    collaborator = f"wp-user-room-context-collab-{suffix}"
    room = _room(owner, suffix)
    client.post(f"/v1/research/rooms/{room['room_id']}/members", headers=HEADERS, json={
        "room_id": room["room_id"], "member_ref": collaborator, "role": "researcher", "status": "active", "added_by_ref": owner,
    })
    source = client.post("/v1/library/objects", headers=HEADERS, json={
        "title": "Cross-member room source",
        "owner_ref": collaborator,
        "source_scope": "my-library",
        "object_type": "source",
        "provenance": {"source_record_id": f"missing-room-record-{suffix}"},
    }).json()
    client.post(f"/v1/research/rooms/{room['room_id']}/evidence", headers=HEADERS, json={
        "room_id": room["room_id"], "object_id": source["object_id"], "state": "proposed", "contributed_by_ref": collaborator,
    })
    client.post(f"/v1/research/rooms/{room['room_id']}/questions", headers=HEADERS, json={
        "room_id": room["room_id"], "question": "What source would resolve this?", "created_by_ref": owner,
    })
    context = client.post("/v1/research/contexts", headers=HEADERS, json={
        "title": "Room context",
        "owner_ref": owner,
        "scopes": ["current-research-room"],
        "room_id": room["room_id"],
        "active": True,
    })
    assert context.status_code == 200, context.text
    resolved = client.get(f"/v1/research/contexts/{context.json()['context_id']}/resolve", headers=HEADERS)
    assert resolved.status_code == 200, resolved.text
    rbody = resolved.json()
    ids = [item["object_id"] for item in rbody["objects"]]
    assert source["object_id"] in ids
    assert rbody["prompt_context"]["room_collaboration"]["room_id"] == room["room_id"]
    assert rbody["prompt_context"]["room_collaboration"]["open_questions"][0]["created_by_ref"] == owner

    ask = client.post("/v1/ask", headers=HEADERS, json={
        "question": "What evidence is available in the room?",
        "research_context": rbody["prompt_context"],
    })
    assert ask.status_code == 200, ask.text
    abody = ask.json()
    assert abody["research_context"]["room_collaboration"]["room_id"] == room["room_id"]
    assert abody["provenance"]["room_collaboration"]["participant_attribution"] is True
    assert abody["provenance"]["room_collaboration"]["not_evidence"] is True
    activity = client.get(f"/v1/research/rooms/{room['room_id']}/activity?member_ref={owner}", headers=HEADERS).json()["activities"]
    assert any(item["event_type"] == "search" and "What evidence is available" in item["note"] for item in activity)


def test_viewer_is_read_only_but_can_view_synthesis() -> None:
    suffix = _suffix()
    owner = f"wp-user-room-view-owner-{suffix}"
    viewer = f"wp-user-room-viewer-{suffix}"
    room = _room(owner, suffix)
    client.post(f"/v1/research/rooms/{room['room_id']}/members", headers=HEADERS, json={
        "room_id": room["room_id"], "member_ref": viewer, "role": "viewer", "status": "active", "added_by_ref": owner,
    })
    source = client.post("/v1/library/objects", headers=HEADERS, json={"title": "Viewer source", "owner_ref": viewer, "source_scope": "my-library"}).json()
    denied = client.post(f"/v1/research/rooms/{room['room_id']}/evidence", headers=HEADERS, json={
        "room_id": room["room_id"], "object_id": source["object_id"], "state": "proposed", "contributed_by_ref": viewer,
    })
    assert denied.status_code == 403
    allowed = client.get(f"/v1/research/rooms/{room['room_id']}/synthesis?member_ref={viewer}", headers=HEADERS)
    assert allowed.status_code == 200


def test_project_backup_carries_collaborative_room_state() -> None:
    suffix = _suffix()
    owner = f"wp-user-room-backup-owner-{suffix}"
    collaborator = f"wp-user-room-backup-collab-{suffix}"
    project = client.post("/v1/projects", headers=HEADERS, json={"title": f"Room backup {suffix}", "owner_ref": owner}).json()
    room = _room(owner, suffix, project["project_id"])
    client.post(f"/v1/research/rooms/{room['room_id']}/members", headers=HEADERS, json={
        "room_id": room["room_id"], "member_ref": collaborator, "role": "researcher", "status": "active", "added_by_ref": owner,
    })
    source = client.post("/v1/library/objects", headers=HEADERS, json={"title": "Backup shared source", "owner_ref": collaborator, "source_scope": "my-library"}).json()
    client.post(f"/v1/research/rooms/{room['room_id']}/evidence", headers=HEADERS, json={
        "room_id": room["room_id"], "object_id": source["object_id"], "state": "included", "contributed_by_ref": collaborator,
    })
    client.post(f"/v1/research/rooms/{room['room_id']}/questions", headers=HEADERS, json={
        "room_id": room["room_id"], "question": "Backup this shared question?", "created_by_ref": owner,
    })

    backup = client.post(f"/v1/projects/{project['project_id']}/backup", headers=HEADERS, json={})
    assert backup.status_code == 200, backup.text
    room_bundles = backup.json()["payload"]["research_rooms"]
    assert len(room_bundles) == 1
    assert room_bundles[0]["members"]
    assert room_bundles[0]["evidence_states"]
    assert room_bundles[0]["questions"]
    assert any(item["object_id"] == source["object_id"] for item in backup.json()["payload"]["library_objects"])

    dry = client.post("/v1/platform/backups/import", headers=HEADERS, json={"envelope": backup.json(), "dry_run": True})
    assert dry.status_code == 200, dry.text
    assert dry.json()["counts"]["research_rooms"] == 1


def test_platform_api_advertises_v750_room_contracts() -> None:
    body = client.get("/v1/platform/api", headers=HEADERS).json()
    assert body["version"] == "10.5.0"
    assert body["schema"] == "sc-connected-research-api/2.0"
    assert "research-rooms" in body["resources"]
    assert "room-synthesis" in body["resources"]
    assert body["research_rooms"]["synthesis_schema"] == "sc-research-room-synthesis/1.0"
    assert body["research_rooms"]["participant_attribution"] is True
    assert body["research_rooms"]["individual_shared_state_separate"] is True
    assert body["research_rooms"]["not_evidence"] is True
