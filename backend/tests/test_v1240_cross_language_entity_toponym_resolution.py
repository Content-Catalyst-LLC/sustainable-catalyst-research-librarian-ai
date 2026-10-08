from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.contracts.cross_language_entity_toponym_resolution import *
from app.services.cross_language_entity_toponym_resolution import (
    CrossLanguageEntityToponymResolutionStore,
    capabilities,
    resolution_manifest,
)


def _store(tmp_path: Path) -> CrossLanguageEntityToponymResolutionStore:
    return CrossLanguageEntityToponymResolutionStore(sqlite_path=tmp_path / "resolution.sqlite3")


def _project(store: CrossLanguageEntityToponymResolutionStore):
    return store.create(CrossLanguageResolutionCreateRequest(
        actor_ref="identity:test-owner",
        title="Cross-language resolution study",
        project_ref="project:test",
        federation_ref="federation:test",
        multilingual_research_ref="multilingual:test",
        objective="Resolve multilingual identity and place ambiguity without automatic canonical promotion.",
    ))


def test_manifest_and_capabilities_define_v1240_boundary():
    m = resolution_manifest()
    c = capabilities()
    assert m["milestone"] == "12.4.0"
    assert m["runtime_authority"] == "python-fastapi-backend"
    assert m["wordpress_required"] is False
    assert m["scope"]["cross_language_entity_resolution"] is True
    assert m["scope"]["cross_language_toponym_resolution"] is True
    assert m["scope"]["automatic_identity_promotion"] is False
    assert m["scope"]["automatic_remote_geocoding"] is False
    assert m["governance"]["accepted_resolution_requires_human_review"] is True
    assert m["database_migration"] == "044_cross_language_entity_toponym_resolution.sql"
    assert m["next_boundary"] == "cross-language-citation-evidence-resolution"
    assert c["human_review_gate"] is True
    assert c["core_candidate_export"] is True


def test_entity_resolution_requires_human_review(tmp_path):
    store = _store(tmp_path)
    rid = _project(store)["resolution_id"]
    record = store.add_entity_mention(rid, EntityMentionAddRequest(
        actor_ref="identity:test-owner",
        surface_form="محمد علی جناح",
        original_script="محمد علی جناح",
        language_profile_ref="lang:ur-Arab",
        source_ref="source:archive:1",
        local_context="Founder context.",
    ))
    mention_id = record["entity_mentions"][-1]["mention_id"]
    record = store.add_entity_candidate(rid, EntityCandidateAddRequest(
        actor_ref="identity:test-owner",
        mention_id=mention_id,
        candidate_entity_ref="entity:muhammad-ali-jinnah",
        canonical_label="Muhammad Ali Jinnah",
        native_labels=["محمد علی جناح"],
        language_profile_refs=["lang:ur-Arab", "lang:en-Latn"],
        basis=["alias-match", "context-match"],
        descriptive_score=0.95,
        source_evidence_refs=["evidence:1"],
    ))
    candidate_id = record["entity_candidates"][-1]["candidate_id"]
    with pytest.raises(ValueError, match="human_reviewed"):
        store.resolve_entity(rid, EntityResolutionDecisionRequest(
            actor_ref="identity:test-owner",
            mention_id=mention_id,
            candidate_id=candidate_id,
            decision="accepted",
            confidence=0.95,
            human_reviewed=False,
        ))
    record = store.resolve_entity(rid, EntityResolutionDecisionRequest(
        actor_ref="identity:test-owner",
        mention_id=mention_id,
        candidate_id=candidate_id,
        decision="accepted",
        confidence=0.95,
        human_reviewed=True,
        reviewer_ref="identity:reviewer",
        rationale="Original-script, source identity and contextual evidence align.",
        evidence_refs=["evidence:1"],
    ))
    decision = record["entity_resolutions"][-1]
    assert decision["canonical_identity_promoted"] is False
    assert decision["core_promotion_requires_explicit_governed_action"] is True


def test_toponym_resolution_preserves_competing_historical_candidates(tmp_path):
    store = _store(tmp_path)
    rid = _project(store)["resolution_id"]
    record = store.add_toponym_mention(rid, ToponymMentionAddRequest(
        actor_ref="identity:test-owner",
        surface_form="Londonderry",
        original_script="Londonderry",
        language_profile_ref="lang:en-Latn",
        source_ref="source:historical:map",
        temporal_context="Historical map context",
        jurisdiction_context="Northern Ireland",
    ))
    mention_id = record["toponym_mentions"][-1]["mention_id"]
    ids = []
    for ref, label, score in [
        ("place:derry-londonderry", "Derry / Londonderry", 0.88),
        ("place:other-londonderry", "Londonderry candidate", 0.30),
    ]:
        record = store.add_toponym_candidate(rid, ToponymCandidateAddRequest(
            actor_ref="identity:test-owner",
            mention_id=mention_id,
            candidate_place_ref=ref,
            canonical_label=label,
            jurisdiction="Northern Ireland",
            historical_jurisdiction="historical-context-preserved",
            basis=["alias-match", "geographic-match"],
            descriptive_score=score,
            source_evidence_refs=["evidence:map:1"],
        ))
        ids.append(record["toponym_candidates"][-1]["candidate_id"])
    record = store.resolve_toponym(rid, ToponymResolutionDecisionRequest(
        actor_ref="identity:test-owner",
        mention_id=mention_id,
        candidate_id=ids[0],
        decision="accepted",
        confidence=0.88,
        human_reviewed=True,
        reviewer_ref="identity:reviewer",
        rationale="Context supports candidate while preserving competing names.",
        evidence_refs=["evidence:map:1"],
        preserve_competing_candidates=True,
    ))
    decision = record["toponym_resolutions"][-1]
    assert decision["canonical_place_promoted"] is False
    assert decision["competing_candidates_preserved"] is True
    assert len(record["toponym_candidates"]) == 2


def test_alias_alignment_preserves_transformation_provenance(tmp_path):
    store = _store(tmp_path)
    rid = _project(store)["resolution_id"]
    record = store.add_alias_alignment(rid, AliasAlignmentAddRequest(
        actor_ref="identity:test-owner",
        target_type="entity",
        target_ref="entity:test",
        representation="Aleksandr Pushkin",
        alias_kind="transliteration",
        language_profile_ref="lang:ru-Cyrl",
        script_ref="script:Cyrl",
        source_ref="source:bibliographic:1",
        transformation_refs=["transform:iso-9"],
        provenance_note="Romanized representation derived from Cyrillic source identity.",
    ))
    alias = record["alias_alignments"][-1]
    assert alias["representation_is_provenanced"] is True
    assert alias["representation_is_not_automatic_identity_equivalence"] is True


def test_snapshot_readiness_and_core_candidate_preserve_governance(tmp_path):
    store = _store(tmp_path)
    rid = _project(store)["resolution_id"]
    readiness = store.readiness(rid)
    assert readiness["canonical_promotion_performed"] is False
    core = store.core_candidate(rid)
    assert core["automatic_canonical_identity_promotion"] is False
    assert core["promotion_requires_explicit_core_write"] is True
    snapshot = store.freeze_snapshot(CrossLanguageResolutionSnapshotRequest(
        actor_ref="identity:test-owner",
        resolution_id=rid,
        label="v12.4-test-snapshot",
    ))
    assert len(snapshot["snapshot_hash"]) == 64
    assert snapshot["governance"]["snapshot_preserves_competing_candidates"] is True


def test_routes_auth_health_and_current_boundary(tmp_path):
    from app.services import cross_language_entity_toponym_resolution as service
    service._store = CrossLanguageEntityToponymResolutionStore(sqlite_path=tmp_path / "api-resolution.sqlite3")
    from app.main import app
    client = TestClient(app)
    paths = {getattr(route, "path", "") for route in app.routes}
    prefix = "/v1/research-librarian/cross-language-entity-toponym-resolution"
    assert prefix + "/manifest" in paths
    assert prefix + "/capabilities" in paths
    assert prefix + "/projects" in paths
    public = client.get(prefix + "/manifest")
    assert public.status_code == 200
    assert public.json()["data"]["milestone"] == "12.4.0"
    assert client.get(prefix + "/capabilities").status_code == 401
    cap = client.get(prefix + "/capabilities", headers={"X-SC-RL-Key": "test-key"})
    assert cap.status_code == 200
    health = client.get("/health")
    assert health.status_code == 200
    h = health.json()
    assert h["version"] == "12.4.0"
    assert h["cross_language_entity_toponym_resolution"] is True
    assert h["cross_language_resolution_runtime"] == "12.4.0"
    assert h["human_confirmed_entity_resolution"] is True
    assert h["toponym_ambiguity_preserved"] is True
    assert h["automatic_identity_promotion"] is False
    assert h["wordpress_required"] is False
    from app.services.independent_research_librarian_api import api_manifest, capabilities as independent_capabilities
    m = api_manifest()
    c = independent_capabilities()
    assert m["scope"]["cross_language_entity_toponym_resolution"] is True
    assert m["next_boundary"] == "cross-language-citation-evidence-resolution"
    assert c["milestone"] == "12.4.0"
    assert c["cross_language_entity_toponym_resolution"] is True


def test_v1230_global_source_federation_remains_historical_foundation():
    from app.services.global_source_federation_original_language import federation_manifest
    m = federation_manifest()
    assert m["milestone"] == "12.3.0"
    assert m["wordpress_required"] is False
    assert m["scope"]["automatic_entity_resolution"] is False
    assert m["scope"]["automatic_toponym_resolution"] is False
    assert m["next_boundary"] == "cross-language-entity-toponym-resolution"
