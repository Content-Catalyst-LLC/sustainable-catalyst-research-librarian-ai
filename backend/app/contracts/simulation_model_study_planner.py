from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

SIMULATION_MODEL_STUDY_SCHEMA = "sc-research-librarian-simulation-model-study-planner/1.0"
SIMULATION_MODEL_STUDY_SNAPSHOT_SCHEMA = "sc-research-librarian-simulation-model-study-planner-snapshot/1.0"
PlanState = Literal["draft","in_review","approved","archived"]
ModelClass = Literal["deterministic","stochastic","agent-based","system-dynamics","discrete-event","monte-carlo","optimization","mechanistic","hybrid","surrogate","other"]
VariableKind = Literal["state","input","output","latent","derived","boundary","other"]
ParameterRole = Literal["fixed","calibrated","estimated","sampled","scenario","nuisance","other"]
DistributionFamily = Literal["normal","lognormal","uniform","triangular","beta","gamma","poisson","binomial","empirical","custom","none","other"]
CalibrationMethod = Literal["manual","optimization","bayesian","approximate-bayesian","simulation-based","moment-matching","other"]
ValidationType = Literal["internal","external","cross-validation","holdout","historical","face-validity","extreme-condition","conservation-check","other"]
UncertaintyType = Literal["parameter","structural","initial-condition","measurement","scenario","stochastic","numerical","other"]
SensitivityMethod = Literal["local","one-at-a-time","morris","sobol","fast","variance-based","scenario","threshold","other"]
EnsembleMethod = Literal["equal-weight","performance-weighted","bayesian-model-averaging","stacking","scenario-ensemble","other"]
Decision = Literal["pending","approved","rejected","waived"]

class SimulationModelStudyCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    study_ref: str = Field(min_length=1,max_length=2000)
    causal_design_id: str = Field(min_length=1,max_length=255)
    purpose: str = Field(default="prospective simulation and model study planning",max_length=5000)
    core_project_id: str = Field(default="",max_length=255)
    metadata: dict[str,Any] = Field(default_factory=dict)

class SimulationModelSpecificationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    model_class: ModelClass
    purpose: str = Field(min_length=1,max_length=10000)
    equations_or_rules_ref: str = Field(default="",max_length=5000)
    preferred_runtime: str = Field(default="research-lab",max_length=255)
    assumptions: list[str] = Field(default_factory=list,max_length=5000)
    limitations: list[str] = Field(default_factory=list,max_length=5000)

class SimulationVariableAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    variable_ref: str = Field(min_length=1,max_length=2000)
    label: str = Field(min_length=1,max_length=1000)
    kind: VariableKind
    units: str = Field(default="",max_length=255)
    definition: str = Field(default="",max_length=10000)
    initial_or_boundary_value: str = Field(default="",max_length=5000)

class SimulationParameterAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    parameter_ref: str = Field(min_length=1,max_length=2000)
    label: str = Field(min_length=1,max_length=1000)
    role: ParameterRole
    units: str = Field(default="",max_length=255)
    baseline_value: str = Field(default="",max_length=5000)
    plausible_range: str = Field(default="",max_length=5000)
    source_refs: list[str] = Field(default_factory=list,max_length=5000)

class SimulationScenarioSetAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    model_specification_ids: list[str] = Field(min_length=1,max_length=5000)
    scenarios: list[dict[str,Any]] = Field(min_length=1,max_length=5000)
    comparison_basis: str = Field(min_length=1,max_length=10000)
    interpretation_boundary: str = Field(default="",max_length=10000)

class SimulationStochasticAssumptionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    target_ref: str = Field(min_length=1,max_length=2000)
    distribution_family: DistributionFamily
    distribution_parameters: dict[str,Any] = Field(default_factory=dict)
    dependence_structure: str = Field(default="",max_length=10000)
    rationale: str = Field(default="",max_length=10000)

class SimulationCalibrationPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    model_specification_ids: list[str] = Field(min_length=1,max_length=5000)
    method: CalibrationMethod
    target_refs: list[str] = Field(default_factory=list,max_length=5000)
    dataset_refs: list[str] = Field(default_factory=list,max_length=5000)
    objective_or_likelihood: str = Field(default="",max_length=10000)
    acceptance_criteria: list[str] = Field(default_factory=list,max_length=5000)

class SimulationValidationPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    model_specification_ids: list[str] = Field(min_length=1,max_length=5000)
    validation_type: ValidationType
    dataset_refs: list[str] = Field(default_factory=list,max_length=5000)
    metrics: list[str] = Field(default_factory=list,max_length=5000)
    acceptance_criteria: list[str] = Field(default_factory=list,max_length=5000)
    interpretation_boundary: str = Field(default="",max_length=10000)

class SimulationUncertaintyPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    uncertainty_type: UncertaintyType
    target_refs: list[str] = Field(default_factory=list,max_length=5000)
    procedure: str = Field(min_length=1,max_length=10000)
    sample_count: int | None = Field(default=None,ge=1)
    seed_policy: str = Field(default="record-and-freeze-seed",max_length=1000)
    interpretation_boundary: str = Field(default="",max_length=10000)

class SimulationSensitivityPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    method: SensitivityMethod
    parameter_ids: list[str] = Field(default_factory=list,max_length=5000)
    output_refs: list[str] = Field(default_factory=list,max_length=5000)
    procedure: str = Field(min_length=1,max_length=10000)
    interpretation_boundary: str = Field(default="",max_length=10000)

class SimulationEnsemblePlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    model_specification_ids: list[str] = Field(min_length=2,max_length=5000)
    method: EnsembleMethod
    weighting_rule: str = Field(default="",max_length=10000)
    disagreement_reporting: str = Field(default="report model-specific and ensemble results separately",max_length=10000)

class SimulationComputeBudgetRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    max_runs: int | None = Field(default=None,ge=1)
    max_wall_time_minutes: int | None = Field(default=None,ge=1)
    max_memory_gb: float | None = Field(default=None,gt=0)
    max_cost_usd: float | None = Field(default=None,ge=0)
    parallelism_limit: int | None = Field(default=None,ge=1)
    note: str = Field(default="",max_length=10000)

class SimulationStoppingCriterionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    criterion: str = Field(min_length=1,max_length=10000)
    rationale: str = Field(default="",max_length=10000)

class SimulationOutputCommitmentAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    output_ref: str = Field(min_length=1,max_length=2000)
    summary_or_metric: str = Field(min_length=1,max_length=10000)
    aggregation: str = Field(default="",max_length=5000)
    visualization_or_table: str = Field(default="",max_length=5000)
    reporting_commitment: str = Field(default="report planned output with uncertainty and limitations",max_length=10000)

class SimulationStudyDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    object_type: Literal["model-specification","scenario-set","calibration-plan","validation-plan","uncertainty-plan","sensitivity-plan","ensemble-plan"]
    object_id: str = Field(min_length=1,max_length=255)
    decision: Decision
    rationale: str = Field(default="",max_length=10000)

class SimulationModelStudyStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: PlanState
    note: str = Field(default="",max_length=10000)

class SimulationModelStudySnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    simulation_study_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="simulation-model-study-planner-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
