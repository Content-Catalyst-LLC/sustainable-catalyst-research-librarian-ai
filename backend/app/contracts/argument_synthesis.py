from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ARGUMENT_SYNTHESIS_SCHEMA = "sc-research-librarian-argument-contradiction-synthesis/1.0"
CORE_ARGUMENT_CONTRACT = "sc.research.argument-evidentiary-synthesis.v1"

ArgumentType = Literal["analytical", "explanatory", "comparative", "causal", "interpretive", "methodological"]
NodeType = Literal["evidence", "finding", "interpretation", "claim", "hypothesis", "assumption", "counterclaim", "limitation", "context", "method"]
NodeRole = Literal["premise", "support", "objection", "qualifier", "conclusion", "context", "gap"]
EdgeRelation = Literal["supports", "contradicts", "qualifies", "depends_on", "contextualizes", "responds_to", "derived_from", "is_relevant_to"]
SynthesisType = Literal["evidentiary", "narrative", "thematic", "comparative", "integrative"]


class ArgumentNodeInput(BaseModel):
    local_ref: str = Field(min_length=1, max_length=255)
    core_object_type: NodeType
    core_object_id: str | None = Field(default=None, max_length=255)
    statement_text: str | None = Field(default=None, max_length=20_000)
    role: NodeRole = "context"
    citation_refs: list[str] = Field(default_factory=list, max_length=100)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reference_or_statement_required(self):
        if not str(self.core_object_id or "").strip() and not str(self.statement_text or "").strip():
            raise ValueError("Argument nodes require core_object_id or statement_text.")
        return self


class DeclaredArgumentRelation(BaseModel):
    source_local_ref: str = Field(min_length=1, max_length=255)
    target_local_ref: str = Field(min_length=1, max_length=255)
    relation: EdgeRelation
    rationale: str | None = Field(default=None, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def no_self_reference(self):
        if self.source_local_ref == self.target_local_ref:
            raise ValueError("Declared argument relations cannot be self-referential.")
        return self


class DeclaredTension(BaseModel):
    tension_key: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10_000)
    source_refs: list[str] = Field(default_factory=list, max_length=100)
    status: Literal["open", "contextualized", "resolved_by_researcher", "external"] = "open"
    researcher_resolution_note: str | None = Field(default=None, max_length=10_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearcherAuthoredSynthesis(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    synthesis_text: str = Field(min_length=1, max_length=40_000)
    synthesis_type: SynthesisType = "evidentiary"
    limitations: list[str] = Field(default_factory=list, max_length=100)
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    component_local_refs: list[str] = Field(default_factory=list, max_length=200)


class ArgumentSynthesisPlanRequest(BaseModel):
    core_project_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    thesis_text: str | None = Field(default=None, max_length=20_000)
    central_claim_ref: str | None = Field(default=None, max_length=255)
    argument_type: ArgumentType = "analytical"
    nodes: list[ArgumentNodeInput] = Field(min_length=1, max_length=300)
    relations: list[DeclaredArgumentRelation] = Field(default_factory=list, max_length=500)
    tensions: list[DeclaredTension] = Field(default_factory=list, max_length=200)
    synthesis: ResearcherAuthoredSynthesis | None = None
    limitations: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def declared_refs_exist(self):
        refs = {n.local_ref for n in self.nodes}
        if len(refs) != len(self.nodes):
            raise ValueError("Argument node local_ref values must be unique.")
        for rel in self.relations:
            if rel.source_local_ref not in refs or rel.target_local_ref not in refs:
                raise ValueError("Declared argument relations must reference supplied nodes.")
        if self.synthesis:
            unknown = [x for x in self.synthesis.component_local_refs if x not in refs]
            if unknown:
                raise ValueError("Synthesis components must reference supplied nodes: " + unknown[0])
        return self


class ArgumentSynthesisPlan(BaseModel):
    plan_id: str
    core_project_id: str
    argument: dict[str, Any]
    nodes: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    tensions: list[dict[str, Any]]
    synthesis: dict[str, Any] | None = None
    review_decision: Literal["pending", "approved", "rejected"] = "pending"
    reviewer_ref: str | None = Field(default=None, max_length=255)
    reviewer_note: str | None = Field(default=None, max_length=5000)
    provenance: dict[str, Any] = Field(default_factory=dict)


class CoreArgumentSynthesisPromotionRequest(BaseModel):
    plan: ArgumentSynthesisPlan
    created_by: str = Field(default="research-librarian", min_length=1, max_length=255)

    @model_validator(mode="after")
    def explicit_review_required(self):
        if self.plan.review_decision != "approved":
            raise ValueError("Core argument promotion requires plan.review_decision='approved'.")
        if not str(self.plan.reviewer_ref or "").strip():
            raise ValueError("Core argument promotion requires plan.reviewer_ref.")
        return self
