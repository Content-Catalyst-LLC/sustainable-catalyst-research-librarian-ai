from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

SCHOLARLY_RESEARCH_SCHEMA = "sc-research-librarian-original-scholarly-research/1.0"
SCHOLARLY_REVISION_SCHEMA = "sc-research-librarian-scholarly-study-revision/1.0"
SCHOLARLY_PACKAGE_SCHEMA = "sc-research-librarian-scholarly-research-package/1.0"
PUBLICATION_READINESS_SCHEMA = "sc-research-librarian-publication-readiness/1.0"

StudyType = Literal[
    "observational", "experimental", "quasi-experimental", "modeling",
    "systematic-review", "evidence-synthesis", "qualitative", "mixed-methods",
    "methodological", "case-study", "other",
]


class ScholarlyProtocol(BaseModel):
    aims: list[str] = Field(default_factory=list, max_length=50)
    hypotheses: list[str] = Field(default_factory=list, max_length=100)
    population_or_system: str = Field(default="", max_length=10_000)
    sampling_or_case_selection: str = Field(default="", max_length=10_000)
    inclusion_criteria: list[str] = Field(default_factory=list, max_length=100)
    exclusion_criteria: list[str] = Field(default_factory=list, max_length=100)
    exposures_or_predictors: list[str] = Field(default_factory=list, max_length=200)
    outcomes_or_endpoints: list[str] = Field(default_factory=list, max_length=200)
    variables_or_constructs: list[str] = Field(default_factory=list, max_length=500)
    methods: str = Field(default="", max_length=30_000)
    analysis_plan: str = Field(default="", max_length=30_000)
    data_management_plan: str = Field(default="", max_length=20_000)
    preregistration_ref: str = Field(default="", max_length=1000)
    ethics_review_status: Literal["not-applicable", "not-started", "pending", "approved", "exempt", "declared-other"] = "not-started"
    ethics_review_ref: str = Field(default="", max_length=1000)
    deviations_policy: str = Field(default="", max_length=10_000)


class ScholarlyStudyCreateRequest(BaseModel):
    core_project_id: str = Field(min_length=1, max_length=255)
    local_project_id: str | None = Field(default=None, max_length=220)
    workflow_id: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    research_question: str = Field(min_length=1, max_length=10_000)
    study_type: StudyType
    protocol: ScholarlyProtocol = Field(default_factory=ScholarlyProtocol)
    authors: list[str] = Field(default_factory=list, max_length=100)
    affiliations: list[str] = Field(default_factory=list, max_length=100)
    funding_statement: str = Field(default="", max_length=10_000)
    conflict_of_interest_statement: str = Field(default="", max_length=10_000)
    source_refs: list[str] = Field(default_factory=list, max_length=5000)
    core_evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    core_research_object_refs: list[str] = Field(default_factory=list, max_length=5000)
    statistical_reasoning_refs: list[str] = Field(default_factory=list, max_length=1000)
    visual_refs: list[str] = Field(default_factory=list, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=500)


class ScholarlyProtocolFreezeRequest(BaseModel):
    reviewer_ref: str = Field(min_length=1, max_length=255)
    note: str = Field(default="", max_length=4000)


class ScholarlyDeviationRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    category: Literal["protocol", "sampling", "measurement", "analysis", "data", "other"]
    description: str = Field(min_length=1, max_length=20_000)
    rationale: str = Field(default="", max_length=20_000)
    impact_assessment: str = Field(default="", max_length=20_000)


class ScholarlyResultRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    result_type: Literal["descriptive", "statistical", "qualitative", "model", "simulation", "mixed", "other"]
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=30_000)
    runtime_ref: str = Field(default="", max_length=1000)
    artifact_ref: str = Field(default="", max_length=2000)
    content_hash: str = Field(default="", max_length=128)
    statistical_reasoning_ref: str = Field(default="", max_length=1000)
    visual_refs: list[str] = Field(default_factory=list, max_length=1000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    limitations: list[str] = Field(default_factory=list, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScholarlyInterpretationRequest(BaseModel):
    author_ref: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=30_000)
    result_refs: list[str] = Field(default_factory=list, max_length=1000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    uncertainty_or_qualification: str = Field(default="", max_length=20_000)


class ScholarlyManuscriptSectionRequest(BaseModel):
    author_ref: str = Field(min_length=1, max_length=255)
    section: Literal[
        "title", "abstract", "introduction", "literature-review", "methods",
        "results", "discussion", "limitations", "conclusion", "data-availability",
        "code-availability", "ethics", "funding", "conflicts", "acknowledgements", "other",
    ]
    heading: str = Field(default="", max_length=500)
    text: str = Field(min_length=1, max_length=100_000)
    citation_refs: list[str] = Field(default_factory=list, max_length=5000)


class ScholarlyReviewRequest(BaseModel):
    reviewer_ref: str = Field(min_length=1, max_length=255)
    decision: Literal["approved", "changes-requested", "rejected"]
    scope: Literal["protocol", "results", "interpretation", "manuscript", "package", "study"]
    note: str = Field(default="", max_length=20_000)


class ScholarlyPackageFreezeRequest(BaseModel):
    reviewer_ref: str = Field(min_length=1, max_length=255)
    package_label: str = Field(default="research-package", max_length=255)
    note: str = Field(default="", max_length=10_000)
    require_publication_ready: bool = True

    @model_validator(mode="after")
    def reviewer_required(self):
        if not self.reviewer_ref.strip():
            raise ValueError("reviewer_ref is required to freeze a scholarly package")
        return self
