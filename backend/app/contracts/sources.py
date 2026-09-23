from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class SourceResolveRequest(BaseModel):
    title: str = Field(default="", max_length=1000)
    authors: list[str] = Field(default_factory=list, max_length=200)
    institutions: list[str] = Field(default_factory=list, max_length=200)
    publication_year: int | None = Field(default=None, ge=1000, le=3000)
    identifiers: dict[str, Any] = Field(default_factory=dict)
    source_url: str = Field(default="", max_length=4000)
    filename: str = Field(default="", max_length=1000)
    media_type: str = Field(default="", max_length=300)
    content_fingerprint: str = Field(default="", max_length=256)
    version_label: str = Field(default="", max_length=300)
    references: list[dict[str, Any]] = Field(default_factory=list, max_length=2000)
    parsed_document: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    register_citations: bool = True


class CitationRegisterRequest(BaseModel):
    references: list[dict[str, Any]] = Field(default_factory=list, max_length=2000)
