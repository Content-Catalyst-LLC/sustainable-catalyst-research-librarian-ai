from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

CORE_INTEGRATION_SCHEMA = "sc-research-librarian-platform-core/1.0"
CORE_BINDING_SCHEMA = "sc-research-librarian-core-binding/1.0"
CORE_MINIMUM_VERSION = "3.3.0"
CORE_SUPPORTED_MAJOR = 3


class CoreResearchObjectPromotionRequest(BaseModel):
    local_object_id: str = Field(min_length=1, max_length=255)
    object_type: Literal[
        "research-project",
        "model",
        "model-version",
        "variable",
        "parameter",
        "scenario",
        "model-run",
        "result",
    ]
    name: str = Field(min_length=1, max_length=300)
    slug: str | None = Field(default=None, max_length=200)
    description: str | None = None
    visibility: Literal["public", "internal", "private"] = "private"
    status: str = Field(default="active", max_length=50)
    attributes: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    project_id: str | None = Field(default=None, max_length=255)
    idempotency_key: str | None = Field(default=None, max_length=160)


class CoreUnifiedProjectSyncRequest(BaseModel):
    local_project_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=400)
    project_key: str | None = Field(default=None, max_length=200)
    abstract: str | None = None
    research_question: str | None = None
    objective: str | None = None
    methodology: str | None = None
    research_type: str = Field(default="general", max_length=80)
    lifecycle_state: str = Field(default="draft", max_length=80)
    visibility: Literal["public", "internal", "private"] = "private"
    reproducibility_target: str = Field(default="reproducible", max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)
    scope: dict[str, Any] = Field(default_factory=dict)
    ethics: dict[str, Any] = Field(default_factory=dict)
    governance: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=160)


class CoreExchangeItem(BaseModel):
    artifact_type: str = Field(default="evidence", max_length=80)
    subject_type: str = Field(min_length=1, max_length=120)
    subject_id: str = Field(min_length=1, max_length=255)
    snapshot_mode: str = Field(default="reference", max_length=80)
    evidence_role: str = Field(default="inherited", max_length=80)
    provenance: dict[str, Any] = Field(default_factory=dict)


class CoreExchangePackageRequest(BaseModel):
    local_exchange_id: str = Field(min_length=1, max_length=255)
    target_product: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=400)
    purpose: str | None = None
    visibility: Literal["public", "internal", "private"] = "internal"
    items: list[CoreExchangeItem] = Field(min_length=1, max_length=100)
    provenance: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=160)
