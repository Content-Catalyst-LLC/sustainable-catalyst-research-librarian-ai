import os
os.environ.setdefault("SC_RL_BACKEND_API_KEY", "test-key")
import asyncio
from fastapi.testclient import TestClient

from app.contracts.research_integrity_methodological_audit import *
from app.services.research_integrity_methodological_audit import ResearchIntegrityMethodologicalAuditStore, capabilities
from app.async_jobs import JOB_TYPES, JobClaim
from app.services.document_jobs import execute_job


def fake_resolvers():
    def resolver(ref):
        if ref == "missing":
            raise ValueError("missing")
        return {"record_hash": f"hash-{ref}"}
    return {
        "study-protocol": resolver,
        "statistical-analysis-plan-intelligence": resolver,
        "cross-study-synthesis-plan": resolver,
    }


def make_store(tmp_path):
    return ResearchIntegrityMethodologicalAuditStore(tmp_path / "integrity.sqlite3", target_resolvers=fake_resolvers())


def make_audit(store):
    return store.create(ResearchIntegrityAuditCreateRequest(
        actor_ref="lead-reviewer",
        title="Methodological integrity audit",
        audit_question="Do the reported methods remain traceable to declared plans and evidence?",
        project_ref="project-1",
        targets=[
            ResearchIntegrityTargetBinding(target_type="study-protocol", target_ref="protocol-1"),
            ResearchIntegrityTargetBinding(target_type="statistical-analysis-plan-intelligence", target_ref="stats-1"),
            ResearchIntegrityTargetBinding(target_type="cross-study-synthesis-plan", target_ref="synth-1"),
        ],
        audit_standard_refs=["protocol", "analysis-plan", "reporting-guideline"],
    ))


def test_create_preserves_lineage_and_guardrails(tmp_path):
    s=make_store(tmp_path); rec=make_audit(s)
    assert rec["schema"] == RESEARCH_INTEGRITY_AUDIT_SCHEMA
    assert len(rec["targets"]) == 3 and all(x["resolved_hash"] for x in rec["targets"])
    assert rec["governance"]["audit_findings_are_human_authored"] is True
    assert rec["governance"]["automatic_misconduct_inference"] is False
    assert rec["governance"]["automatic_invalidity_verdict"] is False
    assert rec["governance"]["automatic_truth_promotion"] is False


def test_known_missing_target_fails_closed(tmp_path):
    s=make_store(tmp_path)
    try:
        s.create(ResearchIntegrityAuditCreateRequest(actor_ref="x", title="Bad audit", audit_question="q", targets=[ResearchIntegrityTargetBinding(target_type="study-protocol", target_ref="missing")]))
    except ValueError as exc:
        assert "audit target" in str(exc)
    else:
        raise AssertionError("known target should fail closed when resolver cannot retrieve it")


def test_criteria_observations_and_findings_are_human_authored(tmp_path):
    s=make_store(tmp_path); aid=make_audit(s)["audit_id"]
    rec=s.add_criterion(aid, ResearchIntegrityCriterionAddRequest(actor_ref="reviewer", domain="analysis-plan-consistency", label="Primary model", audit_question="Was the declared primary model used?", expectation_basis="Frozen statistical analysis plan"))
    cid=rec["criteria"][0]["criterion_id"]
    rec=s.add_observation(aid, ResearchIntegrityObservationAddRequest(actor_ref="reviewer", criterion_id=cid, target_ref="stats-1", status="inconsistent", expected_or_declared="Model A", observed_or_reported="Model B", description="Reported primary analysis differs from the declared model.", evidence_refs=["analysis-plan", "manuscript-methods"]))
    rec=s.add_finding(aid, ResearchIntegrityFindingAddRequest(actor_ref="reviewer", criterion_id=cid, finding_kind="declared-deviation", significance="review-needed", finding="Primary analysis differs from the declared plan.", rationale="The divergence should be explained and traced.", evidence_refs=["analysis-plan", "manuscript-methods"]))
    assert rec["observations"][0]["status_is_review_signal_not_verdict"] is True
    assert rec["findings"][0]["human_authored"] is True
    assert rec["findings"][0]["misconduct_not_inferred"] is True
    assert rec["findings"][0]["invalidity_not_inferred"] is True


def test_methodological_profile_has_no_score_or_ranking(tmp_path):
    s=make_store(tmp_path); aid=make_audit(s)["audit_id"]
    s.add_appraisal(aid, ResearchIntegrityMethodologicalAppraisalAddRequest(actor_ref="reviewer", domain="missing-data", judgment="some-concerns", rationale="Missing-data handling is incompletely documented."))
    profile=s.methodological_profile(aid)
    assert profile["domains"]["missing-data"][0]["human_authored"] is True
    assert profile["governance"]["no_composite_quality_score"] is True
    assert profile["governance"]["no_methodological_ranking"] is True


def test_verification_requires_human_approval_and_receipt_is_not_verdict(tmp_path):
    s=make_store(tmp_path); aid=make_audit(s)["audit_id"]
    rec=s.add_verification_request(aid, ResearchIntegrityVerificationRequestAddRequest(actor_ref="reviewer", label="Re-run primary analysis", requested_check="Reproduce the primary model from the declared analysis plan.", target_refs=["stats-1"], runtime_target="workspace", expected_artifacts=["model-output", "environment-manifest"]))
    vid=rec["verification_requests"][0]["verification_request_id"]
    assert s.verification_handoffs(aid)["packets"] == []
    s.decide(aid, ResearchIntegrityDecisionRequest(actor_ref="lead-reviewer", object_type="verification-request", object_id=vid, decision="approved", rationale="Verification is needed."))
    packets=s.verification_handoffs(aid)["packets"]
    assert len(packets)==1 and packets[0]["execution_performed"] is False and packets[0]["misconduct_inferred"] is False
    rec=s.add_verification_receipt(aid, ResearchIntegrityVerificationReceiptAddRequest(actor_ref="runner", verification_request_id=vid, execution_ref="workspace-run-1170", status="completed", observed_summary="Re-run completed with documented output.", metrics={"rows":100}, artifact_refs=["artifact-1"]))
    assert rec["verification_receipts"][0]["receipt_is_observation_not_integrity_verdict"] is True
    assert rec["verification_receipts"][0]["automatic_finding_creation"] is False


def test_remediation_and_finding_disposition_are_separate_human_actions(tmp_path):
    s=make_store(tmp_path); aid=make_audit(s)["audit_id"]
    rec=s.add_criterion(aid, ResearchIntegrityCriterionAddRequest(actor_ref="reviewer", domain="reporting-completeness", label="Deviation reporting", audit_question="Are deviations explained?", expectation_basis="Protocol and report"))
    cid=rec["criteria"][0]["criterion_id"]
    rec=s.add_finding(aid, ResearchIntegrityFindingAddRequest(actor_ref="reviewer", criterion_id=cid, finding_kind="reporting-gap", significance="review-needed", finding="Deviation rationale is absent.", rationale="The report identifies a changed analysis but not why."))
    fid=rec["findings"][0]["finding_id"]
    rec=s.add_remediation_action(aid, ResearchIntegrityRemediationActionAddRequest(actor_ref="reviewer", finding_ids=[fid], action="Add a dated explanation of the analysis deviation.", owner_ref="study-team"))
    rid=rec["remediation_actions"][0]["remediation_action_id"]
    rec=s.set_remediation_status(aid, ResearchIntegrityRemediationStatusRequest(actor_ref="study-team", remediation_action_id=rid, status="completed", note="Explanation added."))
    assert rec["findings"][0]["disposition"] == "open"
    rec=s.set_finding_disposition(aid, ResearchIntegrityFindingDispositionRequest(actor_ref="lead-reviewer", finding_id=fid, disposition="resolved", rationale="The added explanation closes the reporting gap."))
    assert rec["findings"][0]["disposition"] == "resolved"


def test_traceability_discrepancy_readiness_core_and_snapshot(tmp_path):
    s=make_store(tmp_path); aid=make_audit(s)["audit_id"]
    rec=s.add_criterion(aid, ResearchIntegrityCriterionAddRequest(actor_ref="reviewer", domain="preregistration-consistency", label="Primary outcome", audit_question="Does the reported primary outcome match the preregistered outcome?", expectation_basis="Frozen protocol"))
    cid=rec["criteria"][0]["criterion_id"]
    s.add_observation(aid, ResearchIntegrityObservationAddRequest(actor_ref="reviewer", criterion_id=cid, status="consistent", description="Primary outcome matches the frozen protocol."))
    assert s.readiness(aid)["ready_for_human_review"] is True
    assert len(s.traceability_matrix(aid)["rows"]) == 1
    assert s.discrepancy_register(aid)["open_findings"] == []
    cand=s.core_candidate(aid); snap=s.freeze_snapshot(ResearchIntegrityAuditSnapshotRequest(actor_ref="lead-reviewer", audit_id=aid))
    assert cand["misconduct_not_inferred"] is True and cand["scientific_validity_not_certified"] is True and cand["truth_promoted"] is False
    assert snap["schema"] == RESEARCH_INTEGRITY_AUDIT_SNAPSHOT_SCHEMA and len(snap["snapshot_hash"]) == 64


def test_durable_job_and_authenticated_api_surface(tmp_path, monkeypatch):
    s=make_store(tmp_path); aid=make_audit(s)["audit_id"]
    assert "research-integrity-methodological-audit-snapshot" in JOB_TYPES
    import app.services.document_jobs as dj
    monkeypatch.setattr(dj, "get_research_integrity_methodological_audit_store", lambda:s)
    events=[]
    claim=JobClaim(job_id="job-1170", job_type="research-integrity-methodological-audit-snapshot", payload={"snapshot":{"actor_ref":"lead-reviewer","audit_id":aid}}, attempts=1, max_attempts=3, worker_id="w")
    out=asyncio.run(execute_job(claim, lambda stage,percent:events.append((stage,percent))))
    assert out["schema"] == RESEARCH_INTEGRITY_AUDIT_SNAPSHOT_SCHEMA and events[-1] == ("research-integrity-methodological-audit-snapshot-ready",95)
    from app.main import app
    paths={getattr(r,"path","") for r in app.routes}
    required={
        "/v1/core/research-integrity-methodological-audit/capabilities",
        "/v1/core/research-integrity-methodological-audit/audits",
        "/v1/core/research-integrity-methodological-audit/audits/{audit_id}/traceability-matrix",
        "/v1/core/research-integrity-methodological-audit/audits/{audit_id}/verification-handoffs",
        "/v1/core/research-integrity-methodological-audit/snapshots/freeze",
    }
    assert not(required-paths), required-paths
    client=TestClient(app)
    assert client.get("/v1/core/research-integrity-methodological-audit/capabilities").status_code in {401,503}
    ok=client.get("/v1/core/research-integrity-methodological-audit/capabilities",headers={"X-SC-RL-Key":"test-key"})
    assert ok.status_code==200 and ok.json()["automatic_misconduct_inference"] is False


def test_unified_environment_accepts_integrity_audit_binding(tmp_path):
    from app.contracts.unified_scholarly_ai_environment import UnifiedResearchEnvironmentCreateRequest
    from app.services.unified_scholarly_ai_environment import UnifiedScholarlyAIEnvironmentStore
    s=make_store(tmp_path); aid=make_audit(s)["audit_id"]
    env=UnifiedScholarlyAIEnvironmentStore(tmp_path/"env.sqlite3", research_integrity_audit_store=s)
    rec=env.create(UnifiedResearchEnvironmentCreateRequest(actor_ref="lead",title="Unified",project_ref="p",research_integrity_audit_ids=[aid]))
    line=env.lineage(rec["environment_id"]); ready=env.readiness(rec["environment_id"])
    assert len(line["research_design"]["research_integrity_audits"])==1
    assert ready["dimensions"]["research_integrity_audit_bound"] is True


def test_capabilities_guardrails_are_explicit():
    cap=capabilities()
    assert cap["milestone"]=="11.7" and cap["human_integrity_findings"] is True and cap["remediation_tracking"] is True
    assert cap["audit_findings_are_human_authored"] is True and cap["specialist_runtimes_own_verification_execution"] is True
    assert cap["automatic_misconduct_inference"] is False and cap["automatic_invalidity_verdict"] is False
    assert cap["automatic_retraction_recommendation"] is False and cap["automatic_methodological_scoring"] is False
    assert cap["automatic_publication_block"] is False and cap["automatic_execution"] is False and cap["automatic_truth_promotion"] is False
