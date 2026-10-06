import os

os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")
os.environ.setdefault("SC_RL_IDENTITY_COOKIE_SECURE", "false")

from fastapi.testclient import TestClient

from app.contracts.global_source_federation_original_language import (
    FederationQueryPlanAddRequest,
    FederationRetrievalReceiptAddRequest,
    FederatedSourceAddRequest,
    GlobalSourceFederationCreateRequest,
    GlobalSourceFederationSnapshotRequest,
    OriginalLanguageAcquisitionAddRequest,
    SourceIngestionReceiptAddRequest,
    SourceTrustPreferenceAddRequest,
)
from app.services.global_source_federation_original_language import (
    GlobalSourceFederationOriginalLanguageStore,
    capabilities,
    federation_manifest,
)


def _store(tmp_path):
    return GlobalSourceFederationOriginalLanguageStore(sqlite_path=tmp_path / "federation.sqlite3")


def _project(store):
    return store.create(GlobalSourceFederationCreateRequest(
        actor_ref="identity:test-owner",
        title="Global original-language infrastructure sources",
        project_ref="project:test",
        multilingual_research_ref="multilingual:test",
        objective="Federate authoritative sources while preserving original-language provenance.",
    ))


def _source(store, federation_id, label="Eurostat"):
    record = store.add_source(federation_id, FederatedSourceAddRequest(
        actor_ref="identity:test-owner",
        label=label,
        source_type="intergovernmental",
        source_ref=f"source:{label.lower().replace(' ', '-')}",
        institution=label,
        jurisdiction="test",
        access_method="connector",
        connector_ref=f"connector:{label.lower().replace(' ', '-')}",
        language_profile_refs=["core:language:en", "core:language:fr"],
        collection_refs=["collection:statistics"],
        quality_signals={"institutional_provenance": True, "official_publication": True},
    ))
    return record["federated_sources"][-1]["federated_source_id"]


def test_manifest_and_capabilities_define_v1230_boundary():
    manifest = federation_manifest()
    caps = capabilities()
    assert manifest["milestone"] == "12.3.0"
    assert manifest["runtime_authority"] == "python-fastapi-backend"
    assert manifest["wordpress_required"] is False
    assert manifest["scope"]["global_source_federation"] is True
    assert manifest["scope"]["original_language_source_research"] is True
    assert manifest["scope"]["new_source_ingestion"] is True
    assert manifest["scope"]["source_quality_trust_separation"] is True
    assert manifest["scope"]["automatic_remote_crawling"] is False
    assert manifest["scope"]["automatic_entity_resolution"] is False
    assert manifest["scope"]["automatic_toponym_resolution"] is False
    assert manifest["scope"]["automatic_citation_resolution"] is False
    assert manifest["scope"]["automatic_evidence_resolution"] is False
    assert manifest["authority"]["knowledge_library_or_connector_ingestion_authority"] is True
    assert manifest["database_migration"] == "043_global_source_federation_original_language_research.sql"
    assert manifest["next_boundary"] == "cross-language-entity-toponym-resolution"
    assert caps["global_source_registry"] is True
    assert caps["quality_trust_separation"] is True


def test_source_quality_and_user_trust_are_separate(tmp_path):
    store = _store(tmp_path)
    federation_id = _project(store)["federation_id"]
    source_id = _source(store, federation_id)
    record = store.set_source_trust_preference(federation_id, SourceTrustPreferenceAddRequest(
        actor_ref="identity:test-owner",
        user_ref="identity:test-owner",
        federated_source_id=source_id,
        preference="trusted",
        rationale="Explicit user choice for this project.",
    ))
    source = record["federated_sources"][0]
    pref = record["source_trust_preferences"][0]
    assert source["quality_signals"]["official_publication"] is True
    assert source["quality_signals_are_descriptive_not_trust"] is True
    assert source["user_trust_not_inferred"] is True
    assert pref["preference"] == "trusted"
    assert pref["user_preference_not_source_quality"] is True
    lineage = store.lineage(federation_id)
    assert lineage["governance"]["source_quality_and_user_trust_are_separate"] is True


def test_original_language_acquisition_and_ingestion_lineage(tmp_path):
    store = _store(tmp_path)
    federation_id = _project(store)["federation_id"]
    source_id = _source(store, federation_id, "National Archive")
    record = store.add_original_language_acquisition(federation_id, OriginalLanguageAcquisitionAddRequest(
        actor_ref="identity:test-owner",
        federated_source_id=source_id,
        external_record_ref="archive:record:fa-001",
        source_locator="box:12/folder:4/page:2",
        language_profile_ref="core:language:fa-Arab",
        original_content_ref="library:object:fa-001",
        original_content_hash="sha256:original-fa-001",
        acquisition_method="connector",
        acquisition_execution_ref="library:ingestion-run:1",
        extraction_lineage_refs=["library:extraction:1"],
    ))
    acquisition = record["original_language_acquisitions"][0]
    assert acquisition["original_language"] is True
    assert acquisition["derived_representation"] is False
    assert acquisition["translation_not_substituted_for_source"] is True
    record = store.add_ingestion_receipt(federation_id, SourceIngestionReceiptAddRequest(
        actor_ref="identity:test-owner",
        acquisition_id=acquisition["acquisition_id"],
        execution_ref="library:ingestion-run:1",
        status="accepted",
        normalized_record_ref="library:normalized:fa-001",
        normalized_record_hash="sha256:normalized-fa-001",
        transformation_refs=["library:ocr:1", "library:normalization:1"],
        diagnostics={"records": 1},
    ))
    receipt = record["ingestion_receipts"][0]
    assert receipt["receipt_is_provenance_not_quality_verdict"] is True
    assert receipt["ingestion_execution_may_be_external"] is True


def test_query_and_retrieval_receipts_are_reviewable(tmp_path):
    store = _store(tmp_path)
    federation_id = _project(store)["federation_id"]
    a = _source(store, federation_id, "Source A")
    b = _source(store, federation_id, "Source B")
    record = store.add_query_plan(federation_id, FederationQueryPlanAddRequest(
        actor_ref="identity:test-owner",
        label="Original-language-first federation query",
        query_ref="session:query:fa-1",
        source_language_profile_ref="core:language:fa-Arab",
        target_federated_source_ids=[a, b],
        target_language_profile_refs=["core:language:fa-Arab", "core:language:en-Latn"],
        strategy="original-language-first",
        derived_query_refs=["workspace:query:en-1"],
        retrieval_constraints={"jurisdictions": ["IR", "EU"]},
    ))
    query_plan = record["query_plans"][0]
    assert query_plan["original_query_preserved"] is True
    assert query_plan["remote_execution_performed_by_recording_method"] is False
    record = store.add_retrieval_receipt(federation_id, FederationRetrievalReceiptAddRequest(
        actor_ref="identity:test-owner",
        query_plan_id=query_plan["query_plan_id"],
        execution_ref="connector:federation-run:1",
        result_refs=["external:result:1", "external:result:2"],
        result_federated_source_ids=[a, b],
        result_language_profile_refs=["core:language:fa-Arab", "core:language:en-Latn"],
        diagnostics={"candidate_count": 22},
    ))
    receipt = record["retrieval_receipts"][0]
    assert receipt["receipt_is_observation_not_relevance_truth"] is True
    assert receipt["source_trust_not_inferred_from_retrieval"] is True


def test_snapshot_candidates_preserve_authority_boundaries(tmp_path):
    store = _store(tmp_path)
    federation_id = _project(store)["federation_id"]
    source_id = _source(store, federation_id)
    store.add_original_language_acquisition(federation_id, OriginalLanguageAcquisitionAddRequest(
        actor_ref="identity:test-owner",
        federated_source_id=source_id,
        external_record_ref="source:record:1",
        language_profile_ref="core:language:de-Latn",
        original_content_ref="library:object:de-1",
        acquisition_method="connector",
    ))
    readiness = store.readiness(federation_id)
    assert readiness["ready_for_global_source_research"] is True
    assert readiness["governance"]["readiness_is_structural_not_source_quality_judgment"] is True
    multilingual = store.multilingual_candidate(federation_id)
    assert multilingual["automatic_multilingual_write"] is False
    assert multilingual["automatic_translation"] is False
    core = store.core_candidate(federation_id)
    assert core["platform_core_authority_required"] is True
    assert core["automatic_core_write"] is False
    assert core["automatic_entity_resolution"] is False
    assert core["automatic_toponym_resolution"] is False
    snapshot = store.freeze_snapshot(GlobalSourceFederationSnapshotRequest(
        actor_ref="identity:test-owner", federation_id=federation_id,
    ))
    assert len(snapshot["snapshot_hash"]) == 64
    assert snapshot["governance"]["snapshot_preserves_quality_trust_separation"] is True


def test_routes_auth_health_and_current_boundary(tmp_path):
    from app.services import global_source_federation_original_language as federation_service
    federation_service._store = GlobalSourceFederationOriginalLanguageStore(sqlite_path=tmp_path / "api-federation.sqlite3")
    from app.main import app
    client = TestClient(app)
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/v1/research-librarian/global-source-federation/manifest" in paths
    assert "/v1/research-librarian/global-source-federation/capabilities" in paths
    assert "/v1/research-librarian/global-source-federation/projects" in paths
    public = client.get("/v1/research-librarian/global-source-federation/manifest")
    assert public.status_code == 200
    assert public.json()["data"]["milestone"] == "12.3.0"
    assert client.get("/v1/research-librarian/global-source-federation/capabilities").status_code == 401
    cap = client.get("/v1/research-librarian/global-source-federation/capabilities", headers={"X-SC-RL-Key": "test-key"})
    assert cap.status_code == 200
    health = client.get("/health")
    assert health.status_code == 200
    payload = health.json()
    assert payload["version"] == "12.3.0"
    assert payload["global_source_federation"] is True
    assert payload["global_source_federation_runtime"] == "12.3.0"
    assert payload["original_language_source_research"] is True
    assert payload["source_quality_trust_separation"] is True
    assert payload["wordpress_required"] is False
    from app.services.independent_research_librarian_api import api_manifest, capabilities as independent_capabilities
    manifest = api_manifest()
    current = independent_capabilities()
    assert manifest["scope"]["global_source_federation"] is True
    assert manifest["scope"]["original_language_source_research"] is True
    assert manifest["next_boundary"] == "cross-language-entity-toponym-resolution"
    assert current["milestone"] == "12.3.0"
    assert current["global_source_federation"] is True


def test_v1220_multilingual_layer_remains_historical_foundation():
    from app.services.multilingual_cross_language_research import multilingual_manifest
    manifest = multilingual_manifest()
    assert manifest["milestone"] == "12.2.0"
    assert manifest["wordpress_required"] is False
    assert manifest["principles"]["analyze_original_language_first"] is True
    assert manifest["next_boundary"] == "global-source-federation-original-language-research"
