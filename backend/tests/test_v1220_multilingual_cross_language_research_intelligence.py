import os

os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
os.environ.setdefault("SC_RL_IDENTITY_COOKIE_SECURE","false")

from fastapi.testclient import TestClient

from app.contracts.multilingual_cross_language_research import (
    MultilingualResearchCreateRequest,
    LanguageProfileAddRequest,
    OriginalLanguageSourceTextAddRequest,
    DerivedLanguageRepresentationAddRequest,
    TextAlignmentAddRequest,
    CrossLanguageQueryPlanAddRequest,
    CrossLanguageRetrievalReceiptAddRequest,
    MultilingualResearchSnapshotRequest,
)
from app.services.multilingual_cross_language_research import (
    MultilingualCrossLanguageResearchStore,
    multilingual_manifest,
    capabilities,
)


def _store(tmp_path):
    return MultilingualCrossLanguageResearchStore(
        sqlite_path=tmp_path/"multilingual.sqlite3"
    )


def _project(store):
    return store.create(MultilingualResearchCreateRequest(
        actor_ref="identity:test-owner",
        title="Persian-English infrastructure research",
        project_ref="project:test",
        research_question_ref="rq:test",
        objective="Preserve original-language evidence and inspect derived cross-language representations.",
    ))


def _profile(store,rid,tag,name,script,direction="ltr"):
    rec=store.add_language_profile(rid,LanguageProfileAddRequest(
        actor_ref="identity:test-owner",
        language_tag=tag,
        language_name=name,
        script_code=script,
        direction=direction,
        identification_method="source-metadata",
    ))
    return rec["language_profiles"][-1]["language_profile_id"]


def test_manifest_preserves_roadmap_boundaries():
    m=multilingual_manifest()
    c=capabilities()
    assert m["milestone"]=="12.2.0"
    assert m["runtime_authority"]=="python-fastapi-backend"
    assert m["wordpress_required"] is False
    assert m["principles"]["analyze_original_language_first"] is True
    assert m["principles"]["translation_is_derived_representation"] is True
    assert m["principles"]["transliteration_is_derived_representation"] is True
    assert m["scope"]["global_source_federation"] is False
    assert m["scope"]["new_source_ingestion"] is False
    assert m["scope"]["automatic_entity_resolution"] is False
    assert m["scope"]["automatic_citation_resolution"] is False
    assert m["scope"]["automatic_evidence_resolution"] is False
    assert m["database_migration"]=="042_multilingual_cross_language_research_intelligence.sql"
    assert m["next_boundary"]=="global-source-federation-original-language-research"
    assert c["parallel_text_alignment"] is True
    assert c["cross_language_query_plans"] is True
    assert c["cross_language_retrieval_receipts"] is True


def test_original_language_derived_representation_and_alignment_lineage(tmp_path):
    store=_store(tmp_path)
    project=_project(store)
    rid=project["multilingual_research_id"]

    fa=_profile(store,rid,"fa","Persian","Arab","rtl")
    en=_profile(store,rid,"en","English","Latn","ltr")

    project=store.add_source_text(rid,OriginalLanguageSourceTextAddRequest(
        actor_ref="identity:test-owner",
        label="Original Persian passage",
        source_ref="library:source:fa-1",
        source_hash="sha256:source-fa",
        language_profile_id=fa,
        text_ref="library:text:fa-1",
        text_hash="sha256:text-fa",
        source_locator="page:12",
        extraction_lineage_refs=["library:extraction:1"],
    ))
    sid=project["source_texts"][0]["source_text_id"]
    assert project["source_texts"][0]["original_language"] is True

    project=store.add_derived_representation(rid,DerivedLanguageRepresentationAddRequest(
        actor_ref="identity:test-owner",
        label="Reviewed English translation",
        source_text_id=sid,
        representation_type="translation",
        target_language_profile_id=en,
        derived_text_ref="workspace:translation:fa-en-1",
        derived_text_hash="sha256:translation-1",
        method="hybrid",
        provider_ref="external:translation-provider",
        model_ref="external:model:translator",
        tool_version="1",
        reviewer_ref="identity:reviewer",
        review_status="reviewed",
        transformation_refs=["workspace:translation-job:1"],
    ))
    did=project["derived_representations"][0]["derived_representation_id"]
    derived=project["derived_representations"][0]
    assert derived["derived_from_original"] is True
    assert derived["source_text_remains_authoritative_representation"] is True
    assert derived["semantic_equivalence_not_inferred"] is True

    project=store.add_alignment(rid,TextAlignmentAddRequest(
        actor_ref="identity:test-owner",
        source_text_id=sid,
        derived_representation_id=did,
        granularity="sentence",
        alignment_ref="workspace:alignment:1",
        alignment_hash="sha256:alignment-1",
        method="hybrid",
        segment_count=4,
        reviewer_ref="identity:reviewer",
        review_status="reviewed",
    ))
    alignment=project["alignments"][0]
    assert alignment["semantic_equivalence_not_inferred"] is True
    assert alignment["alignment_is_provenance_not_truth"] is True

    lineage=store.lineage(rid)
    assert lineage["derived_representations"][0]["source_language_profile_id"]==fa
    assert lineage["derived_representations"][0]["target_language_profile"]["language_tag"]=="en"
    assert lineage["governance"]["original_language_precedes_derived_representations"] is True


def test_cross_language_query_plan_and_retrieval_receipt_are_reviewable(tmp_path):
    store=_store(tmp_path)
    rid=_project(store)["multilingual_research_id"]
    fa=_profile(store,rid,"fa","Persian","Arab","rtl")
    en=_profile(store,rid,"en","English","Latn","ltr")

    project=store.add_query_plan(rid,CrossLanguageQueryPlanAddRequest(
        actor_ref="identity:test-owner",
        label="Original-first infrastructure query",
        query_ref="session:query:fa-1",
        source_language_profile_id=fa,
        target_language_profile_ids=[fa,en],
        strategy="original-language-first",
        derived_query_refs=["workspace:derived-query:en-1"],
        representation_refs=["core:cross-lingual-representation:1"],
        retrieval_constraints={"domains":["infrastructure"]},
    ))
    qid=project["query_plans"][0]["query_plan_id"]
    assert project["query_plans"][0]["translation_execution_performed"] is False
    assert project["query_plans"][0]["retrieval_execution_performed"] is False
    assert project["query_plans"][0]["original_query_preserved"] is True

    project=store.add_retrieval_receipt(rid,CrossLanguageRetrievalReceiptAddRequest(
        actor_ref="identity:test-owner",
        query_plan_id=qid,
        execution_ref="librarian:retrieval-run:1",
        result_refs=["library:source:fa-1","library:source:en-2"],
        result_language_profile_ids=[fa,en],
        retrieval_profile="cross-language-hybrid",
        diagnostics={"candidate_count":12},
    ))
    receipt=project["retrieval_receipts"][0]
    assert receipt["receipt_is_observation_not_relevance_truth"] is True
    assert receipt["cross_language_results_require_review"] is True


def test_alignment_lineage_mismatch_fails_closed(tmp_path):
    store=_store(tmp_path)
    rid=_project(store)["multilingual_research_id"]
    fa=_profile(store,rid,"fa","Persian","Arab","rtl")
    en=_profile(store,rid,"en","English","Latn","ltr")

    project=store.add_source_text(rid,OriginalLanguageSourceTextAddRequest(
        actor_ref="identity:test-owner",
        label="Source one",
        source_ref="source:1",
        language_profile_id=fa,
        text_ref="text:1",
    ))
    sid1=project["source_texts"][-1]["source_text_id"]
    project=store.add_source_text(rid,OriginalLanguageSourceTextAddRequest(
        actor_ref="identity:test-owner",
        label="Source two",
        source_ref="source:2",
        language_profile_id=fa,
        text_ref="text:2",
    ))
    sid2=project["source_texts"][-1]["source_text_id"]
    project=store.add_derived_representation(rid,DerivedLanguageRepresentationAddRequest(
        actor_ref="identity:test-owner",
        label="Translation one",
        source_text_id=sid1,
        representation_type="translation",
        target_language_profile_id=en,
        derived_text_ref="derived:1",
    ))
    did=project["derived_representations"][-1]["derived_representation_id"]

    try:
        store.add_alignment(rid,TextAlignmentAddRequest(
            actor_ref="identity:test-owner",
            source_text_id=sid2,
            derived_representation_id=did,
            granularity="sentence",
            alignment_ref="alignment:bad",
        ))
        assert False,"mismatched lineage should fail"
    except ValueError as exc:
        assert "does not match" in str(exc)


def test_snapshot_and_core_candidate_preserve_authority_boundaries(tmp_path):
    store=_store(tmp_path)
    rid=_project(store)["multilingual_research_id"]
    fa=_profile(store,rid,"fa","Persian","Arab","rtl")
    store.add_source_text(rid,OriginalLanguageSourceTextAddRequest(
        actor_ref="identity:test-owner",
        label="Persian source",
        source_ref="source:fa",
        language_profile_id=fa,
        text_ref="text:fa",
    ))

    ready=store.readiness(rid)
    assert ready["ready_for_cross_language_research"] is True
    assert ready["governance"]["readiness_is_structural_not_translation_quality_judgment"] is True

    core=store.core_candidate(rid)
    assert core["platform_core_authority_required"] is True
    assert core["automatic_core_write"] is False
    assert core["automatic_entity_resolution"] is False
    assert core["automatic_citation_resolution"] is False
    assert core["automatic_evidence_resolution"] is False

    snap=store.freeze_snapshot(MultilingualResearchSnapshotRequest(
        actor_ref="identity:test-owner",
        multilingual_research_id=rid,
    ))
    assert len(snap["snapshot_hash"])==64
    assert snap["governance"]["snapshot_preserves_language_lineage_not_translation_quality_verdict"] is True


def test_routes_auth_health_and_current_boundary(tmp_path):
    from app.services import multilingual_cross_language_research as multilingual_service
    multilingual_service._store=MultilingualCrossLanguageResearchStore(
        sqlite_path=tmp_path/"api-multilingual.sqlite3"
    )

    from app.main import app
    client=TestClient(app)
    paths={getattr(r,"path","") for r in app.routes}

    assert "/v1/research-librarian/multilingual-research/manifest" in paths
    assert "/v1/research-librarian/multilingual-research/capabilities" in paths
    assert "/v1/research-librarian/multilingual-research/projects" in paths

    public=client.get("/v1/research-librarian/multilingual-research/manifest")
    assert public.status_code==200
    assert public.json()["data"]["milestone"]=="12.2.0"

    assert client.get("/v1/research-librarian/multilingual-research/capabilities").status_code==401
    cap=client.get(
        "/v1/research-librarian/multilingual-research/capabilities",
        headers={"X-SC-RL-Key":"test-key"},
    )
    assert cap.status_code==200

    created=client.post(
        "/v1/research-librarian/multilingual-research/projects",
        headers={"X-SC-RL-Key":"test-key"},
        json={
            "actor_ref":"identity:test-owner",
            "title":"API multilingual study",
            "objective":"Preserve original language and derived representation provenance.",
        },
    )
    assert created.status_code==200

    health=client.get("/health")
    assert health.status_code==200
    h=health.json()
    assert h["version"]=="12.3.0"
    assert h["multilingual_cross_language_research"] is True
    assert h["multilingual_research_runtime"]=="12.2.0"
    assert h["wordpress_required"] is False

    from app.services.independent_research_librarian_api import api_manifest,capabilities as independent_capabilities
    m=api_manifest()
    c=independent_capabilities()
    assert m["scope"]["multilingual_cross_language_research"] is True
    assert m["next_boundary"]=="cross-language-entity-toponym-resolution"
    assert c["milestone"]=="12.3.0"
    assert c["multilingual_cross_language_research"] is True
    assert c["global_source_federation"] is True


def test_v1210_neural_foundation_remains_historical_boundary():
    from app.services.neural_research_intelligence import neural_manifest
    m=neural_manifest()
    assert m["milestone"]=="12.1.0"
    assert m["wordpress_required"] is False
    assert m["execution"]["librarian_executes_training"] is False
    assert m["execution"]["librarian_executes_inference"] is False
