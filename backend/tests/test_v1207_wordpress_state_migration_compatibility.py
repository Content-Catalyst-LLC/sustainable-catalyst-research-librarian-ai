import os
from pathlib import Path
import tempfile

os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
os.environ.setdefault("SC_RL_IDENTITY_COOKIE_SECURE","false")

from fastapi.testclient import TestClient

from app.contracts.wordpress_state_migration import (
    WordPressMigrationPrepareRequest,
    WordPressMigrationCandidateInput,
    WordPressMigrationApplyRequest,
)
from app.services.wordpress_state_migration import (
    WordPressStateMigrationStore,
    migration_manifest,
)

def test_manifest_preserves_backend_authority_and_explicit_cutover():
    m=migration_manifest()
    assert m["milestone"]=="12.0.7"
    assert m["runtime_authority"]=="python-fastapi-backend"
    assert m["wordpress_required"] is False
    assert m["migration_mode"]=="explicit-prepare-apply"
    assert m["automatic_migration"] is False
    assert m["idempotency"]["durable_receipts"] is True
    assert m["idempotency"]["durable_compatibility_aliases"] is True
    assert m["governance"]["conflicts_fail_closed"] is True
    assert m["governance"]["legacy_state_not_deleted"] is True
    assert m["governance"]["compatibility_aliases_do_not_grant_access"] is True
    assert m["next_boundary"]=="neural-research-intelligence-foundation"

def test_prepare_classifies_owner_mapping_secret_payloads_and_compatibility(tmp_path):
    store=WordPressStateMigrationStore(sqlite_path=tmp_path/"migration.sqlite3")
    req=WordPressMigrationPrepareRequest(
        source_site="https://example.test/",
        source_instance="wordpress:1:test",
        actor_ref="",
        owner_map={"wp-user:7":"identity:rli-test-owner"},
        candidates=[
            WordPressMigrationCandidateInput(
                source_type="project",
                legacy_id="project-old",
                owner_key="wp-user:7",
                payload={"project_id":"project-old","title":"Legacy Project","objective":"Preserve me"},
            ),
            WordPressMigrationCandidateInput(
                source_type="persistent-session",
                legacy_id="session-old",
                owner_key="wp-user:8",
                payload={"session_id":"session-old","title":"Needs mapping"},
            ),
            WordPressMigrationCandidateInput(
                source_type="compatibility-record",
                legacy_id="option:legacy",
                payload={"mode":"legacy"},
            ),
            WordPressMigrationCandidateInput(
                source_type="compatibility-record",
                legacy_id="option:secret",
                payload={"api_key":"must-not-cross"},
            ),
        ],
    )
    prepared=store.prepare(req)
    by_id={x["legacy_id"]:x for x in prepared["candidates"]}
    assert by_id["project-old"]["classification"]=="migratable"
    assert by_id["project-old"]["mapped_owner_ref"]=="identity:rli-test-owner"
    assert by_id["session-old"]["classification"]=="blocked-owner-map"
    assert by_id["option:legacy"]["classification"]=="migratable"
    assert by_id["option:secret"]["classification"]=="blocked-secret-bearing"
    run=prepared["run"]
    assert run["migratable_count"]==2
    assert run["blocked_count"]==2
    assert run["compatibility_count"]==2

def test_compatibility_record_apply_is_idempotent_and_receipted(tmp_path):
    store=WordPressStateMigrationStore(sqlite_path=tmp_path/"migration.sqlite3")
    prepared=store.prepare(WordPressMigrationPrepareRequest(
        source_site="https://example.test/",
        source_instance="wordpress:1:test",
        candidates=[
            WordPressMigrationCandidateInput(
                source_type="compatibility-record",
                legacy_id="option:legacy",
                source_locator="wp-option:sc_rl_legacy",
                payload={"mode":"legacy","enabled":True},
            )
        ],
    ))
    run_id=prepared["run"]["run_id"]
    first=store.apply(run_id,WordPressMigrationApplyRequest(confirm=True,note="pytest"))
    assert not first["failures"]
    assert first["receipts"][0]["outcome"]=="applied"
    alias=store.resolve("https://example.test/","compatibility-record","option:legacy")
    assert alias is not None
    assert alias["target_type"]=="compatibility-record"
    assert alias["governance"]["alias_grants_access"] is False

    prepared2=store.prepare(WordPressMigrationPrepareRequest(
        source_site="https://example.test/",
        source_instance="wordpress:1:test",
        candidates=[
            WordPressMigrationCandidateInput(
                source_type="compatibility-record",
                legacy_id="option:legacy",
                source_locator="wp-option:sc_rl_legacy",
                payload={"mode":"legacy","enabled":True},
            )
        ],
    ))
    assert prepared2["candidates"][0]["classification"]=="duplicate"

def test_changed_legacy_record_conflicts_fail_closed(tmp_path):
    store=WordPressStateMigrationStore(sqlite_path=tmp_path/"migration.sqlite3")
    first=store.prepare(WordPressMigrationPrepareRequest(
        source_site="https://example.test/",
        candidates=[
            WordPressMigrationCandidateInput(
                source_type="compatibility-record",
                legacy_id="option:legacy",
                payload={"mode":"v1"},
            )
        ],
    ))
    store.apply(first["run"]["run_id"],WordPressMigrationApplyRequest(confirm=True))
    second=store.prepare(WordPressMigrationPrepareRequest(
        source_site="https://example.test/",
        candidates=[
            WordPressMigrationCandidateInput(
                source_type="compatibility-record",
                legacy_id="option:legacy",
                payload={"mode":"v2"},
            )
        ],
    ))
    assert second["candidates"][0]["classification"]=="conflict"
    try:
        store.apply(second["run"]["run_id"],WordPressMigrationApplyRequest(confirm=True))
        assert False,"conflict run should fail closed"
    except ValueError as exc:
        assert "conflicts" in str(exc).lower()

def test_persistent_turn_requested_id_is_idempotent():
    from app.services.persistent_research_session_conversation import PersistentResearchSessionStore
    from app.contracts.persistent_research_session_conversation import (
        ResearchSessionCreateRequest,
        ResearchSessionTurnAddRequest,
    )
    path=Path(tempfile.mkdtemp(prefix="sc-rl-v1207-session-"))/"session.sqlite3"
    store=PersistentResearchSessionStore(sqlite_path=path)
    session=store.create(
        ResearchSessionCreateRequest(title="Migrated"),
        requested_session_id="session-wp-test",
    )
    first=store.add_turn(
        session["session_id"],
        ResearchSessionTurnAddRequest(role="research-note",content="Legacy note"),
        requested_turn_id="turn-wp-test",
    )
    second=store.add_turn(
        session["session_id"],
        ResearchSessionTurnAddRequest(role="research-note",content="Legacy note"),
        requested_turn_id="turn-wp-test",
    )
    assert first["turn_id"]=="turn-wp-test"
    assert second["turn_id"]=="turn-wp-test"
    assert len(store.turns(session["session_id"]))==1

def test_api_routes_health_and_current_boundary(tmp_path):
    from app.services import wordpress_state_migration as migration_service
    migration_service._STORE=WordPressStateMigrationStore(sqlite_path=tmp_path/"api-migration.sqlite3")

    from app.main import app
    client=TestClient(app)

    manifest=client.get("/v1/research-librarian/wordpress-migration/manifest")
    assert manifest.status_code==200
    assert manifest.json()["data"]["milestone"]=="12.0.7"

    assert client.get("/v1/research-librarian/wordpress-migration/capabilities").status_code==401
    allowed=client.get(
        "/v1/research-librarian/wordpress-migration/capabilities",
        headers={"X-SC-RL-Key":"test-key"},
    )
    assert allowed.status_code==200
    assert allowed.json()["data"]["migration_table_version"]=="040"

    prepared=client.post(
        "/v1/research-librarian/wordpress-migration/prepare",
        headers={"X-SC-RL-Key":"test-key"},
        json={
            "source_site":"https://example.test/",
            "candidates":[
                {
                    "source_type":"compatibility-record",
                    "legacy_id":"option:api-test",
                    "payload":{"value":"safe"},
                }
            ],
        },
    )
    assert prepared.status_code==200
    run_id=prepared.json()["data"]["run"]["run_id"]

    not_confirmed=client.post(
        f"/v1/research-librarian/wordpress-migration/runs/{run_id}/apply",
        headers={"X-SC-RL-Key":"test-key"},
        json={"confirm":False},
    )
    assert not_confirmed.status_code==409

    applied=client.post(
        f"/v1/research-librarian/wordpress-migration/runs/{run_id}/apply",
        headers={"X-SC-RL-Key":"test-key"},
        json={"confirm":True},
    )
    assert applied.status_code==200

    health=client.get("/health").json()
    assert health["version"]=="12.0.8"
    assert health["wordpress_state_migration"] is True
    assert health["wordpress_state_migration_runtime"]=="12.0.7"
    assert health["wordpress_compatibility_aliases"] is True
    assert health["wordpress_required"] is False

def test_independent_api_advances_to_failure_certification_boundary():
    from app.services.independent_research_librarian_api import api_manifest,capabilities
    m=api_manifest()
    c=capabilities()
    assert m["scope"]["thin_wordpress_adapter"] is True
    assert m["scope"]["wordpress_state_migration"] is True
    assert m["next_boundary"]=="neural-research-intelligence-foundation"
    assert c["milestone"]=="12.0.8"
    assert c["wordpress_state_migration"] is True
