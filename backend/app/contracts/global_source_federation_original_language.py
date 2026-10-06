from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

GLOBAL_SOURCE_FEDERATION_SCHEMA = "sc-research-librarian-global-source-federation-original-language/1.0"
GLOBAL_SOURCE_FEDERATION_SNAPSHOT_SCHEMA = "sc-research-librarian-global-source-federation-snapshot/1.0"
FEDERATED_SOURCE_SCHEMA = "sc-research-librarian-federated-source/1.0"
ORIGINAL_LANGUAGE_ACQUISITION_SCHEMA = "sc-research-librarian-original-language-acquisition/1.0"
SOURCE_INGESTION_RECEIPT_SCHEMA = "sc-research-librarian-source-ingestion-receipt/1.0"
SOURCE_TRUST_PREFERENCE_SCHEMA = "sc-research-librarian-source-trust-preference/1.0"
FEDERATION_QUERY_PLAN_SCHEMA = "sc-research-librarian-federation-query-plan/1.0"
FEDERATION_RETRIEVAL_RECEIPT_SCHEMA = "sc-research-librarian-federation-retrieval-receipt/1.0"

FederationState = Literal["draft", "active", "review", "closed", "archived"]
SourceType = Literal[
    "government", "university", "library", "archive", "journal", "repository",
    "dataset", "standards-body", "ngo", "intergovernmental", "website", "other"
]
AccessMethod = Literal["api", "feed", "file", "connector", "web", "manual", "other"]
AcquisitionMethod = Literal[
    "api", "feed", "file-import", "connector", "web-fetch", "manual", "ocr", "htr",
    "transcription", "other"
]
IngestionStatus = Literal["observed", "accepted", "partial", "rejected", "failed"]
TrustPreference = Literal["trusted", "neutral", "restricted", "excluded"]
FederationQueryStrategy = Literal[
    "original-language-first", "source-native", "parallel-source", "cross-language", "hybrid"
]


class GlobalSourceFederationCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    project_ref: str = Field(default="", max_length=2000)
    multilingual_research_ref: str = Field(default="", max_length=2000)
    objective: str = Field(default="", max_length=30000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FederatedSourceAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    source_type: SourceType
    source_ref: str = Field(min_length=1, max_length=4000)
    institution: str = Field(default="", max_length=1000)
    jurisdiction: str = Field(default="", max_length=1000)
    base_uri: str = Field(default="", max_length=4000)
    access_method: AccessMethod = "connector"
    connector_ref: str = Field(default="", max_length=4000)
    language_profile_refs: list[str] = Field(default_factory=list, max_length=500)
    collection_refs: list[str] = Field(default_factory=list, max_length=5000)
    rights_note: str = Field(default="", max_length=10000)
    access_note: str = Field(default="", max_length=10000)
    quality_signals: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OriginalLanguageAcquisitionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    federated_source_id: str = Field(min_length=1, max_length=255)
    external_record_ref: str = Field(min_length=1, max_length=4000)
    source_locator: str = Field(default="", max_length=4000)
    language_profile_ref: str = Field(min_length=1, max_length=2000)
    original_content_ref: str = Field(min_length=1, max_length=4000)
    original_content_hash: str = Field(default="", max_length=255)
    acquisition_method: AcquisitionMethod
    acquisition_execution_ref: str = Field(default="", max_length=4000)
    extraction_lineage_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceIngestionReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    acquisition_id: str = Field(min_length=1, max_length=255)
    execution_ref: str = Field(min_length=1, max_length=4000)
    status: IngestionStatus = "observed"
    normalized_record_ref: str = Field(default="", max_length=4000)
    normalized_record_hash: str = Field(default="", max_length=255)
    transformation_refs: list[str] = Field(default_factory=list, max_length=5000)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    provenance_note: str = Field(default="", max_length=20000)


class SourceTrustPreferenceAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    user_ref: str = Field(min_length=1, max_length=2000)
    federated_source_id: str = Field(min_length=1, max_length=255)
    preference: TrustPreference = "neutral"
    rationale: str = Field(default="", max_length=20000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FederationQueryPlanAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    query_ref: str = Field(min_length=1, max_length=4000)
    source_language_profile_ref: str = Field(default="", max_length=2000)
    target_federated_source_ids: list[str] = Field(min_length=1, max_length=500)
    target_language_profile_refs: list[str] = Field(default_factory=list, max_length=500)
    strategy: FederationQueryStrategy = "original-language-first"
    derived_query_refs: list[str] = Field(default_factory=list, max_length=5000)
    retrieval_constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FederationRetrievalReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    query_plan_id: str = Field(min_length=1, max_length=255)
    execution_ref: str = Field(min_length=1, max_length=4000)
    result_refs: list[str] = Field(default_factory=list, max_length=10000)
    result_federated_source_ids: list[str] = Field(default_factory=list, max_length=500)
    result_language_profile_refs: list[str] = Field(default_factory=list, max_length=500)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    provenance_note: str = Field(default="", max_length=20000)


class GlobalSourceFederationStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: FederationState
    note: str = Field(default="", max_length=20000)


class GlobalSourceFederationSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    federation_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="global-source-federation-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
