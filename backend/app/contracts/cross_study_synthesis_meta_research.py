from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

CROSS_STUDY_SYNTHESIS_SCHEMA = "sc-research-librarian-cross-study-synthesis-meta-research/1.0"
CROSS_STUDY_SYNTHESIS_SNAPSHOT_SCHEMA = "sc-research-librarian-cross-study-synthesis-meta-research-snapshot/1.0"
PlanState = Literal["draft", "in_review", "approved", "archived"]
Decision = Literal["pending", "approved", "rejected", "waived"]
StudyDisposition = Literal["pending", "included", "excluded"]
EvidenceDirection = Literal["positive", "negative", "null", "mixed", "not-assessed"]
SynthesisKind = Literal["multi-study-comparison", "systematic-review-synthesis", "meta-analysis-plan", "replication-synthesis", "evidence-map", "meta-research", "other"]
MethodKind = Literal["narrative", "fixed-effect", "random-effects", "bayesian", "meta-regression", "network-meta-analysis", "evidence-map", "other"]
BiasJudgment = Literal["low", "some-concerns", "high", "unclear", "not-assessed"]

class CrossStudySynthesisCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    research_question: str = Field(min_length=1, max_length=20000)
    synthesis_kind: SynthesisKind = "multi-study-comparison"
    systematic_review_id: str = Field(default="", max_length=255)
    research_program_id: str = Field(default="", max_length=255)
    reproduction_replication_ids: list[str] = Field(default_factory=list, max_length=5000)
    core_project_id: str = Field(default="", max_length=255)
    protocol_note: str = Field(default="", max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class CrossStudyEvidenceAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    study_ref: str = Field(min_length=1, max_length=2000)
    label: str = Field(min_length=1, max_length=1000)
    design: str = Field(default="", max_length=1000)
    population_context: str = Field(default="", max_length=10000)
    sample_size: int | None = Field(default=None, ge=0)
    intervention_exposure: str = Field(default="", max_length=10000)
    comparator: str = Field(default="", max_length=10000)
    outcome: str = Field(default="", max_length=10000)
    effect_measure: str = Field(default="", max_length=1000)
    estimate: float | None = None
    standard_error: float | None = Field(default=None, ge=0)
    ci_lower: float | None = None
    ci_upper: float | None = None
    direction: EvidenceDirection = "not-assessed"
    source_refs: list[str] = Field(default_factory=list, max_length=5000)
    dataset_refs: list[str] = Field(default_factory=list, max_length=5000)
    code_refs: list[str] = Field(default_factory=list, max_length=5000)
    reproduction_replication_id: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=20000)

class CrossStudyDispositionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    study_id: str = Field(min_length=1, max_length=255)
    disposition: StudyDisposition
    rationale: str = Field(min_length=1, max_length=20000)

class CrossStudySynthesisDimensionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    dimension: Literal["population", "setting", "intervention-exposure", "comparator", "outcome", "measurement", "design", "analysis", "time", "data", "implementation", "other"]
    comparison_basis: str = Field(min_length=1, max_length=10000)
    known_differences: list[str] = Field(default_factory=list, max_length=5000)
    interpretation_boundary: str = Field(default="", max_length=10000)

class CrossStudyBiasAssessmentAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    study_id: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=1000)
    judgment: BiasJudgment
    rationale: str = Field(min_length=1, max_length=20000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)

class MetaResearchObservationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    category: Literal["publication-pattern", "reporting-practice", "method-use", "reproducibility", "replication", "data-availability", "code-availability", "citation-pattern", "research-gap", "other"]
    scope: str = Field(min_length=1, max_length=10000)
    observation: str = Field(min_length=1, max_length=20000)
    supporting_refs: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)

class CrossStudySynthesisPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    method_kind: MethodKind
    estimand_or_target: str = Field(min_length=1, max_length=10000)
    included_outcomes: list[str] = Field(default_factory=list, max_length=5000)
    grouping_variables: list[str] = Field(default_factory=list, max_length=5000)
    heterogeneity_metrics: list[str] = Field(default_factory=list, max_length=5000)
    bias_diagnostics: list[str] = Field(default_factory=list, max_length=5000)
    sensitivity_analyses: list[str] = Field(default_factory=list, max_length=5000)
    assumptions: list[str] = Field(default_factory=list, max_length=5000)
    runtime_target: str = Field(default="workspace", max_length=255)
    compute_note: str = Field(default="", max_length=10000)

class CrossStudySynthesisReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    synthesis_plan_id: str = Field(min_length=1, max_length=255)
    execution_ref: str = Field(min_length=1, max_length=2000)
    status: Literal["completed", "partial", "failed-to-run", "cancelled"]
    observed_summary: str = Field(default="", max_length=20000)
    metrics: dict[str, Any] = Field(default_factory=dict)
    pooled_estimates: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)
    artifact_refs: list[str] = Field(default_factory=list, max_length=5000)
    provenance_note: str = Field(default="", max_length=10000)

class CrossStudyHumanInterpretationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    interpretation: str = Field(min_length=1, max_length=30000)
    conclusion_scope: str = Field(default="human-authored interpretation of the assembled cross-study evidence only", max_length=10000)
    limitations: list[str] = Field(default_factory=list, max_length=5000)
    supporting_refs: list[str] = Field(default_factory=list, max_length=5000)

class CrossStudyDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    object_type: Literal["synthesis-plan", "synthesis-dimension", "bias-assessment"]
    object_id: str = Field(min_length=1, max_length=255)
    decision: Decision
    rationale: str = Field(default="", max_length=10000)

class CrossStudyStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: PlanState
    note: str = Field(default="", max_length=10000)

class CrossStudySnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    cross_study_synthesis_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="cross-study-synthesis-meta-research-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
