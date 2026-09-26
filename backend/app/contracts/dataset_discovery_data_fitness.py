from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

DATASET_DISCOVERY_FITNESS_SCHEMA = "sc-research-librarian-dataset-discovery-data-fitness/1.0"
DATASET_DISCOVERY_FITNESS_SNAPSHOT_SCHEMA = "sc-research-librarian-dataset-discovery-data-fitness-snapshot/1.0"
FitnessDecision = Literal["pending","fit","fit-with-limitations","not-fit"]
ReviewState = Literal["draft","in_review","approved","archived"]

class DatasetFitnessCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    project_ref: str = Field(min_length=1,max_length=2000)
    research_question: str = Field(default="",max_length=20000)
    gap_novelty_id: str = Field(default="",max_length=255)
    research_opportunity_ids: list[str] = Field(default_factory=list,max_length=5000)
    core_project_id: str = Field(default="",max_length=255)
    metadata: dict[str,Any] = Field(default_factory=dict)

class DatasetCandidateAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    source_ref: str = Field(min_length=1,max_length=4000)
    title: str = Field(min_length=1,max_length=1000)
    provider: str = Field(default="",max_length=1000)
    landing_page: str = Field(default="",max_length=4000)
    identifiers: dict[str,str] = Field(default_factory=dict)
    description: str = Field(default="",max_length=20000)
    geography: list[str] = Field(default_factory=list,max_length=5000)
    populations: list[str] = Field(default_factory=list,max_length=5000)
    temporal_coverage: str = Field(default="",max_length=2000)
    access_mode: str = Field(default="unknown",max_length=255)
    license: str = Field(default="unknown",max_length=2000)
    provenance_notes: str = Field(default="",max_length=10000)
    metadata: dict[str,Any] = Field(default_factory=dict)

class DatasetVariableAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    dataset_id: str = Field(min_length=1,max_length=255)
    name: str = Field(min_length=1,max_length=1000)
    label: str = Field(default="",max_length=2000)
    role: Literal["outcome","exposure","predictor","confounder","mediator","moderator","identifier","weight","time","geography","other"] = "other"
    data_type: str = Field(default="unknown",max_length=255)
    unit: str = Field(default="",max_length=255)
    missingness_note: str = Field(default="",max_length=5000)
    transformation_notes: str = Field(default="",max_length=5000)
    metadata: dict[str,Any] = Field(default_factory=dict)

class DataRequirementAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    description: str = Field(min_length=1,max_length=10000)
    required_variables: list[str] = Field(default_factory=list,max_length=5000)
    required_geographies: list[str] = Field(default_factory=list,max_length=5000)
    required_populations: list[str] = Field(default_factory=list,max_length=5000)
    required_time_coverage: str = Field(default="",max_length=2000)
    required_access_conditions: list[str] = Field(default_factory=list,max_length=5000)
    opportunity_ids: list[str] = Field(default_factory=list,max_length=5000)

class DatasetFitnessAssessmentRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    dataset_id: str = Field(min_length=1,max_length=255)
    requirement_ids: list[str] = Field(default_factory=list,max_length=5000)
    decision: FitnessDecision = "pending"
    coverage_notes: str = Field(default="",max_length=10000)
    quality_notes: str = Field(default="",max_length=10000)
    missingness_notes: str = Field(default="",max_length=10000)
    provenance_notes: str = Field(default="",max_length=10000)
    licensing_access_notes: str = Field(default="",max_length=10000)
    limitations: list[str] = Field(default_factory=list,max_length=5000)
    rationale: str = Field(default="",max_length=10000)

class DatasetFitnessStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: ReviewState
    note: str = Field(default="",max_length=10000)

class DatasetFitnessSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    data_fitness_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="dataset-discovery-data-fitness-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
