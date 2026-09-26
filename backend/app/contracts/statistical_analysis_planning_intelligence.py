from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

STATISTICAL_ANALYSIS_PLANNING_SCHEMA = "sc-research-librarian-statistical-analysis-planning-intelligence/1.0"
STATISTICAL_ANALYSIS_PLANNING_SNAPSHOT_SCHEMA = "sc-research-librarian-statistical-analysis-planning-intelligence-snapshot/1.0"
PlanState = Literal["draft","in_review","approved","archived"]
EstimandType = Literal["mean","difference-in-means","risk-difference","risk-ratio","odds-ratio","rate-ratio","hazard-ratio","correlation","regression-coefficient","average-treatment-effect","conditional-treatment-effect","quantile","other"]
ModelFamily = Literal["linear","generalized-linear","mixed-effects","survival","time-series","panel","nonparametric","bayesian","causal","machine-learning","other"]
AnalysisDecision = Literal["pending","approved","rejected","waived"]
AssumptionStatus = Literal["planned-check","not-applicable","requires-review"]
MultiplicityFamily = Literal["none","family-wise-error","false-discovery-rate","hierarchical","gatekeeping","other"]
MissingDataStrategy = Literal["complete-case","multiple-imputation","inverse-probability-weighting","maximum-likelihood","model-based","sensitivity-analysis","other"]
SensitivityType = Literal["model-specification","missing-data","unmeasured-confounding","outlier-influence","measurement-error","alternative-estimand","subgroup","robustness","other"]

class StatisticalAnalysisPlanningCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    plan_ref: str = Field(min_length=1,max_length=2000)
    study_protocol_id: str = Field(min_length=1,max_length=255)
    purpose: str = Field(default="prospective statistical analysis planning",max_length=5000)
    computational_plan_id: str = Field(default="",max_length=255)
    core_project_id: str = Field(default="",max_length=255)
    metadata: dict[str,Any] = Field(default_factory=dict)

class StatisticalEstimandAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    estimand_type: EstimandType = "other"
    population: str = Field(min_length=1,max_length=10000)
    treatment_or_exposure: str = Field(default="",max_length=5000)
    comparator: str = Field(default="",max_length=5000)
    outcome: str = Field(min_length=1,max_length=5000)
    time_horizon: str = Field(default="",max_length=1000)
    summary_measure: str = Field(default="",max_length=5000)
    protocol_hypothesis_ids: list[str] = Field(default_factory=list,max_length=5000)
    protocol_outcome_ids: list[str] = Field(default_factory=list,max_length=5000)
    protocol_variable_ids: list[str] = Field(default_factory=list,max_length=5000)
    rationale: str = Field(default="",max_length=10000)

class StatisticalModelSpecificationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    estimand_ids: list[str] = Field(min_length=1,max_length=5000)
    model_family: ModelFamily
    method: str = Field(min_length=1,max_length=5000)
    outcome_variable_refs: list[str] = Field(default_factory=list,max_length=5000)
    predictor_variable_refs: list[str] = Field(default_factory=list,max_length=5000)
    covariate_variable_refs: list[str] = Field(default_factory=list,max_length=5000)
    interaction_terms: list[str] = Field(default_factory=list,max_length=5000)
    link_function: str = Field(default="",max_length=255)
    weighting_strategy: str = Field(default="",max_length=5000)
    clustering_or_dependence: str = Field(default="",max_length=5000)
    computational_plan_step_ids: list[str] = Field(default_factory=list,max_length=5000)
    rationale: str = Field(default="",max_length=10000)

class StatisticalAssumptionCheckAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    model_specification_ids: list[str] = Field(default_factory=list,max_length=5000)
    assumption: str = Field(min_length=1,max_length=10000)
    planned_diagnostic: str = Field(min_length=1,max_length=10000)
    response_if_challenged: str = Field(default="",max_length=10000)
    status: AssumptionStatus = "planned-check"

class StatisticalPowerSampleSizePlanRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    target_sample_size: int | None = Field(default=None,ge=1)
    analysis_population: str = Field(default="",max_length=5000)
    effect_size_basis: str = Field(default="",max_length=10000)
    alpha_or_error_rate: str = Field(default="",max_length=255)
    target_power: str = Field(default="",max_length=255)
    sidedness: str = Field(default="",max_length=255)
    attrition_allowance: str = Field(default="",max_length=1000)
    design_effect_or_clustering: str = Field(default="",max_length=5000)
    calculation_runtime_ref: str = Field(default="",max_length=2000)
    calculation_artifact_ref: str = Field(default="",max_length=2000)
    rationale: str = Field(default="",max_length=10000)

class StatisticalMultiplicityPlanRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    family: MultiplicityFamily = "none"
    hypothesis_or_estimand_ids: list[str] = Field(default_factory=list,max_length=5000)
    procedure: str = Field(default="",max_length=5000)
    error_rate_target: str = Field(default="",max_length=255)
    rationale: str = Field(default="",max_length=10000)

class StatisticalMissingDataPlanRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    strategy: MissingDataStrategy
    variables_or_outcomes: list[str] = Field(default_factory=list,max_length=5000)
    missingness_assumptions: list[str] = Field(default_factory=list,max_length=5000)
    implementation: str = Field(default="",max_length=10000)
    diagnostics: list[str] = Field(default_factory=list,max_length=5000)
    fallback_or_sensitivity: str = Field(default="",max_length=10000)

class StatisticalSensitivityAnalysisAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    sensitivity_type: SensitivityType
    target_estimand_ids: list[str] = Field(default_factory=list,max_length=5000)
    target_model_specification_ids: list[str] = Field(default_factory=list,max_length=5000)
    analysis: str = Field(min_length=1,max_length=10000)
    interpretation_boundary: str = Field(default="",max_length=10000)

class StatisticalReportingCommitmentAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    content: str = Field(min_length=1,max_length=10000)
    required_outputs: list[str] = Field(default_factory=list,max_length=5000)
    precision_or_interval_commitment: str = Field(default="",max_length=5000)
    p_value_or_threshold_policy: str = Field(default="",max_length=5000)
    effect_size_reporting: str = Field(default="",max_length=5000)
    subgroup_reporting: str = Field(default="",max_length=5000)

class StatisticalAnalysisDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    object_type: Literal["model-specification","power-sample-size-plan","multiplicity-plan","missing-data-plan","sensitivity-analysis","reporting-commitment"]
    object_id: str = Field(min_length=1,max_length=255)
    decision: AnalysisDecision
    rationale: str = Field(default="",max_length=10000)

class StatisticalAnalysisPlanningStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: PlanState
    note: str = Field(default="",max_length=10000)

class StatisticalAnalysisPlanningSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    statistical_analysis_plan_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="statistical-analysis-planning-intelligence-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
