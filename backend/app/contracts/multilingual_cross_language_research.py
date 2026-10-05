from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

MULTILINGUAL_RESEARCH_SCHEMA = "sc-research-librarian-multilingual-cross-language-research/1.0"
MULTILINGUAL_RESEARCH_SNAPSHOT_SCHEMA = "sc-research-librarian-multilingual-cross-language-research-snapshot/1.0"
LANGUAGE_PROFILE_SCHEMA = "sc-research-librarian-language-profile/1.0"
SOURCE_TEXT_SCHEMA = "sc-research-librarian-original-language-source-text/1.0"
DERIVED_REPRESENTATION_SCHEMA = "sc-research-librarian-derived-language-representation/1.0"
TEXT_ALIGNMENT_SCHEMA = "sc-research-librarian-text-alignment/1.0"
CROSS_LANGUAGE_QUERY_PLAN_SCHEMA = "sc-research-librarian-cross-language-query-plan/1.0"
CROSS_LANGUAGE_RETRIEVAL_RECEIPT_SCHEMA = "sc-research-librarian-cross-language-retrieval-receipt/1.0"

MultilingualResearchState = Literal["draft", "active", "review", "closed", "archived"]
TextDirection = Literal["ltr", "rtl", "ttb", "btt", "unknown"]
IdentificationMethod = Literal["source-metadata", "human", "external-tool", "imported", "unknown"]
RepresentationType = Literal["translation", "transliteration", "normalization"]
RepresentationMethod = Literal["human", "machine", "hybrid", "imported", "unknown"]
ReviewStatus = Literal["draft", "reviewed", "rejected", "not-reviewed"]
AlignmentGranularity = Literal["document", "section", "paragraph", "sentence", "token", "mixed"]
QueryStrategy = Literal["original-language-first", "parallel-query", "cross-lingual-semantic", "hybrid"]

class MultilingualResearchCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    project_ref: str = Field(default="", max_length=2000)
    research_question_ref: str = Field(default="", max_length=2000)
    objective: str = Field(default="", max_length=30000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class LanguageProfileAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    language_tag: str = Field(min_length=1, max_length=64)
    language_name: str = Field(default="", max_length=500)
    script_code: str = Field(default="", max_length=64)
    region: str = Field(default="", max_length=500)
    variant: str = Field(default="", max_length=500)
    historical_period: str = Field(default="", max_length=1000)
    direction: TextDirection = "unknown"
    identification_method: IdentificationMethod = "unknown"
    source_ref: str = Field(default="", max_length=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class OriginalLanguageSourceTextAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    source_ref: str = Field(min_length=1, max_length=4000)
    source_hash: str = Field(default="", max_length=255)
    language_profile_id: str = Field(min_length=1, max_length=255)
    text_ref: str = Field(min_length=1, max_length=4000)
    text_hash: str = Field(default="", max_length=255)
    source_locator: str = Field(default="", max_length=4000)
    extraction_lineage_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class DerivedLanguageRepresentationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    source_text_id: str = Field(min_length=1, max_length=255)
    representation_type: RepresentationType
    target_language_profile_id: str = Field(min_length=1, max_length=255)
    derived_text_ref: str = Field(min_length=1, max_length=4000)
    derived_text_hash: str = Field(default="", max_length=255)
    method: RepresentationMethod = "unknown"
    provider_ref: str = Field(default="", max_length=4000)
    model_ref: str = Field(default="", max_length=4000)
    tool_version: str = Field(default="", max_length=500)
    reviewer_ref: str = Field(default="", max_length=2000)
    review_status: ReviewStatus = "not-reviewed"
    transformation_refs: list[str] = Field(default_factory=list, max_length=5000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

class TextAlignmentAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    source_text_id: str = Field(min_length=1, max_length=255)
    derived_representation_id: str = Field(min_length=1, max_length=255)
    granularity: AlignmentGranularity
    alignment_ref: str = Field(min_length=1, max_length=4000)
    alignment_hash: str = Field(default="", max_length=255)
    method: RepresentationMethod = "unknown"
    segment_count: int = Field(default=0, ge=0, le=100000000)
    reviewer_ref: str = Field(default="", max_length=2000)
    review_status: ReviewStatus = "not-reviewed"
    metadata: dict[str, Any] = Field(default_factory=dict)

class CrossLanguageQueryPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    query_ref: str = Field(min_length=1, max_length=4000)
    source_language_profile_id: str = Field(min_length=1, max_length=255)
    target_language_profile_ids: list[str] = Field(min_length=1, max_length=100)
    strategy: QueryStrategy = "original-language-first"
    derived_query_refs: list[str] = Field(default_factory=list, max_length=5000)
    representation_refs: list[str] = Field(default_factory=list, max_length=5000)
    retrieval_constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

class CrossLanguageRetrievalReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    query_plan_id: str = Field(min_length=1, max_length=255)
    execution_ref: str = Field(min_length=1, max_length=4000)
    result_refs: list[str] = Field(default_factory=list, max_length=10000)
    result_language_profile_ids: list[str] = Field(default_factory=list, max_length=100)
    retrieval_profile: str = Field(default="", max_length=1000)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    provenance_note: str = Field(default="", max_length=20000)

class MultilingualResearchStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: MultilingualResearchState
    note: str = Field(default="", max_length=20000)

class MultilingualResearchSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    multilingual_research_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="multilingual-cross-language-research-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
