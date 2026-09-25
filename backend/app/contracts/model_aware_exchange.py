from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

MODEL_AWARE_RESEARCH_SCHEMA = "sc-research-librarian-model-aware-research-intelligence/1.0"
CROSS_PRODUCT_EXCHANGE_SCHEMA = "sc-research-librarian-cross-product-exchange/1.0"
CROSS_PRODUCT_EXCHANGE_RECEIPT_SCHEMA = "sc-research-librarian-cross-product-exchange-receipt/1.0"
MODEL_AWARE_SNAPSHOT_SCHEMA = "sc-research-librarian-model-aware-research-snapshot/1.0"

ExchangeDestination = Literal[
    "platform-core", "workspace", "research-lab", "workbench",
    "knowledge-library", "decision-studio", "site-intelligence",
]
ExchangeStatus = Literal["received", "accepted", "imported", "rejected", "failed"]

class ModelAwareResearchRecordRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    research_question: str = Field(default="", max_length=20000)
    project_ref: str = Field(default="", max_length=2000)
    study_ref: str = Field(default="", max_length=2000)
    publication_ref: str = Field(default="", max_length=2000)
    context_id: str = Field(default="", max_length=255)
    experiment_id: str = Field(default="", max_length=255)
    model_ref: str = Field(default="", max_length=2000)
    model_version_ref: str = Field(default="", max_length=2000)
    dataset_ref: str = Field(default="", max_length=2000)
    dataset_version_ref: str = Field(default="", max_length=2000)
    prompt_ref: str = Field(default="", max_length=2000)
    prompt_version_ref: str = Field(default="", max_length=2000)
    inference_run_ref: str = Field(default="", max_length=2000)
    evaluation_ids: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    claim_refs: list[str] = Field(default_factory=list, max_length=5000)
    finding_refs: list[str] = Field(default_factory=list, max_length=5000)
    statistical_refs: list[str] = Field(default_factory=list, max_length=5000)
    visual_refs: list[str] = Field(default_factory=list, max_length=5000)
    artifact_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class CrossProductExchangeCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    record_id: str = Field(min_length=1, max_length=255)
    destination: ExchangeDestination
    purpose: str = Field(min_length=1, max_length=5000)
    payload_contract_ref: str = Field(default="", max_length=2000)
    included_sections: list[str] = Field(default_factory=list, max_length=100)
    additional_object_refs: list[str] = Field(default_factory=list, max_length=5000)
    destination_project_ref: str = Field(default="", max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class CrossProductExchangeReceiptRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    status: ExchangeStatus
    external_receipt_ref: str = Field(default="", max_length=2000)
    destination_object_refs: list[str] = Field(default_factory=list, max_length=5000)
    note: str = Field(default="", max_length=20000)
    error: str = Field(default="", max_length=20000)

class ModelAwareSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    record_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="model-aware-research-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
