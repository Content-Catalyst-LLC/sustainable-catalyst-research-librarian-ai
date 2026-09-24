from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

STATISTICAL_RESEARCH_SCHEMA = "sc-research-librarian-statistical-analytical-integration/1.0"
CORE_STATISTICAL_CONTRACT = "sc.core.statistical-reasoning-object-model.v1"
ANALYTICS_R_SOURCE_CONTRACT = "sc.analytics-r.statistical-diagnostics-validation.v1"

RuntimeTarget = Literal["catalyst-analytics-r","workspace","research-lab","workbench","external-validated-runtime"]
ReviewDecision = Literal["pending","approved","rejected"]

class AnalyticalDatasetBinding(BaseModel):
    local_ref: str = Field(min_length=1,max_length=255)
    core_object_id: str | None = Field(default=None,max_length=255)
    evidence_refs: list[str] = Field(default_factory=list,max_length=200)
    variables: list[str] = Field(default_factory=list,max_length=500)
    role: Literal["primary","comparison","validation","covariate-source","reference"] = "primary"
    metadata: dict[str,Any] = Field(default_factory=dict)

class DeclaredAnalyticalAssumption(BaseModel):
    assumption_ref: str = Field(min_length=1,max_length=255)
    statement: str = Field(min_length=1,max_length=10000)
    status: Literal["declared","supported","challenged","failed","not_assessed"] = "declared"
    evidence_refs: list[str] = Field(default_factory=list,max_length=200)
    limitations: list[str] = Field(default_factory=list,max_length=100)

class StatisticalAnalysisPlanRequest(BaseModel):
    core_project_id: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=500)
    research_question: str = Field(min_length=1,max_length=10000)
    runtime_target: RuntimeTarget = "catalyst-analytics-r"
    analysis_type: str = Field(min_length=1,max_length=255)
    datasets: list[AnalyticalDatasetBinding] = Field(min_length=1,max_length=100)
    methods: list[str] = Field(default_factory=list,max_length=100)
    assumptions: list[DeclaredAnalyticalAssumption] = Field(default_factory=list,max_length=200)
    requested_outputs: list[str] = Field(default_factory=lambda:["diagnostics","coefficients","intervals"],max_length=100)
    evidence_refs: list[str] = Field(default_factory=list,max_length=500)
    limitations: list[str] = Field(default_factory=list,max_length=100)
    metadata: dict[str,Any] = Field(default_factory=dict)

class StatisticalAnalysisPlan(BaseModel):
    plan_id: str
    core_project_id: str
    title: str
    research_question: str
    runtime_target: RuntimeTarget
    analysis_type: str
    datasets: list[dict[str,Any]]
    methods: list[str]
    assumptions: list[dict[str,Any]]
    requested_outputs: list[str]
    evidence_refs: list[str]
    limitations: list[str]
    execution_policy: dict[str,Any]
    review_decision: ReviewDecision = "pending"
    reviewer_ref: str | None = Field(default=None,max_length=255)
    reviewer_note: str | None = Field(default=None,max_length=5000)
    provenance: dict[str,Any] = Field(default_factory=dict)

class CoreStatisticalValidationPromotionRequest(BaseModel):
    plan: StatisticalAnalysisPlan
    result_ref: str = Field(min_length=1,max_length=255)
    validation_evidence: dict[str,Any]
    reasoning_ref: str | None = Field(default=None,max_length=255)
    visibility: str = Field(default="private",max_length=64)

    @model_validator(mode="after")
    def approved(self):
        if self.plan.review_decision != "approved":
            raise ValueError("Core statistical validation promotion requires plan.review_decision='approved'.")
        if not str(self.plan.reviewer_ref or "").strip():
            raise ValueError("Core statistical validation promotion requires plan.reviewer_ref.")
        return self

class CoreCoefficientRequest(BaseModel):
    reasoning_ref: str = Field(min_length=1,max_length=255)
    data: dict[str,Any]

class CoreIntervalRequest(BaseModel):
    reasoning_ref: str = Field(min_length=1,max_length=255)
    data: dict[str,Any]

class CoreInterpretationRequest(BaseModel):
    reasoning_ref: str = Field(min_length=1,max_length=255)
    interpretation_ref: str = Field(min_length=1,max_length=255)
    statement: str = Field(min_length=1,max_length=20000)
    author_ref: str = Field(min_length=1,max_length=255)
    interpretation_type: str = Field(default="researcher_interpretation",max_length=255)
    evidence_refs: list[str] = Field(default_factory=list,max_length=200)
    limitations: list[str] = Field(default_factory=list,max_length=100)
    provenance: dict[str,Any] = Field(default_factory=dict)
    visibility: str = Field(default="private",max_length=64)
