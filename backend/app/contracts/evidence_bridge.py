from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

CORE_EVIDENCE_BRIDGE_SCHEMA = "sc-research-librarian-core-evidence-bridge/1.0"


class CoreSourceSnapshotPromotionRequest(BaseModel):
    canonical_source_id: str = Field(min_length=1, max_length=255)
    local_snapshot_id: str | None = Field(default=None, max_length=255)
    source_instance_id: str | None = Field(default=None, max_length=255)
    content: str | None = Field(default=None, max_length=5_000_000)
    content_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    title: str | None = Field(default=None, max_length=500)
    publisher: str | None = Field(default=None, max_length=300)
    published_at: datetime | None = None
    retrieved_at: datetime | None = None
    media_type: str | None = Field(default=None, max_length=150)
    storage_uri: str | None = Field(default=None, max_length=2000)
    archived_url: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="research-librarian", min_length=1, max_length=300)
    idempotency_key: str | None = Field(default=None, max_length=160)


class CorePassageEvidencePromotionRequest(BaseModel):
    local_evidence_id: str = Field(min_length=1, max_length=255)
    canonical_source_id: str = Field(min_length=1, max_length=255)
    source_snapshot_local_id: str = Field(min_length=1, max_length=255)
    statement: str = Field(min_length=1, max_length=20_000)
    passage_id: str | None = Field(default=None, max_length=255)
    chunk_id: str | None = Field(default=None, max_length=255)
    section_path: list[str] = Field(default_factory=list, max_length=40)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    evidence_type: str = Field(default="source-passage", min_length=1, max_length=100)
    stance: Literal["supports", "contradicts", "contextualizes", "neutral"] = "neutral"
    claim_id: str | None = Field(default=None, max_length=255)
    subject_entity_id: str | None = Field(default=None, max_length=255)
    methodology: str | None = Field(default=None, max_length=20_000)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    review_status: str = Field(default="unreviewed", max_length=50)
    provenance: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="research-librarian", min_length=1, max_length=300)
    idempotency_key: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def page_range_is_ordered(self):
        if self.page_start is not None and self.page_end is not None and self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self
