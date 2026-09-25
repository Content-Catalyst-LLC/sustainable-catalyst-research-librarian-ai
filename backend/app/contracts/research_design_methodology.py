from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

RESEARCH_DESIGN_METHODOLOGY_SCHEMA = "sc-research-librarian-research-design-methodology/1.0"
RESEARCH_DESIGN_METHODOLOGY_SNAPSHOT_SCHEMA = "sc-research-librarian-research-design-methodology-snapshot/1.0"

MethodFamily = Literal[
    "quantitative", "qualitative", "mixed-methods", "experimental", "quasi-experimental",
    "observational", "computational", "systematic-review", "case-study", "survey",
    "longitudinal", "cross-sectional", "methodological", "other",
]
ReviewState = Literal["draft", "under-review", "approved", "rejected"]
ThreatCategory = Literal[
    "internal-validity", "external-validity", "construct-validity", "statistical-conclusion-validity",
    "measurement", "selection", "confounding", "missing-data", "temporal", "reproducibility", "other",
]

class MethodologyCandidateSpec(BaseModel):
    label: str = Field(min_length=1, max_length=1000)
    method_family: MethodFamily
    design_type: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(default="", max_length=20000)
    question_alignment: list[str] = Field(default_factory=list, max_length=1000)
    hypothesis_refs: list[str] = Field(default_factory=list, max_length=1000)
    variable_names: list[str] = Field(default_factory=list, max_length=1000)
    sampling_strategy: str = Field(default="", max_length=10000)
    data_requirements: list[str] = Field(default_factory=list, max_length=1000)
    assumptions: list[str] = Field(default_factory=list, max_length=1000)
    validity_threats: list[str] = Field(default_factory=list, max_length=1000)
    analysis_candidates: list[str] = Field(default_factory=list, max_length=1000)
    execution_targets: list[str] = Field(default_factory=list, max_length=1000)
    limitations: list[str] = Field(default_factory=list, max_length=1000)

class ResearchDesignPlanCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    project_ref: str = Field(min_length=1, max_length=2000)
    question_plan_id: str = Field(default="", max_length=255)
    environment_id: str = Field(default="", max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    research_question: str = Field(default="", max_length=20000)
    objectives: list[str] = Field(default_factory=list, max_length=1000)
    constraints: list[str] = Field(default_factory=list, max_length=1000)
    candidate_designs: list[MethodologyCandidateSpec] = Field(default_factory=list, max_length=100)
    preferred_candidate_id: str = Field(default="", max_length=255)
    scaffold_candidates: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

class MethodologyCandidateAddRequest(MethodologyCandidateSpec):
    actor_ref: str = Field(min_length=1, max_length=255)

class ResearchDesignValidityThreatRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    threat: str = Field(min_length=1, max_length=10000)
    category: ThreatCategory = "other"
    mitigation: str = Field(default="", max_length=10000)
    candidate_id: str = Field(default="", max_length=255)

class ResearchDesignPreferenceRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    candidate_id: str = Field(min_length=1, max_length=255)
    rationale: str = Field(default="", max_length=10000)

class ResearchDesignReviewStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: ReviewState
    note: str = Field(default="", max_length=10000)

class ResearchDesignSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    plan_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="research-design-methodology-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
