from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

RESEARCH_PROGRAM_INTELLIGENCE_SCHEMA = "sc-research-librarian-research-program-intelligence/1.0"
RESEARCH_PROGRAM_SNAPSHOT_SCHEMA = "sc-research-librarian-research-program-intelligence-snapshot/1.0"
ProgramState = Literal["draft","in_review","approved","archived"]
WorkstreamState = Literal["planned","active","on-hold","completed","cancelled"]
MilestoneDecision = Literal["pending","approved","completed","blocked","waived"]
DeliverableState = Literal["planned","draft","in-review","accepted","withdrawn"]
ProgramComponentType = Literal[
    "research-question-plan","research-design-plan","evidence-search-strategy-plan","systematic-review-plan",
    "literature-intelligence-plan","argument-intelligence-plan","research-gap-novelty-plan","dataset-fitness-plan",
    "computational-research-plan","research-workflow","scholarly-study","scholarly-publication","knowledge-graph-node",
    "ai-research-context","rag-evaluation","ai-research-experiment","model-aware-research","cross-product-exchange",
    "core-object","other",
]
ConstraintCategory = Literal["resource","dependency","ethics","privacy","license","reproducibility","coordination","security","other"]

class ResearchProgramCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    program_ref: str = Field(min_length=1,max_length=2000)
    mission: str = Field(default="",max_length=20000)
    research_objectives: list[str] = Field(default_factory=list,max_length=5000)
    computational_plan_ids: list[str] = Field(default_factory=list,max_length=5000)
    core_project_id: str = Field(default="",max_length=255)
    metadata: dict[str,Any] = Field(default_factory=dict)

class ResearchProgramWorkstreamAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    objective: str = Field(min_length=1,max_length=10000)
    lead_ref: str = Field(default="",max_length=255)
    state: WorkstreamState = "planned"
    computational_plan_ids: list[str] = Field(default_factory=list,max_length=5000)
    dependencies: list[str] = Field(default_factory=list,max_length=5000)
    expected_outputs: list[str] = Field(default_factory=list,max_length=5000)
    metadata: dict[str,Any] = Field(default_factory=dict)

class ResearchProgramComponentBindingRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    component_type: ProgramComponentType
    component_ref: str = Field(min_length=1,max_length=2000)
    workstream_id: str = Field(default="",max_length=255)
    role: str = Field(default="",max_length=255)
    source_authority: str = Field(default="",max_length=255)
    note: str = Field(default="",max_length=10000)

class ResearchProgramMilestoneAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    objective: str = Field(default="",max_length=10000)
    target_date: str = Field(default="",max_length=64)
    workstream_ids: list[str] = Field(default_factory=list,max_length=5000)
    dependency_milestone_ids: list[str] = Field(default_factory=list,max_length=5000)
    required_binding_ids: list[str] = Field(default_factory=list,max_length=5000)
    acceptance_criteria: list[str] = Field(default_factory=list,max_length=5000)

class ResearchProgramMilestoneDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    milestone_id: str = Field(min_length=1,max_length=255)
    decision: MilestoneDecision = "pending"
    rationale: str = Field(default="",max_length=10000)

class ResearchProgramDeliverableAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    deliverable_type: str = Field(default="research-output",max_length=255)
    milestone_id: str = Field(default="",max_length=255)
    workstream_id: str = Field(default="",max_length=255)
    binding_ids: list[str] = Field(default_factory=list,max_length=5000)
    state: DeliverableState = "planned"
    artifact_ref: str = Field(default="",max_length=2000)
    note: str = Field(default="",max_length=10000)

class ResearchProgramConstraintAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    category: ConstraintCategory
    description: str = Field(min_length=1,max_length=10000)
    mitigation: str = Field(default="",max_length=10000)
    blocking: bool = False

class ResearchProgramStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: ProgramState
    note: str = Field(default="",max_length=10000)

class ResearchProgramSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    research_program_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="research-program-intelligence-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
