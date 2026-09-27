from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

CAUSAL_RESEARCH_DESIGN_SCHEMA = "sc-research-librarian-causal-research-design-intelligence/1.0"
CAUSAL_RESEARCH_DESIGN_SNAPSHOT_SCHEMA = "sc-research-librarian-causal-research-design-intelligence-snapshot/1.0"
PlanState = Literal["draft","in_review","approved","archived"]
CausalRole = Literal["treatment","exposure","outcome","confounder","mediator","collider","instrument","selection","effect-modifier","negative-control","exogenous","other"]
CausalEdgeType = Literal["causes","affects","selects","measures","proxies","other"]
AssumptionType = Literal["exchangeability","consistency","positivity","no-interference","temporal-order","measurement-validity","exclusion-restriction","instrument-relevance","parallel-trends","continuity","no-anticipation","stable-unit-treatment-value","other"]
Testability = Literal["observable","partially-observable","untestable"]
IdentificationStrategy = Literal["randomized-experiment","backdoor-adjustment","frontdoor-adjustment","instrumental-variable","regression-discontinuity","difference-in-differences","interrupted-time-series","synthetic-control","matching","weighting","g-formula","target-trial-emulation","other"]
DiagnosticType = Literal["overlap","balance","pre-trends","manipulation","first-stage","placebo","negative-control","attrition","missingness","measurement","model-diagnostics","other"]
NegativeControlType = Literal["outcome","exposure","placebo-time","placebo-group","other"]
CausalSensitivityType = Literal["unmeasured-confounding","e-value","rosenbaum-bounds","partial-r2","bias-function","specification","measurement-error","negative-control","other"]
Decision = Literal["pending","approved","rejected","waived"]

class CausalResearchDesignCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    design_ref: str = Field(min_length=1,max_length=2000)
    statistical_analysis_plan_id: str = Field(min_length=1,max_length=255)
    purpose: str = Field(default="prospective causal research design planning",max_length=5000)
    core_project_id: str = Field(default="",max_length=255)
    metadata: dict[str,Any] = Field(default_factory=dict)

class CausalVariableRoleAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    variable_ref: str = Field(min_length=1,max_length=2000)
    label: str = Field(min_length=1,max_length=1000)
    role: CausalRole
    operational_definition: str = Field(default="",max_length=10000)
    temporal_position: str = Field(default="",max_length=5000)
    rationale: str = Field(default="",max_length=10000)

class CausalEdgeAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    source_role_id: str = Field(min_length=1,max_length=255)
    target_role_id: str = Field(min_length=1,max_length=255)
    edge_type: CausalEdgeType = "causes"
    rationale: str = Field(default="",max_length=10000)
    evidence_refs: list[str] = Field(default_factory=list,max_length=5000)

class CausalAssumptionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    assumption_type: AssumptionType
    statement: str = Field(min_length=1,max_length=10000)
    linked_role_ids: list[str] = Field(default_factory=list,max_length=5000)
    testability: Testability = "untestable"
    observable_implication: str = Field(default="",max_length=10000)
    threat_if_violated: str = Field(default="",max_length=10000)

class CausalIdentificationStrategyAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    strategy: IdentificationStrategy
    estimand_ids: list[str] = Field(min_length=1,max_length=5000)
    treatment_or_exposure_role_ids: list[str] = Field(min_length=1,max_length=5000)
    outcome_role_ids: list[str] = Field(min_length=1,max_length=5000)
    adjustment_role_ids: list[str] = Field(default_factory=list,max_length=5000)
    instrument_role_ids: list[str] = Field(default_factory=list,max_length=5000)
    assumption_ids: list[str] = Field(default_factory=list,max_length=5000)
    statistical_model_specification_ids: list[str] = Field(default_factory=list,max_length=5000)
    identification_rationale: str = Field(min_length=1,max_length=10000)
    limitations: list[str] = Field(default_factory=list,max_length=5000)

class CausalDiagnosticPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    diagnostic_type: DiagnosticType
    identification_strategy_ids: list[str] = Field(default_factory=list,max_length=5000)
    procedure: str = Field(min_length=1,max_length=10000)
    interpretation_boundary: str = Field(default="",max_length=10000)

class CausalNegativeControlPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    control_type: NegativeControlType
    identification_strategy_ids: list[str] = Field(default_factory=list,max_length=5000)
    variable_or_period_ref: str = Field(min_length=1,max_length=2000)
    rationale: str = Field(min_length=1,max_length=10000)
    expected_pattern_under_design: str = Field(default="",max_length=10000)

class CausalSensitivityPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    sensitivity_type: CausalSensitivityType
    identification_strategy_ids: list[str] = Field(default_factory=list,max_length=5000)
    procedure: str = Field(min_length=1,max_length=10000)
    target_assumption_ids: list[str] = Field(default_factory=list,max_length=5000)
    interpretation_boundary: str = Field(default="",max_length=10000)

class CausalDesignDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    object_type: Literal["identification-strategy","causal-assumption","diagnostic-plan","negative-control-plan","sensitivity-plan"]
    object_id: str = Field(min_length=1,max_length=255)
    decision: Decision
    rationale: str = Field(default="",max_length=10000)

class CausalResearchDesignStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: PlanState
    note: str = Field(default="",max_length=10000)

class CausalResearchDesignSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    causal_design_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="causal-research-design-intelligence-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
