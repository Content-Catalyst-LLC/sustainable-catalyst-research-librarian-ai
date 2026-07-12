from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class KnowledgeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=220)
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=1600)
    slug: str = Field(default="", max_length=500)
    summary: str = Field(default="", max_length=8000)
    content: str = Field(default="", max_length=50000)
    headings: list[str] = Field(default_factory=list)
    post_type: str = Field(default="page", max_length=100)
    taxonomies: dict[str, list[str]] = Field(default_factory=dict)
    series: str = Field(default="", max_length=500)
    article_map: str = Field(default="", max_length=500)
    parent_title: str = Field(default="", max_length=500)
    modified_utc: str = Field(default="")
    source: str = Field(default="wordpress", max_length=100)
    route_id: str = Field(default="", max_length=180)
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None

    @field_validator("title", "summary", "content", "series", "article_map", "parent_title", mode="before")
    @classmethod
    def clean_text(cls, value: Any) -> str:
        return " ".join(str(value or "").split())


class SyncRequest(BaseModel):
    records: list[KnowledgeRecord]
    mode: str = Field(default="replace", pattern="^(replace|upsert)$")
    source_site: str = ""
    generated_utc: str = Field(default_factory=utc_now)


class SyncResponse(BaseModel):
    ok: bool = True
    mode: str
    received: int
    total_records: int
    indexed_titles: int
    last_sync_utc: str
    source_site: str = ""


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=3000)
    limit: int = Field(default=10, ge=1, le=25)


class RetrievedSource(BaseModel):
    id: str
    title: str
    url: str
    summary: str = ""
    post_type: str = ""
    slug: str = ""
    series: str = ""
    article_map: str = ""
    parent_title: str = ""
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    match_type: str = ""
    exact_title_match: bool = False
    source: str = "wordpress"
    route_id: str = ""


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=3000)
    session_id: str = Field(default="", max_length=180)
    page_url: str = Field(default="", max_length=1600)
    route_hint: dict[str, Any] = Field(default_factory=dict)
    wordpress_status: dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
    answer: str
    source: str
    ai_used: bool
    provider: str = ""
    model: str = ""
    session_id: str
    best_match: RetrievedSource | None = None
    matches: list[RetrievedSource] = Field(default_factory=list)
    related_titles: list[RetrievedSource] = Field(default_factory=list)
    research_path: list[dict[str, str]] = Field(default_factory=list)
    actions: list[dict[str, str]] = Field(default_factory=list)
    interpretation: str = ""
    clarification: str = ""
    confidence: dict[str, Any] = Field(default_factory=dict)
    status: dict[str, Any] = Field(default_factory=dict)
    generated_utc: str = Field(default_factory=utc_now)


class StatusResponse(BaseModel):
    version: str
    state: str
    label: str
    provider: str
    model: str
    ai_configured: bool
    index_ready: bool
    indexed_records: int
    indexed_titles: int
    semantic_retrieval: str
    last_sync_utc: str
    source_site: str
    last_ai_success_utc: str = ""
    last_ai_failure_utc: str = ""
    last_ai_error: str = ""
