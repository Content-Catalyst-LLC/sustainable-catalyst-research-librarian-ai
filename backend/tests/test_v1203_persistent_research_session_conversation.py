import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")

from fastapi.testclient import TestClient

from app.contracts.persistent_research_session_conversation import (
    ResearchSessionCreateRequest,
    ResearchSessionTurnAddRequest,
    ResearchSessionContextBindRequest,
    ResearchSessionStateRequest,
    ResearchSessionSnapshotRequest,
    PERSISTENT_RESEARCH_SESSION_SNAPSHOT_SCHEMA,
)
from app.services.persistent_research_session_conversation import (
    PersistentResearchSessionStore,
    capabilities,
)

def test_session_persists_across_store_instances(tmp_path):
    db=tmp_path/"sessions.sqlite3"
    s1=PersistentResearchSessionStore(db)
    session=s1.create(ResearchSessionCreateRequest(title="Durable research",client_ref="client-a"))
    sid=session["session_id"]
    s1.add_turn(sid,ResearchSessionTurnAddRequest(role="user",content="First research question"))
    s1.add_turn(sid,ResearchSessionTurnAddRequest(role="assistant",content="Grounded answer",evidence_refs=["evidence-1"]))

    s2=PersistentResearchSessionStore(db)
    loaded=s2.get(sid)
    turns=s2.turns(sid)
    assert loaded["turn_count"]==2
    assert [x["role"] for x in turns]==["user","assistant"]
    assert turns[1]["previous_turn_hash"]==turns[0]["record_hash"]

def test_client_ref_is_not_identity_or_authorization(tmp_path):
    s=PersistentResearchSessionStore(tmp_path/"sessions.sqlite3")
    session=s.create(ResearchSessionCreateRequest(client_ref="browser-local-ref"))
    assert session["governance"]["client_ref_is_identity"] is False
    assert session["governance"]["client_ref_grants_authorization"] is False
    assert session["governance"]["identity_and_access_deferred_to_v12_0_5"] is True

def test_context_binding_state_reset_and_snapshot(tmp_path):
    s=PersistentResearchSessionStore(tmp_path/"sessions.sqlite3")
    session=s.create(ResearchSessionCreateRequest(title="Context session"))
    sid=session["session_id"]
    s.add_turn(sid,ResearchSessionTurnAddRequest(role="user",content="Question"))
    s.bind_context(sid,ResearchSessionContextBindRequest(research_context_ref="context-123",note="Bind saved context"))
    paused=s.set_state(sid,ResearchSessionStateRequest(state="paused",note="Pause"))
    assert paused["state"]=="paused"
    assert paused["research_context_ref"]=="context-123"
    removed=s.clear_turns(sid)
    assert removed==1
    assert s.get(sid)["turn_count"]==0
    snap=s.freeze_snapshot(sid,ResearchSessionSnapshotRequest(actor_ref="architect"))
    assert snap["schema"]==PERSISTENT_RESEARCH_SESSION_SNAPSHOT_SCHEMA
    assert len(snap["snapshot_hash"])==64
    assert snap["governance"]["wordpress_required"] is False

def test_closed_session_rejects_new_turns(tmp_path):
    s=PersistentResearchSessionStore(tmp_path/"sessions.sqlite3")
    session=s.create(ResearchSessionCreateRequest())
    sid=session["session_id"]
    s.set_state(sid,ResearchSessionStateRequest(state="closed"))
    try:
        s.add_turn(sid,ResearchSessionTurnAddRequest(role="user",content="Should fail"))
    except ValueError as exc:
        assert "closed or archived" in str(exc)
    else:
        raise AssertionError("expected closed session to reject turns")

def test_history_for_generation_uses_recent_turns(tmp_path):
    s=PersistentResearchSessionStore(tmp_path/"sessions.sqlite3")
    session=s.create(ResearchSessionCreateRequest())
    sid=session["session_id"]
    for i in range(8):
        s.add_turn(sid,ResearchSessionTurnAddRequest(role="user" if i%2==0 else "assistant",content=f"turn-{i}"))
    history=s.history_for_generation(sid,2)
    assert [x["content"] for x in history]==["turn-4","turn-5","turn-6","turn-7"]

def test_independent_api_session_routes():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
      "/v1/research-librarian/sessions",
      "/v1/research-librarian/sessions/{session_id}",
      "/v1/research-librarian/sessions/{session_id}/turns",
      "/v1/research-librarian/sessions/{session_id}/context",
      "/v1/research-librarian/sessions/{session_id}/state",
      "/v1/research-librarian/sessions/{session_id}/reset",
      "/v1/research-librarian/sessions/{session_id}/summary",
      "/v1/research-librarian/sessions/{session_id}/snapshots/freeze",
    }
    assert not(required-paths)
    client=TestClient(app)
    assert client.get("/v1/research-librarian/sessions").status_code in {401,503}
    h={"X-SC-RL-Key":"test-key"}
    created=client.post("/v1/research-librarian/sessions",headers=h,json={"title":"API durable session","client_ref":"client-api"})
    assert created.status_code==200
    session=created.json()["data"]
    sid=session["session_id"]
    turn=client.post(f"/v1/research-librarian/sessions/{sid}/turns",headers=h,json={"role":"user","content":"Persistent question"})
    assert turn.status_code==200
    listed=client.get(f"/v1/research-librarian/sessions/{sid}/turns",headers=h)
    assert listed.status_code==200
    assert listed.json()["data"]["count"]==1

def test_capabilities():
    c=capabilities()
    assert c["milestone"]=="12.0.3"
    assert c["persistent_sessions"] is True
    assert c["persistent_conversations"] is True
    assert c["legacy_ask_persistence"] is True
    assert c["wordpress_required"] is False
    assert c["client_ref_is_identity"] is False
    assert c["identity_sessions"] is False
