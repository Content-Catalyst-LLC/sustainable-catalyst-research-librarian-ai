from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

RESEARCH_QUESTION_HYPOTHESIS_SCHEMA = "sc-research-librarian-research-question-hypothesis-intelligence/1.0"
RESEARCH_QUESTION_HYPOTHESIS_SNAPSHOT_SCHEMA = "sc-research-librarian-research-question-hypothesis-snapshot/1.0"

QuestionType = Literal[
    "unspecified", "descriptive", "exploratory", "comparative", "relational",
    "causal", "evaluative", "predictive", "methodological", "mixed",
]
VariableRole = Literal[
    "exposure", "intervention", "predictor", "outcome", "confounder", "mediator",
    "moderator", "covariate", "measure", "other",
]
HypothesisType = Literal[
    "null", "alternative", "directional", "non-directional", "associational",
    "causal", "mechanistic", "exploratory",
]
Direction = Literal["positive", "negative", "no-difference", "nonlinear", "unspecified"]
ReviewState = Literal["draft", "under-review", "approved", "rejected"]

class ResearchVariableSpec(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    role: VariableRole = "other"
    operational_definition: str = Field(default="", max_length=5000)
    unit: str = Field(default="", max_length=255)
    source_hint: str = Field(default="", max_length=2000)

class ResearchSubquestionSpec(BaseModel):
    question: str = Field(min_length=1, max_length=20000)
    purpose: str = Field(default="", max_length=5000)
    evidence_requirements: list[str] = Field(default_factory=list, max_length=500)
    core_question_ref: str = Field(default="", max_length=2000)

class ResearchHypothesisSpec(BaseModel):
    label: str = Field(default="", max_length=500)
    statement: str = Field(min_length=1, max_length=20000)
    hypothesis_type: HypothesisType = "exploratory"
    expected_direction: Direction = "unspecified"
    rationale: str = Field(default="", max_length=10000)
    falsification_criteria: list[str] = Field(default_factory=list, max_length=500)
    core_hypothesis_ref: str = Field(default="", max_length=2000)

class ResearchQuestionPlanCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    project_ref: str = Field(min_length=1, max_length=2000)
    environment_id: str = Field(default="", max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    broad_question: str = Field(min_length=1, max_length=20000)
    question_type: QuestionType = "unspecified"
    population: str = Field(default="", max_length=5000)
    context: str = Field(default="", max_length=5000)
    geography: str = Field(default="", max_length=2000)
    time_horizon: str = Field(default="", max_length=2000)
    constructs: list[str] = Field(default_factory=list, max_length=500)
    variables: list[ResearchVariableSpec] = Field(default_factory=list, max_length=200)
    subquestions: list[ResearchSubquestionSpec] = Field(default_factory=list, max_length=500)
    hypotheses: list[ResearchHypothesisSpec] = Field(default_factory=list, max_length=500)
    evidence_requirements: list[str] = Field(default_factory=list, max_length=1000)
    assumptions: list[str] = Field(default_factory=list, max_length=1000)
    falsification_criteria: list[str] = Field(default_factory=list, max_length=1000)
    core_object_refs: list[str] = Field(default_factory=list, max_length=5000)
    scaffold_candidates: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchSubquestionAddRequest(ResearchSubquestionSpec):
    actor_ref: str = Field(min_length=1, max_length=255)

class ResearchHypothesisAddRequest(ResearchHypothesisSpec):
    actor_ref: str = Field(min_length=1, max_length=255)

class ResearchEvidenceRequirementRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    requirement: str = Field(min_length=1, max_length=10000)
    rationale: str = Field(default="", max_length=10000)

class ResearchQuestionReviewStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: ReviewState
    note: str = Field(default="", max_length=10000)

class ResearchQuestionSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    plan_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="research-question-hypothesis-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
