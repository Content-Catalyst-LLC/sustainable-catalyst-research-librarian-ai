from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

VISUAL_RESEARCH_SCHEMA = "sc-research-librarian-visual-research-intelligence/1.0"
CORE_VISUAL_OBJECT_CONTRACT = "sc.visual-reasoning.object.v1"
CORE_SCENE_CONTRACT = "sc.visual-runtime.scene.v1"
CORE_UNIFIED_VISUAL_CONTRACT = "sc.visual-runtime.unified-reasoning.v1"
CORE_CROSS_PRODUCT_VISUAL_CONTRACT = "sc.visual-runtime.cross-product-integration.v1"

ReviewDecision = Literal["pending", "approved", "rejected"]
VisualKind = Literal[
    "citation-network",
    "evidence-map",
    "claim-map",
    "finding-map",
    "contradiction-map",
    "argument-graph",
    "statistical-result-view",
    "uncertainty-view",
    "provenance-graph",
    "research-timeline",
    "source-lineage",
    "concept-map",
    "generic",
]
EntityType = Literal[
    "publication", "source", "citation", "evidence", "claim", "finding", "argument",
    "statistical-reasoning", "project-state", "research-object", "other"
]
RelationType = Literal[
    "cites", "supports", "contradicts", "qualifies", "contextualizes", "derived-from",
    "contains", "precedes", "associated-with", "same-source", "version-of"
]


class VisualEntityRef(BaseModel):
    local_ref: str = Field(min_length=1, max_length=255)
    entity_type: EntityType
    core_object_id: str | None = Field(default=None, max_length=255)
    label: str = Field(min_length=1, max_length=1000)
    role: str = Field(default="context", max_length=128)
    evidence_refs: list[str] = Field(default_factory=list, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeclaredVisualRelation(BaseModel):
    relation_ref: str = Field(min_length=1, max_length=255)
    source_local_ref: str = Field(min_length=1, max_length=255)
    target_local_ref: str = Field(min_length=1, max_length=255)
    relation: RelationType
    rationale: str | None = Field(default=None, max_length=5000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VisualResearchViewSpec(BaseModel):
    view_ref: str = Field(min_length=1, max_length=255)
    kind: VisualKind
    title: str = Field(min_length=1, max_length=1000)
    entity_refs: list[str] = Field(default_factory=list, max_length=1000)
    relation_refs: list[str] = Field(default_factory=list, max_length=1000)
    encodings: dict[str, Any] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)
    linked_view_refs: list[str] = Field(default_factory=list, max_length=100)
    layout_hint: str | None = Field(default=None, max_length=128)
    annotations: list[dict[str, Any]] = Field(default_factory=list, max_length=200)


class VisualResearchPlanRequest(BaseModel):
    core_project_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    research_question: str | None = Field(default=None, max_length=10000)
    visual_kind: VisualKind = "evidence-map"
    core_session_id: str | None = Field(default=None, max_length=255)
    entities: list[VisualEntityRef] = Field(min_length=1, max_length=2000)
    relations: list[DeclaredVisualRelation] = Field(default_factory=list, max_length=5000)
    views: list[VisualResearchViewSpec] = Field(default_factory=list, max_length=100)
    source_content_hashes: dict[str, str] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_refs(self):
        entity_refs = {x.local_ref for x in self.entities}
        relation_refs = {x.relation_ref for x in self.relations}
        for rel in self.relations:
            if rel.source_local_ref not in entity_refs or rel.target_local_ref not in entity_refs:
                raise ValueError("Visual relations must reference supplied entities.")
        for view in self.views:
            missing_entities = set(view.entity_refs) - entity_refs
            missing_relations = set(view.relation_refs) - relation_refs
            if missing_entities:
                raise ValueError(f"View {view.view_ref!r} references missing entities: {sorted(missing_entities)}")
            if missing_relations:
                raise ValueError(f"View {view.view_ref!r} references missing relations: {sorted(missing_relations)}")
        return self


class VisualResearchPlan(BaseModel):
    plan_id: str
    core_project_id: str
    core_session_id: str | None = None
    title: str
    research_question: str | None = None
    visual_kind: VisualKind
    entities: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    views: list[dict[str, Any]]
    source_content_hashes: dict[str, str]
    limitations: list[str]
    renderer_policy: dict[str, Any]
    review_decision: ReviewDecision = "pending"
    reviewer_ref: str | None = Field(default=None, max_length=255)
    reviewer_note: str | None = Field(default=None, max_length=5000)
    provenance: dict[str, Any] = Field(default_factory=dict)


class CoreVisualResearchPromotionRequest(BaseModel):
    plan: VisualResearchPlan
    visibility: str = Field(default="private", max_length=64)
    create_snapshot: bool = True
    bind_to_core_session: bool = True

    @model_validator(mode="after")
    def approved(self):
        if self.plan.review_decision != "approved":
            raise ValueError("Core visual research promotion requires plan.review_decision='approved'.")
        if not str(self.plan.reviewer_ref or "").strip():
            raise ValueError("Core visual research promotion requires plan.reviewer_ref.")
        if self.bind_to_core_session and not str(self.plan.core_session_id or "").strip():
            raise ValueError("Core visual session binding requires plan.core_session_id when bind_to_core_session=true.")
        return self
