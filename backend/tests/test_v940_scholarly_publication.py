from __future__ import annotations
import asyncio, os
os.environ.setdefault("SC_RL_BACKEND_API_KEY","test-key")
from fastapi.testclient import TestClient
from app.async_jobs import JobClaim, JOB_TYPES
from app.contracts.scholarly_research import ScholarlyStudyCreateRequest, ScholarlyProtocol, ScholarlyProtocolFreezeRequest, ScholarlyResultRequest, ScholarlyInterpretationRequest, ScholarlyManuscriptSectionRequest
from app.contracts.scholarly_publication import (
    ScholarlyPublicationCreateRequest, PublicationContributor, PublicationReference,
    PublicationVersionRequest, PublicationIdentifierRequest, PublicationStateTransitionRequest,
    PublicationHandoffRequest, PublicationPackageFreezeRequest,
)
from app.services.scholarly_research import ScholarlyResearchStore
from app.services.scholarly_publication import ScholarlyPublicationStore
from app.services.document_jobs import execute_job


def ready_study(tmp_path, monkeypatch):
    scholarly=ScholarlyResearchStore(tmp_path/"scholarly.sqlite3")
    study,_=scholarly.create(ScholarlyStudyCreateRequest(
        core_project_id="core-940",title="Publication-ready study",research_question="What does the registered analysis show?",study_type="observational",
        protocol=ScholarlyProtocol(methods="Registered method.",analysis_plan="Registered analysis.",data_management_plan="Archive hashes.",ethics_review_status="not-applicable"),
        authors=["Author A"],affiliations=["Independent Lab"],funding_statement="No external funding.",conflict_of_interest_statement="No conflicts declared.",source_refs=["source:940"],core_evidence_refs=["evidence:940"],visual_refs=["visual:study-940"],idempotency_key="study-940"))
    scholarly.freeze_protocol(study["study_id"],ScholarlyProtocolFreezeRequest(reviewer_ref="protocol-reviewer"))
    study=scholarly.add_result(study["study_id"],ScholarlyResultRequest(actor_ref="author",result_type="statistical",title="Primary result",summary="Archived estimate.",runtime_ref="analytics-r:940",artifact_ref="artifact:result-940",evidence_refs=["evidence:940"],visual_refs=["visual:result-940"]))
    rid=study["results"][0]["result_id"]
    scholarly.add_interpretation(study["study_id"],ScholarlyInterpretationRequest(author_ref="author",text="Human interpretation with qualification.",result_refs=[rid],evidence_refs=["evidence:940"],uncertainty_or_qualification="Uncertainty retained."))
    for sec in ["methods","results","discussion","limitations"]:
        scholarly.add_manuscript_section(study["study_id"],ScholarlyManuscriptSectionRequest(author_ref="author",section=sec,heading=sec.title(),text=f"Human-authored {sec} section.",citation_refs=["source:940"]))
    import app.services.scholarly_publication as sp
    monkeypatch.setattr(sp,"get_scholarly_research_store",lambda:scholarly)
    return scholarly,scholarly.get(study["study_id"])


def publication_request(key="pub-940"):
    return ScholarlyPublicationCreateRequest(actor_ref="author",publication_type="article",title="Research publication",abstract="A human-authored abstract describing the study.",keywords=["research","evidence"],contributors=[PublicationContributor(contributor_ref="author-1",display_name="Author A",role="author",affiliation="Independent Lab")],manuscript_artifact_ref="artifact:manuscript-v1",references=[PublicationReference(title="Reference work",authors=["Scholar B"],year=2025,doi="10.1000/example",source_ref="source:940")],source_refs=["source:940"],core_evidence_refs=["evidence:940"],visual_refs=["visual:result-940"],idempotency_key=key)


def test_publication_creation_is_idempotent_and_versioned(tmp_path,monkeypatch):
    _,study=ready_study(tmp_path,monkeypatch); store=ScholarlyPublicationStore(tmp_path/"publication.sqlite3")
    p1,r1=store.create(study["study_id"],publication_request()); p2,r2=store.create(study["study_id"],publication_request())
    assert r1 is False and r2 is True and p1["publication_id"]==p2["publication_id"]
    assert p1["version"]==1 and len(p1["versions"])==1 and len(p1["record_fingerprint"])==64


def test_declared_identifier_is_recorded_but_never_minted(tmp_path,monkeypatch):
    _,study=ready_study(tmp_path,monkeypatch); store=ScholarlyPublicationStore(tmp_path/"publication.sqlite3"); pub,_=store.create(study["study_id"],publication_request())
    pub=store.add_identifier(pub["publication_id"],PublicationIdentifierRequest(actor_ref="publisher",identifier_type="doi",value="10.1234/sc.940",registrar_or_authority="Declared registrar",resolver_url="https://doi.org/10.1234/sc.940"))
    assert pub["identifiers"][0]["assigned_by_librarian"] is False
    cap=__import__("app.services.scholarly_publication",fromlist=["capabilities"]).capabilities(); assert cap["doi_minting"] is False and cap["automatic_publication"] is False


def test_state_transition_requires_human_decision_and_url(tmp_path,monkeypatch):
    _,study=ready_study(tmp_path,monkeypatch); store=ScholarlyPublicationStore(tmp_path/"publication.sqlite3"); pub,_=store.create(study["study_id"],publication_request())
    pub=store.transition(pub["publication_id"],PublicationStateTransitionRequest(actor_ref="author",state="submitted",rationale="Submitted to venue.",venue="Journal"))
    try:
        store.transition(pub["publication_id"],PublicationStateTransitionRequest(actor_ref="editor",state="accepted",rationale="Accepted.")); assert False
    except ValueError: pass
    # publish cannot skip accepted and requires canonical URL
    pub=store.transition(pub["publication_id"],PublicationStateTransitionRequest(actor_ref="editor",state="accepted",rationale="Accepted after review.",decision_ref="editorial-decision:940"))
    try:
        store.transition(pub["publication_id"],PublicationStateTransitionRequest(actor_ref="publisher",state="published",rationale="Released.",decision_ref="editorial-decision:940")); assert False
    except ValueError: pass


def test_citation_export_and_knowledge_library_handoff_preserve_visual_lineage(tmp_path,monkeypatch):
    _,study=ready_study(tmp_path,monkeypatch); store=ScholarlyPublicationStore(tmp_path/"publication.sqlite3"); pub,_=store.create(study["study_id"],publication_request())
    exports=store.citation_exports(pub["publication_id"]); assert exports["schema"]=="sc-research-librarian-citation-export/1.0" and "Research publication" in exports["bibtex"]
    handoff=store.knowledge_library_handoff(pub["publication_id"],PublicationHandoffRequest(actor_ref="librarian"))
    assert handoff["status"]=="ready-for-explicit-library-import" and handoff["visual_refs"]==["visual:result-940"] and handoff["governance"]["handoff_does_not_publish_automatically"] is True


def test_versions_readiness_and_frozen_package(tmp_path,monkeypatch):
    _,study=ready_study(tmp_path,monkeypatch); store=ScholarlyPublicationStore(tmp_path/"publication.sqlite3"); pub,_=store.create(study["study_id"],publication_request())
    pub=store.add_version(pub["publication_id"],PublicationVersionRequest(actor_ref="author",change_summary="Clarified discussion.",version_label="v2",manuscript_artifact_ref="artifact:manuscript-v2",visual_refs=["visual:result-940","visual:citation-map-940"]))
    assert pub["version"]==2 and len(pub["versions"][-1]["content_hash"])==64
    ready=store.readiness(pub["publication_id"]); assert ready["ready"] is True
    pkg=store.freeze_package(pub["publication_id"],PublicationPackageFreezeRequest(actor_ref="author"))
    assert pkg["schema"]=="sc-research-librarian-scholarly-publication-package/1.0" and len(pkg["package_hash"])==64 and pkg["governance"]["package_is_not_doi_registration"] is True


def test_async_publication_package_job(tmp_path,monkeypatch):
    _,study=ready_study(tmp_path,monkeypatch); store=ScholarlyPublicationStore(tmp_path/"publication.sqlite3"); pub,_=store.create(study["study_id"],publication_request())
    import app.services.document_jobs as dj; monkeypatch.setattr(dj,"get_scholarly_publication_store",lambda:store)
    claim=JobClaim(job_id="job-940",job_type="scholarly-publication-package",payload={"publication_id":pub["publication_id"],"freeze":{"actor_ref":"author"}},attempts=1,max_attempts=3,worker_id="worker")
    events=[]; out=asyncio.run(execute_job(claim,lambda stage,pct:events.append((stage,pct))))
    assert out["publication_id"]==pub["publication_id"] and events[-1]==("scholarly-publication-package-ready",95) and "scholarly-publication-package" in JOB_TYPES


def test_authenticated_v940_api_surface():
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/scholarly-publication/capabilities",
        "/v1/core/scholarly-publication/studies/{study_id}/publications",
        "/v1/core/scholarly-publication/publications/{publication_id}/versions",
        "/v1/core/scholarly-publication/publications/{publication_id}/identifiers",
        "/v1/core/scholarly-publication/publications/{publication_id}/citation-exports",
        "/v1/core/scholarly-publication/publications/{publication_id}/knowledge-library-handoffs",
        "/v1/core/scholarly-publication/publications/{publication_id}/packages/freeze",
    }
    assert not(required-paths),required-paths
    client=TestClient(app); resp=client.get("/v1/core/scholarly-publication/capabilities",headers={"X-SC-RL-Key":"test-key"}); assert resp.status_code==200
