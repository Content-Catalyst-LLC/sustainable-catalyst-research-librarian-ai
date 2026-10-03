from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

PERSISTENT_RESEARCH_SESSION_SCHEMA = "sc-research-librarian-persistent-research-session/1.0"
PERSISTENT_RESEARCH_TURN_SCHEMA = "sc-research-librarian-persistent-research-turn/1.0"
PERSISTENT_RESEARCH_SESSION_SNAPSHOT_SCHEMA = "sc-research-librarian-persistent-research-session-snapshot/1.0"

SessionState = Literal["active", "paused", "closed", "archived"]
TurnRole = Literal["user", "assistant", "system", "tool", "research-note"]

class ResearchSessionCreateRequest(BaseModel):
    title: str = Field(default="Research session", max_length=500)
    client_ref: str = Field(default="", max_length=255)
    project_id: str = Field(default="", max_length=255)
    scientist_environment_id: str = Field(default="", max_length=255)
    research_context_ref: str = Field(default="", max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchSessionTurnAddRequest(BaseModel):
    role: TurnRole
    content: str = Field(min_length=1, max_length=100000)
    source_refs: list[str] = Field(default_factory=list, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    artifact_refs: list[str] = Field(default_factory=list, max_length=5000)
    answer_trace_ref: str = Field(default="", max_length=2000)
    provider: str = Field(default="", max_length=255)
    model: str = Field(default="", max_length=255)
    provenance: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

class ResearchSessionContextBindRequest(BaseModel):
    project_id: str = Field(default="", max_length=255)
    scientist_environment_id: str = Field(default="", max_length=255)
    research_context_ref: str = Field(default="", max_length=2000)
    note: str = Field(default="", max_length=10000)

class ResearchSessionStateRequest(BaseModel):
    state: SessionState
    note: str = Field(default="", max_length=10000)

class ResearchSessionSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    label: str = Field(default="persistent-research-session-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
