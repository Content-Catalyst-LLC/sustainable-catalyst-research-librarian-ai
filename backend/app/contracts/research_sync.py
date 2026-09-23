from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

CORE_RESEARCH_SYNC_SCHEMA = "sc-research-librarian-core-research-sync/1.0"
CORE_PROJECT_STATE_CONTRACT = "sc.research.project-state-versioning-reproducibility.v1"


class CoreProjectSynchronizationRequest(BaseModel):
    local_project_id: str = Field(min_length=1, max_length=220)
    include_contexts: bool = True
    include_rooms: bool = True
    include_sources: bool = True
    include_entities: bool = True
    include_questions: bool = True
    include_lifecycles: bool = True
    freeze_version: bool = True
    create_snapshot: bool = True
    visibility: Literal["private", "internal", "public"] = "internal"
    created_by: str = Field(default="research-librarian", max_length=255)
    dry_run: bool = False


class CoreProjectSynchronizationPlanRequest(BaseModel):
    local_project_id: str = Field(min_length=1, max_length=220)
    include_contexts: bool = True
    include_rooms: bool = True
    include_sources: bool = True
    include_entities: bool = True
    include_questions: bool = True
    include_lifecycles: bool = True
    visibility: Literal["private", "internal", "public"] = "internal"
