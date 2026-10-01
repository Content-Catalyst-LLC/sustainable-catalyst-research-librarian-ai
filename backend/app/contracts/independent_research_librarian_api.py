from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

INDEPENDENT_API_SCHEMA = "sc-research-librarian-independent-api/1.0"
INDEPENDENT_API_ENVELOPE_SCHEMA = "sc-research-librarian-independent-api-envelope/1.0"
INDEPENDENT_API_SNAPSHOT_SCHEMA = "sc-research-librarian-independent-api-contract-snapshot/1.0"

class IndependentRetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=3000)
    limit: int = Field(default=10, ge=1, le=25)
    include_semantic: bool = True
    include_diagnostics: bool = True
    advanced: bool = True
    max_queries: int | None = Field(default=None, ge=1, le=8)
    candidate_pool: int | None = Field(default=None, ge=5, le=25)
    filters: dict[str, Any] = Field(default_factory=dict)

class IndependentAPIContractSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(default="independent-research-librarian-api-v1", max_length=255)
    note: str = Field(default="", max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)
