from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

CROSS_LANGUAGE_RESOLUTION_SCHEMA = "sc-research-librarian-cross-language-entity-toponym-resolution/1.0"
CROSS_LANGUAGE_RESOLUTION_SNAPSHOT_SCHEMA = "sc-research-librarian-cross-language-entity-toponym-resolution-snapshot/1.0"
ENTITY_MENTION_SCHEMA = "sc-research-librarian-cross-language-entity-mention/1.0"
ENTITY_CANDIDATE_SCHEMA = "sc-research-librarian-cross-language-entity-candidate/1.0"
ENTITY_RESOLUTION_SCHEMA = "sc-research-librarian-cross-language-entity-resolution/1.0"
TOPONYM_MENTION_SCHEMA = "sc-research-librarian-cross-language-toponym-mention/1.0"
TOPONYM_CANDIDATE_SCHEMA = "sc-research-librarian-cross-language-toponym-candidate/1.0"
TOPONYM_RESOLUTION_SCHEMA = "sc-research-librarian-cross-language-toponym-resolution/1.0"
ALIAS_ALIGNMENT_SCHEMA = "sc-research-librarian-cross-language-alias-alignment/1.0"

ResolutionProjectState = Literal["draft", "active", "review", "closed", "archived"]
MentionKind = Literal["person", "organization", "institution", "event", "work", "concept", "other"]
AliasKind = Literal[
    "native", "alternate", "transliteration", "translation", "historical",
    "abbreviation", "acronym", "exonym", "endonym", "other"
]
ResolutionDecision = Literal["accepted", "rejected", "deferred", "needs-review"]
CandidateBasis = Literal[
    "source-identifier", "alias-match", "transliteration-match", "translation-match",
    "context-match", "temporal-match", "geographic-match", "graph-match", "model-suggestion", "other"
]


class CrossLanguageResolutionCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=1000)
    project_ref: str = Field(default="", max_length=2000)
    federation_ref: str = Field(default="", max_length=2000)
    multilingual_research_ref: str = Field(default="", max_length=2000)
    objective: str = Field(default="", max_length=30000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityMentionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    surface_form: str = Field(min_length=1, max_length=4000)
    original_script: str = Field(default="", max_length=4000)
    language_profile_ref: str = Field(min_length=1, max_length=2000)
    source_ref: str = Field(min_length=1, max_length=4000)
    source_locator: str = Field(default="", max_length=4000)
    mention_kind: MentionKind = "other"
    local_context: str = Field(default="", max_length=30000)
    temporal_context: str = Field(default="", max_length=4000)
    jurisdiction_context: str = Field(default="", max_length=4000)
    acquisition_ref: str = Field(default="", max_length=4000)
    transformation_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityCandidateAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    mention_id: str = Field(min_length=1, max_length=255)
    candidate_entity_ref: str = Field(min_length=1, max_length=4000)
    canonical_label: str = Field(default="", max_length=4000)
    native_labels: list[str] = Field(default_factory=list, max_length=1000)
    language_profile_refs: list[str] = Field(default_factory=list, max_length=1000)
    alias_refs: list[str] = Field(default_factory=list, max_length=5000)
    source_evidence_refs: list[str] = Field(default_factory=list, max_length=10000)
    basis: list[CandidateBasis] = Field(default_factory=list, max_length=100)
    descriptive_score: float = Field(default=0.0, ge=0.0, le=1.0)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntityResolutionDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    mention_id: str = Field(min_length=1, max_length=255)
    candidate_id: str = Field(min_length=1, max_length=255)
    decision: ResolutionDecision
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    human_reviewed: bool = False
    reviewer_ref: str = Field(default="", max_length=2000)
    rationale: str = Field(default="", max_length=30000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToponymMentionAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    surface_form: str = Field(min_length=1, max_length=4000)
    original_script: str = Field(default="", max_length=4000)
    language_profile_ref: str = Field(min_length=1, max_length=2000)
    source_ref: str = Field(min_length=1, max_length=4000)
    source_locator: str = Field(default="", max_length=4000)
    local_context: str = Field(default="", max_length=30000)
    temporal_context: str = Field(default="", max_length=4000)
    jurisdiction_context: str = Field(default="", max_length=4000)
    acquisition_ref: str = Field(default="", max_length=4000)
    transformation_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToponymCandidateAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    mention_id: str = Field(min_length=1, max_length=255)
    candidate_place_ref: str = Field(min_length=1, max_length=4000)
    canonical_label: str = Field(default="", max_length=4000)
    native_labels: list[str] = Field(default_factory=list, max_length=1000)
    jurisdiction: str = Field(default="", max_length=4000)
    historical_jurisdiction: str = Field(default="", max_length=4000)
    temporal_scope: str = Field(default="", max_length=4000)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    geospatial_ref: str = Field(default="", max_length=4000)
    alias_refs: list[str] = Field(default_factory=list, max_length=5000)
    source_evidence_refs: list[str] = Field(default_factory=list, max_length=10000)
    basis: list[CandidateBasis] = Field(default_factory=list, max_length=100)
    descriptive_score: float = Field(default=0.0, ge=0.0, le=1.0)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToponymResolutionDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    mention_id: str = Field(min_length=1, max_length=255)
    candidate_id: str = Field(min_length=1, max_length=255)
    decision: ResolutionDecision
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    human_reviewed: bool = False
    reviewer_ref: str = Field(default="", max_length=2000)
    rationale: str = Field(default="", max_length=30000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=10000)
    preserve_competing_candidates: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class AliasAlignmentAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    target_type: Literal["entity", "toponym"]
    target_ref: str = Field(min_length=1, max_length=4000)
    representation: str = Field(min_length=1, max_length=4000)
    alias_kind: AliasKind
    language_profile_ref: str = Field(default="", max_length=2000)
    script_ref: str = Field(default="", max_length=2000)
    source_ref: str = Field(default="", max_length=4000)
    transformation_refs: list[str] = Field(default_factory=list, max_length=5000)
    provenance_note: str = Field(default="", max_length=20000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossLanguageResolutionStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: ResolutionProjectState
    note: str = Field(default="", max_length=20000)


class CrossLanguageResolutionSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    resolution_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="cross-language-resolution-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
