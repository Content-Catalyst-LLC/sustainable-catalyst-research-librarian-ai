from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

from .argument_synthesis import ArgumentSynthesisPlanRequest
from .research_intelligence_extraction import ResearchIntelligenceExtractionRequest
from .research_sync import CoreProjectSynchronizationPlanRequest
from .statistical_research import StatisticalAnalysisPlanRequest
from .visual_research import VisualResearchPlanRequest

UNIFIED_RESEARCH_RUNTIME_SCHEMA = "sc-research-librarian-unified-research-intelligence-runtime/1.0"
CORE_UNIFIED_RESEARCH_CONTRACT = "sc.research.unified-research-scientific-investigation-runtime.v1"

StageName = Literal[
    "discovery",
    "ingestion",
    "document-intelligence",
    "source-identity",
    "retrieval",
    "evidence-governance",
    "research-intelligence",
    "argument-synthesis",
    "statistical-analysis",
    "visual-research",
    "project-state",
    "reproducibility",
]

DEFAULT_STAGES: list[str] = [
    "discovery", "ingestion", "document-intelligence", "source-identity", "retrieval",
    "evidence-governance", "research-intelligence", "argument-synthesis",
    "statistical-analysis", "visual-research", "project-state", "reproducibility",
]


class UnifiedResearchRuntimePlanRequest(BaseModel):
    core_project_id: str = Field(min_length=1, max_length=255)
    core_session_id: str | None = Field(default=None, max_length=255)
    local_project_id: str | None = Field(default=None, max_length=220)
    title: str = Field(min_length=1, max_length=500)
    research_question: str = Field(min_length=1, max_length=10_000)
    objective: str | None = Field(default=None, max_length=10_000)
    requested_stages: list[StageName] = Field(default_factory=lambda: list(DEFAULT_STAGES), min_length=1, max_length=20)
    document_refs: list[str] = Field(default_factory=list, max_length=500)
    source_refs: list[str] = Field(default_factory=list, max_length=2000)
    core_evidence_refs: list[str] = Field(default_factory=list, max_length=2000)
    core_research_object_refs: list[str] = Field(default_factory=list, max_length=2000)
    statistical_reasoning_refs: list[str] = Field(default_factory=list, max_length=500)
    visual_refs: list[str] = Field(default_factory=list, max_length=500)
    source_content_hashes: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_stages(self):
        if len(set(self.requested_stages)) != len(self.requested_stages):
            raise ValueError("requested_stages must not contain duplicates")
        return self


class UnifiedResearchRuntimePlan(BaseModel):
    run_id: str
    core_project_id: str
    core_session_id: str | None = None
    local_project_id: str | None = None
    title: str
    research_question: str
    objective: str | None = None
    stages: list[dict[str, Any]]
    stage_order: list[StageName]
    inputs: dict[str, Any]
    gates: list[dict[str, Any]]
    endpoint_map: dict[str, str]
    reproducibility: dict[str, Any]
    governance: dict[str, Any]


class UnifiedResearchStagePayloads(BaseModel):
    research_intelligence: ResearchIntelligenceExtractionRequest | None = None
    argument_synthesis: ArgumentSynthesisPlanRequest | None = None
    statistical_analysis: StatisticalAnalysisPlanRequest | None = None
    visual_research: VisualResearchPlanRequest | None = None
    project_sync: CoreProjectSynchronizationPlanRequest | None = None


class UnifiedResearchRuntimeExecutionRequest(BaseModel):
    plan: UnifiedResearchRuntimePlan
    payloads: UnifiedResearchStagePayloads = Field(default_factory=UnifiedResearchStagePayloads)
    execute_stages: list[StageName] = Field(
        default_factory=lambda: ["retrieval", "research-intelligence", "argument-synthesis", "statistical-analysis", "visual-research", "project-state"],
        max_length=20,
    )
    strict_project_identity: bool = True

    @model_validator(mode="after")
    def project_identity_matches(self):
        if not self.strict_project_identity:
            return self
        expected = self.plan.core_project_id
        for payload in [
            self.payloads.research_intelligence,
            self.payloads.argument_synthesis,
            self.payloads.statistical_analysis,
            self.payloads.visual_research,
        ]:
            if payload is not None and payload.core_project_id != expected:
                raise ValueError("All unified runtime stage payloads must target plan.core_project_id.")
        if self.payloads.project_sync is not None and self.plan.local_project_id:
            if self.payloads.project_sync.local_project_id != self.plan.local_project_id:
                raise ValueError("project_sync.local_project_id must match plan.local_project_id.")
        return self
