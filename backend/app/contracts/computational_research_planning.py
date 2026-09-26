from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA = "sc-research-librarian-computational-research-planning/1.0"
COMPUTATIONAL_RESEARCH_PLANNING_SNAPSHOT_SCHEMA = "sc-research-librarian-computational-research-planning-snapshot/1.0"
PlanState = Literal["draft","in_review","approved","archived"]
StepDecision = Literal["pending","approved-for-execution","revise","rejected"]
RuntimeKind = Literal["workspace","research-lab","workbench","python","r","julia","fortran","rust","c-cpp","haskell","sql","other"]
ConstraintCategory = Literal["assumption","resource","privacy","license","reproducibility","validation","numerical","security","other"]

class ComputationalResearchPlanCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    project_ref: str = Field(min_length=1,max_length=2000)
    research_question: str = Field(default="",max_length=20000)
    data_fitness_id: str = Field(default="",max_length=255)
    dataset_ids: list[str] = Field(default_factory=list,max_length=5000)
    core_project_id: str = Field(default="",max_length=255)
    metadata: dict[str,Any] = Field(default_factory=dict)

class ComputationalRuntimeTargetAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    runtime_kind: RuntimeKind
    name: str = Field(min_length=1,max_length=1000)
    version_constraint: str = Field(default="",max_length=255)
    environment_ref: str = Field(default="",max_length=2000)
    capabilities: list[str] = Field(default_factory=list,max_length=5000)
    restrictions: list[str] = Field(default_factory=list,max_length=5000)
    metadata: dict[str,Any] = Field(default_factory=dict)

class ComputationalAnalysisStepAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    objective: str = Field(min_length=1,max_length=10000)
    method_family: str = Field(default="",max_length=1000)
    runtime_target_id: str = Field(min_length=1,max_length=255)
    dataset_ids: list[str] = Field(default_factory=list,max_length=5000)
    variable_ids: list[str] = Field(default_factory=list,max_length=5000)
    dependency_step_ids: list[str] = Field(default_factory=list,max_length=5000)
    parameter_spec: dict[str,Any] = Field(default_factory=dict)
    preprocessing: list[str] = Field(default_factory=list,max_length=5000)
    analysis_spec: dict[str,Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list,max_length=5000)
    validation_checks: list[str] = Field(default_factory=list,max_length=5000)
    reproducibility_notes: str = Field(default="",max_length=10000)
    limitations: list[str] = Field(default_factory=list,max_length=5000)

class ComputationalStepDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    step_id: str = Field(min_length=1,max_length=255)
    decision: StepDecision = "pending"
    rationale: str = Field(default="",max_length=10000)

class ReproducibilityRequirementAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    description: str = Field(min_length=1,max_length=10000)
    artifact_type: str = Field(default="",max_length=255)
    required: bool = True
    verification_note: str = Field(default="",max_length=10000)

class ComputationalConstraintAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    category: ConstraintCategory
    description: str = Field(min_length=1,max_length=10000)
    mitigation: str = Field(default="",max_length=10000)
    blocking: bool = False

class ComputationalResearchPlanStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: PlanState
    note: str = Field(default="",max_length=10000)

class ComputationalResearchPlanSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    computational_plan_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="computational-research-planning-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
