from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

STUDY_PROTOCOL_PREREGISTRATION_SCHEMA = "sc-research-librarian-study-protocol-preregistration/1.0"
STUDY_PROTOCOL_SNAPSHOT_SCHEMA = "sc-research-librarian-study-protocol-preregistration-snapshot/1.0"
ProtocolState = Literal["draft","in_review","preregistered","amended","closed"]
HypothesisRole = Literal["confirmatory","exploratory","secondary","other"]
OutcomeRole = Literal["primary","secondary","exploratory","safety","other"]
VariableRole = Literal["exposure","outcome","covariate","confounder","moderator","mediator","instrument","identifier","other"]
CommitmentDecision = Literal["pending","approved","rejected","waived"]
AmendmentImpact = Literal["none","minor","material","analysis-changing","scope-changing","other"]
DeviationCategory = Literal["sampling","measurement","exclusion","analysis","data","timing","protocol","other"]

class StudyProtocolCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    protocol_ref: str = Field(min_length=1,max_length=2000)
    research_program_id: str = Field(min_length=1,max_length=255)
    workstream_id: str = Field(default="",max_length=255)
    research_question: str = Field(default="",max_length=20000)
    study_type: str = Field(default="observational",max_length=255)
    registration_target: str = Field(default="",max_length=2000)
    planned_start_date: str = Field(default="",max_length=64)
    core_project_id: str = Field(default="",max_length=255)
    metadata: dict[str,Any] = Field(default_factory=dict)

class ProtocolHypothesisAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    statement: str = Field(min_length=1,max_length=20000)
    role: HypothesisRole = "confirmatory"
    directional: bool = False
    rationale: str = Field(default="",max_length=10000)
    source_refs: list[str] = Field(default_factory=list,max_length=5000)

class ProtocolOutcomeAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    role: OutcomeRole = "primary"
    measure: str = Field(min_length=1,max_length=10000)
    timepoint: str = Field(default="",max_length=1000)
    aggregation: str = Field(default="",max_length=1000)
    source_refs: list[str] = Field(default_factory=list,max_length=5000)

class ProtocolVariableAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    name: str = Field(min_length=1,max_length=1000)
    role: VariableRole
    operational_definition: str = Field(min_length=1,max_length=10000)
    unit: str = Field(default="",max_length=255)
    dataset_ref: str = Field(default="",max_length=2000)
    source_refs: list[str] = Field(default_factory=list,max_length=5000)

class ProtocolSamplingPlanRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    population: str = Field(min_length=1,max_length=10000)
    sampling_frame: str = Field(default="",max_length=10000)
    recruitment: str = Field(default="",max_length=10000)
    inclusion_criteria: list[str] = Field(default_factory=list,max_length=5000)
    exclusion_criteria: list[str] = Field(default_factory=list,max_length=5000)
    target_sample_size: int | None = Field(default=None,ge=1)
    stopping_rule: str = Field(default="",max_length=10000)
    power_analysis_ref: str = Field(default="",max_length=2000)

class ProtocolAnalysisCommitmentAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    method: str = Field(min_length=1,max_length=5000)
    hypothesis_ids: list[str] = Field(default_factory=list,max_length=5000)
    outcome_ids: list[str] = Field(default_factory=list,max_length=5000)
    variable_ids: list[str] = Field(default_factory=list,max_length=5000)
    computational_plan_id: str = Field(default="",max_length=255)
    alpha_or_threshold: str = Field(default="",max_length=255)
    multiplicity_strategy: str = Field(default="",max_length=5000)
    missing_data_strategy: str = Field(default="",max_length=5000)
    outlier_strategy: str = Field(default="",max_length=5000)
    transformation_strategy: str = Field(default="",max_length=5000)
    robustness_checks: list[str] = Field(default_factory=list,max_length=5000)

class ProtocolCommitmentDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    commitment_id: str = Field(min_length=1,max_length=255)
    decision: CommitmentDecision
    rationale: str = Field(default="",max_length=10000)

class ProtocolPreregisterRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    registration_target: str = Field(default="",max_length=2000)
    registration_identifier: str = Field(default="",max_length=2000)
    registration_url: str = Field(default="",max_length=2000)
    note: str = Field(default="",max_length=10000)

class ProtocolAmendmentAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    description: str = Field(min_length=1,max_length=20000)
    rationale: str = Field(min_length=1,max_length=20000)
    impact: AmendmentImpact = "other"
    affected_sections: list[str] = Field(default_factory=list,max_length=5000)
    prospective: bool = True

class ProtocolDeviationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    category: DeviationCategory
    description: str = Field(min_length=1,max_length=20000)
    rationale: str = Field(default="",max_length=20000)
    affected_commitment_ids: list[str] = Field(default_factory=list,max_length=5000)
    consequence_note: str = Field(default="",max_length=20000)

class StudyProtocolStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: ProtocolState
    note: str = Field(default="",max_length=10000)

class StudyProtocolSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    study_protocol_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="study-protocol-preregistration-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
