from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

RUNTIME_AUTHORITY_SCHEMA = "sc-research-librarian-runtime-authority-wordpress-decoupling/1.0"
RUNTIME_AUTHORITY_SNAPSHOT_SCHEMA = "sc-research-librarian-runtime-authority-wordpress-decoupling-snapshot/1.0"

class RuntimeAuthoritySnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(default="runtime-authority-wordpress-decoupling-certification", max_length=255)
    note: str = Field(default="", max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)
