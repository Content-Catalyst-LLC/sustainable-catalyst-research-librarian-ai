from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

SCHOLARLY_PUBLICATION_SCHEMA = "sc-research-librarian-scholarly-publication/1.0"
SCHOLARLY_PUBLICATION_PACKAGE_SCHEMA = "sc-research-librarian-scholarly-publication-package/1.0"
SCHOLARLY_DISSEMINATION_READINESS_SCHEMA = "sc-research-librarian-scholarly-dissemination-readiness/1.0"
KNOWLEDGE_LIBRARY_HANDOFF_SCHEMA = "sc-research-librarian-knowledge-library-publication-handoff/1.0"
CITATION_EXPORT_SCHEMA = "sc-research-librarian-citation-export/1.0"


class PublicationContributor(BaseModel):
    contributor_ref: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=500)
    role: Literal["author", "editor", "reviewer", "data-curator", "software", "visualization", "methodology", "other"] = "author"
    affiliation: str = Field(default="", max_length=1000)
    orcid: str = Field(default="", max_length=64)


class PublicationReference(BaseModel):
    reference_id: str = Field(default="", max_length=255)
    title: str = Field(min_length=1, max_length=2000)
    authors: list[str] = Field(default_factory=list, max_length=100)
    year: int | None = Field(default=None, ge=1000, le=3000)
    container_title: str = Field(default="", max_length=2000)
    doi: str = Field(default="", max_length=512)
    url: str = Field(default="", max_length=4000)
    source_ref: str = Field(default="", max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScholarlyPublicationCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    publication_type: Literal["article", "preprint", "report", "thesis", "chapter", "working-paper", "dataset-paper", "methods-paper", "other"] = "article"
    title: str = Field(min_length=1, max_length=1000)
    subtitle: str = Field(default="", max_length=1000)
    abstract: str = Field(min_length=1, max_length=50_000)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    contributors: list[PublicationContributor] = Field(default_factory=list, max_length=200)
    manuscript_artifact_ref: str = Field(default="", max_length=4000)
    scholarly_package_ref: str = Field(default="", max_length=2000)
    peer_review_package_ref: str = Field(default="", max_length=2000)
    references: list[PublicationReference] = Field(default_factory=list, max_length=10_000)
    source_refs: list[str] = Field(default_factory=list, max_length=5000)
    core_evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    core_research_object_refs: list[str] = Field(default_factory=list, max_length=5000)
    statistical_reasoning_refs: list[str] = Field(default_factory=list, max_length=1000)
    visual_refs: list[str] = Field(default_factory=list, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def at_least_one_author(self):
        if not any(c.role == "author" for c in self.contributors):
            raise ValueError("At least one human-declared author contributor is required.")
        return self


class PublicationVersionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    version_label: str = Field(default="revision", max_length=255)
    change_summary: str = Field(min_length=1, max_length=30_000)
    manuscript_artifact_ref: str = Field(default="", max_length=4000)
    title: str = Field(default="", max_length=1000)
    abstract: str = Field(default="", max_length=50_000)
    keywords: list[str] = Field(default_factory=list, max_length=100)
    visual_refs: list[str] = Field(default_factory=list, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PublicationIdentifierRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    identifier_type: Literal["doi", "isbn", "issn", "handle", "arxiv", "pmid", "local", "other"]
    value: str = Field(min_length=1, max_length=2000)
    registrar_or_authority: str = Field(default="", max_length=1000)
    resolver_url: str = Field(default="", max_length=4000)
    verification_note: str = Field(default="", max_length=10_000)


class PublicationStateTransitionRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    state: Literal["draft", "submitted", "accepted", "published", "withdrawn", "superseded"]
    rationale: str = Field(min_length=1, max_length=20_000)
    venue: str = Field(default="", max_length=2000)
    canonical_url: str = Field(default="", max_length=4000)
    decision_ref: str = Field(default="", max_length=2000)
    publication_date: str = Field(default="", max_length=64)


class PublicationHandoffRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    collection_ref: str = Field(default="knowledge-library:research-publications", max_length=1000)
    include_visualizations: bool = True
    include_citation_exports: bool = True
    note: str = Field(default="", max_length=10_000)


class PublicationPackageFreezeRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    package_label: str = Field(default="scholarly-publication-package", max_length=255)
    require_publication_ready: bool = True
    require_published_state: bool = False
    note: str = Field(default="", max_length=10_000)
