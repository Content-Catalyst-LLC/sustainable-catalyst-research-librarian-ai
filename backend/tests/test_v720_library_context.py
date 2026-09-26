from __future__ import annotations

import os
import uuid

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")

from fastapi.testclient import TestClient

from app.library_context import sanitize_inline_context
from app.main import app


client = TestClient(app)
HEADERS = {"X-SC-RL-Key": "test-key"}


def _suffix() -> str:
    return uuid.uuid4().hex[:12]


def test_library_object_model_declares_library_native_types_and_boundaries() -> None:
    response = client.get("/v1/library/object-model", headers=HEADERS)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == "10.3.0"
    assert body["schema"] == "sc-research-library-object-model/1.0"
    required = {
        "source",
        "publication",
        "recommendation",
        "saved-search",
        "watchlist",
        "research-queue-item",
        "source-bundle",
        "research-room",
        "pathway",
        "workspace-notebook",
        "workspace-evidence",
    }
    assert required.issubset(set(body["object_types"]))
    assert body["context_scopes"]["my-library"]["boundary"] == "private-personal"
    assert body["context_scopes"]["sustainable-catalyst-collection"]["boundary"] == "public-editorial"


def test_library_objects_link_to_projects_without_losing_source_identity() -> None:
    suffix = _suffix()
    owner = f"wp-user-v720-{suffix}"
    project = client.post(
        "/v1/projects",
        headers=HEADERS,
        json={"title": f"Library alignment {suffix}", "owner_ref": owner},
    ).json()
    obj = client.post(
        "/v1/library/objects",
        headers=HEADERS,
        json={
            "object_type": "source-bundle",
            "title": "Climate evidence bundle",
            "owner_ref": owner,
            "source_scope": "my-library",
            "tags": ["climate", "evidence"],
            "provenance": {
                "origin_system": "knowledge-library",
                "origin_object_id": f"bundle-{suffix}",
                "provider": "Sustainable Catalyst Library",
            },
        },
    )
    assert obj.status_code == 200, obj.text
    saved = obj.json()
    assert saved["schema"] == "sc-research-library-object/1.0"
    assert saved["source_scope"] == "my-library"
    assert saved["provenance"]["origin_object_id"] == f"bundle-{suffix}"

    linked = client.post(
        f"/v1/library/objects/{saved['object_id']}/projects/{project['project_id']}",
        headers=HEADERS,
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["project_link"]["entity_type"] == "library-object-ref"

    project_objects = client.get(
        f"/v1/projects/{project['project_id']}/library-objects", headers=HEADERS
    ).json()["objects"]
    assert any(item["object_id"] == saved["object_id"] for item in project_objects)
    assert next(item for item in project_objects if item["object_id"] == saved["object_id"])["source_scope"] == "my-library"


def test_context_resolution_separates_personal_project_room_and_editorial_scopes() -> None:
    suffix = _suffix()
    owner = f"wp-user-v720-{suffix}"
    project = client.post(
        "/v1/projects", headers=HEADERS, json={"title": f"Context project {suffix}", "owner_ref": owner}
    ).json()

    personal = client.post(
        "/v1/library/objects",
        headers=HEADERS,
        json={
            "object_type": "recommendation",
            "title": "Personal recommendation",
            "owner_ref": owner,
            "source_scope": "my-library",
            "provenance": {"source_record_id": "post:personal-context"},
        },
    ).json()
    project_source = client.post(
        "/v1/library/objects",
        headers=HEADERS,
        json={
            "object_type": "source",
            "title": "Project evidence",
            "owner_ref": owner,
            "source_scope": "my-library",
            "relationships": {"project_ids": [project["project_id"]]},
            "provenance": {"source_record_id": "post:project-context"},
        },
    ).json()
    research_room = client.post(
        "/v1/research/rooms",
        headers=HEADERS,
        json={"title": f"Room {suffix}", "objective": "v7.2 compatibility room", "owner_ref": owner},
    ).json()
    room = client.post(
        "/v1/library/objects",
        headers=HEADERS,
        json={
            "object_type": "research-room",
            "title": "Room evidence",
            "owner_ref": owner,
            "source_scope": "current-research-room",
            "relationships": {"room_ids": [research_room["room_id"]]},
        },
    ).json()

    context = client.post(
        "/v1/research/contexts",
        headers=HEADERS,
        json={
            "title": "Bounded mixed context",
            "owner_ref": owner,
            "scopes": ["my-library", "current-project", "current-research-room"],
            "project_id": project["project_id"],
            "room_id": research_room["room_id"],
            "active": True,
        },
    )
    assert context.status_code == 200, context.text
    context_id = context.json()["context_id"]
    resolution = client.get(f"/v1/research/contexts/{context_id}/resolve", headers=HEADERS)
    assert resolution.status_code == 200, resolution.text
    body = resolution.json()
    ids = {item["object_id"] for item in body["objects"]}
    assert {personal["object_id"], project_source["object_id"], room["object_id"]}.issubset(ids)
    assert body["counts_by_scope"]["my-library"] >= 2
    assert body["counts_by_scope"]["current-research-room"] >= 1
    assert body["prompt_context"]["context_id"] == context_id
    assert "not editorial endorsement" in body["prompt_context"]["boundary_note"]


def test_only_one_context_is_active_per_owner_and_payload_state_matches_index() -> None:
    suffix = _suffix()
    owner = f"wp-user-v720-{suffix}"
    first = client.post(
        "/v1/research/contexts",
        headers=HEADERS,
        json={"title": "First context", "owner_ref": owner, "scopes": ["my-library"], "active": True},
    ).json()
    second = client.post(
        "/v1/research/contexts",
        headers=HEADERS,
        json={"title": "Second context", "owner_ref": owner, "scopes": ["sustainable-catalyst-collection"], "active": True},
    ).json()
    listing = client.get(f"/v1/research/contexts?owner_ref={owner}", headers=HEADERS).json()
    assert listing["active"]["context_id"] == second["context_id"]
    by_id = {item["context_id"]: item for item in listing["contexts"]}
    assert by_id[first["context_id"]]["active"] is False
    assert by_id[second["context_id"]]["active"] is True


def test_inline_context_is_bounded_and_ask_echoes_authorized_context_metadata() -> None:
    raw = {
        "context_id": "context-v720-test",
        "title": "My source set",
        "scopes": ["my-library"],
        "objects": [
            {
                "object_id": f"source-{index}",
                "object_type": "source",
                "title": f"Source {index}",
                "source_scope": "my-library" if index < 50 else "made-up-scope",
                "source_record_id": f"post:{index}",
            }
            for index in range(80)
        ],
    }
    clean = sanitize_inline_context(raw)
    assert len(clean["objects"]) == 50
    assert clean["objects"][0]["source_scope"] == "my-library"
    assert clean["fingerprint"]

    response = client.post(
        "/v1/ask",
        headers=HEADERS,
        json={"question": "What does the indexed evidence say about this research topic?", "research_context": clean},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["research_context"]["context_id"] == "context-v720-test"
    assert body["workspace"]["schema"] == "sc-research-librarian-public-workspace/3.0"
    assert body["workspace"]["research_context"]["object_count"] == 50
    assert body["provenance"]["research_context"]["object_count"] == 50
    assert body["retrieval_diagnostics"]["research_context_retrieval"]["enabled"] is True


def test_project_backup_carries_linked_library_objects() -> None:
    suffix = _suffix()
    owner = f"wp-user-v720-{suffix}"
    project = client.post(
        "/v1/projects", headers=HEADERS, json={"title": f"Backup context {suffix}", "owner_ref": owner}
    ).json()
    obj = client.post(
        "/v1/library/objects",
        headers=HEADERS,
        json={"object_type": "watchlist", "title": "Watch this", "owner_ref": owner, "source_scope": "my-library"},
    ).json()
    client.post(f"/v1/library/objects/{obj['object_id']}/projects/{project['project_id']}", headers=HEADERS)
    backup = client.post(f"/v1/projects/{project['project_id']}/backup", headers=HEADERS)
    assert backup.status_code == 200, backup.text
    envelope = backup.json()
    assert any(item["object_id"] == obj["object_id"] for item in envelope["payload"]["library_objects"])
    dry = client.post("/v1/platform/backups/import", headers=HEADERS, json={"envelope": envelope, "dry_run": True})
    assert dry.status_code == 200, dry.text
    assert dry.json()["counts"]["library_objects"] >= 1
