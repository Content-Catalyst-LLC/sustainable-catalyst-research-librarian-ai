from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

REPRODUCTION_REPLICATION_SCHEMA = "sc-research-librarian-reproduction-replication-intelligence/1.0"
REPRODUCTION_REPLICATION_SNAPSHOT_SCHEMA = "sc-research-librarian-reproduction-replication-intelligence-snapshot/1.0"
PlanState = Literal["draft","in_review","approved","archived"]
ReproductionKind = Literal["computational","analytical","data-processing","figure-table","environment","model-simulation","other"]
ReplicationKind = Literal["direct","conceptual","partial","extension","independent-data","cross-context","cross-population","other"]
Decision = Literal["pending","approved","rejected","waived"]
OutcomeAssessment = Literal["not-assessed","reproduced","partially-reproduced","not-reproduced","replication-supported","replication-not-supported","mixed","inconclusive"]

class ReproductionReplicationCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    source_study_ref: str = Field(min_length=1,max_length=2000)
    study_protocol_id: str = Field(min_length=1,max_length=255)
    statistical_analysis_plan_id: str = Field(default="",max_length=255)
    causal_design_id: str = Field(default="",max_length=255)
    simulation_study_id: str = Field(default="",max_length=255)
    purpose: str = Field(default="prospective reproduction and replication planning",max_length=5000)
    core_project_id: str = Field(default="",max_length=255)
    metadata: dict[str,Any] = Field(default_factory=dict)

class ReproductionAttemptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    kind: ReproductionKind
    target_refs: list[str] = Field(min_length=1,max_length=5000)
    data_refs: list[str] = Field(default_factory=list,max_length=5000)
    code_refs: list[str] = Field(default_factory=list,max_length=5000)
    environment_refs: list[str] = Field(default_factory=list,max_length=5000)
    runtime_target: str = Field(default="workspace",max_length=255)
    fidelity_basis: str = Field(min_length=1,max_length=10000)
    expected_outputs: list[str] = Field(default_factory=list,max_length=5000)
    permitted_deviations: list[str] = Field(default_factory=list,max_length=5000)

class ReplicationStudyAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    kind: ReplicationKind
    target_claim_refs: list[str] = Field(min_length=1,max_length=5000)
    research_question: str = Field(min_length=1,max_length=20000)
    population_or_context: str = Field(default="",max_length=10000)
    dataset_refs: list[str] = Field(default_factory=list,max_length=5000)
    method_refs: list[str] = Field(default_factory=list,max_length=5000)
    independence_note: str = Field(default="",max_length=10000)
    planned_differences: list[str] = Field(default_factory=list,max_length=5000)

class ComparabilityCriterionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    dimension: Literal["population","setting","exposure-treatment","outcome","measurement","design","analysis","data","implementation","time","model","other"]
    source_basis: str = Field(min_length=1,max_length=10000)
    replication_basis: str = Field(min_length=1,max_length=10000)
    acceptable_difference: str = Field(default="",max_length=10000)
    interpretation_boundary: str = Field(default="",max_length=10000)

class ReproductionEnvironmentManifestRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    runtime: str = Field(default="",max_length=255)
    runtime_version: str = Field(default="",max_length=255)
    package_lock_refs: list[str] = Field(default_factory=list,max_length=5000)
    container_or_environment_refs: list[str] = Field(default_factory=list,max_length=5000)
    operating_system: str = Field(default="",max_length=1000)
    hardware_notes: str = Field(default="",max_length=5000)
    seed_policy: str = Field(default="preserve-or-record-seeds",max_length=1000)
    data_access_notes: str = Field(default="",max_length=10000)

class ReproductionReplicationDeviationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    target_type: Literal["reproduction-attempt","replication-study"]
    target_id: str = Field(min_length=1,max_length=255)
    category: Literal["data","code","environment","method","population","measurement","timing","runtime","other"]
    description: str = Field(min_length=1,max_length=10000)
    rationale: str = Field(default="",max_length=10000)
    materiality_note: str = Field(default="",max_length=10000)

class ReproductionReplicationReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    target_type: Literal["reproduction-attempt","replication-study"]
    target_id: str = Field(min_length=1,max_length=255)
    execution_ref: str = Field(min_length=1,max_length=2000)
    status: Literal["completed","partial","failed-to-run","cancelled"]
    observed_summary: str = Field(default="",max_length=20000)
    artifact_refs: list[str] = Field(default_factory=list,max_length=5000)
    metrics: dict[str,Any] = Field(default_factory=dict)
    provenance_note: str = Field(default="",max_length=10000)

class ReproductionReplicationAssessmentRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    target_type: Literal["reproduction-attempt","replication-study"]
    target_id: str = Field(min_length=1,max_length=255)
    assessment: OutcomeAssessment
    rationale: str = Field(min_length=1,max_length=20000)
    evidentiary_scope: str = Field(default="human scholarly assessment of the registered attempt/study only",max_length=10000)
    limitations: list[str] = Field(default_factory=list,max_length=5000)

class ReproductionReplicationDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    object_type: Literal["reproduction-attempt","replication-study","comparability-criterion"]
    object_id: str = Field(min_length=1,max_length=255)
    decision: Decision
    rationale: str = Field(default="",max_length=10000)

class ReproductionReplicationStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: PlanState
    note: str = Field(default="",max_length=10000)

class ReproductionReplicationSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    reproduction_replication_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="reproduction-replication-intelligence-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
