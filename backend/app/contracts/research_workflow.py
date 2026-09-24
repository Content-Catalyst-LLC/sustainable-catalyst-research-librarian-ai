from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field
from .unified_research_runtime import UnifiedResearchRuntimePlan, UnifiedResearchStagePayloads, StageName

RESEARCH_WORKFLOW_SCHEMA = "sc-research-librarian-research-workflow/1.0"
RESEARCH_WORKFLOW_EVENT_SCHEMA = "sc-research-librarian-research-workflow-event/1.0"
RESEARCH_WORKFLOW_CHECKPOINT_SCHEMA = "sc-research-librarian-research-workflow-checkpoint/1.0"

class ResearchWorkflowCreateRequest(BaseModel):
    plan: UnifiedResearchRuntimePlan
    payloads: UnifiedResearchStagePayloads = Field(default_factory=UnifiedResearchStagePayloads)
    auto_schedule_safe_stages: bool = True
    max_parallel_stages: int = Field(default=1, ge=1, le=8)
    max_attempts_per_stage: int = Field(default=3, ge=1, le=10)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchWorkflowControlRequest(BaseModel):
    action: Literal["start","pause","resume","cancel","retry-failed"]
    actor_ref: str = Field(min_length=1,max_length=255)
    reason: str = Field(default="",max_length=2000)

class ResearchWorkflowApprovalRequest(BaseModel):
    stage: StageName
    decision: Literal["approved","rejected"]
    reviewer_ref: str = Field(min_length=1,max_length=255)
    note: str = Field(default="",max_length=4000)

class ResearchWorkflowAdvanceRequest(BaseModel):
    actor_ref: str = Field(default="system",min_length=1,max_length=255)
    schedule_jobs: bool = True
    max_new_jobs: int = Field(default=1,ge=0,le=20)
