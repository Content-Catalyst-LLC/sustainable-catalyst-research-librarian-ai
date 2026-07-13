from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class KnowledgeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1, max_length=220)
    title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=1, max_length=1600)
    slug: str = Field(default="", max_length=500)
    summary: str = Field(default="", max_length=8000)
    content: str = Field(default="", max_length=60000)
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
    content_hash: str = Field(default="", max_length=128)
    embedding: list[float] | None = None

    @field_validator("title", "summary", "content", "series", "article_map", "parent_title", mode="before")
    @classmethod
    def clean_text(cls, value: Any) -> str:
        return " ".join(str(value or "").split())


class SyncRequest(BaseModel):
    # Raw dictionaries are accepted deliberately. Each record is validated and
    # isolated inside the transactional store so one malformed record cannot
    # reject an otherwise valid synchronization batch.
    records: list[dict[str, Any]] = Field(default_factory=list)
    mode: str = Field(default="replace", pattern="^(replace|upsert|delete)$")
    source_site: str = ""
    generated_utc: str = Field(default_factory=utc_now)
    job_id: str = Field(default="", max_length=220)
    batch_index: int = Field(default=1, ge=1)
    batch_count: int = Field(default=1, ge=1)
    deleted_ids: list[str] = Field(default_factory=list)
    reason: str = Field(default="wordpress-sync", max_length=220)

    @model_validator(mode="after")
    def validate_batch_position(self) -> "SyncRequest":
        if self.batch_index > self.batch_count:
            raise ValueError("batch_index must not exceed batch_count")
        return self


class SyncResponse(BaseModel):
    ok: bool = True
    mode: str
    state: str = "completed"
    committed: bool = True
    received: int
    accepted: int = 0
    rejected: int = 0
    rejected_records: list[dict[str, Any]] = Field(default_factory=list)
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    deleted: int = 0
    staged_records: int = 0
    staged_deletions: int = 0
    duplicate_batch: bool = False
    job_id: str = ""
    batch_index: int = 1
    batch_count: int = 1
    total_records: int
    indexed_titles: int
    index_version: int = 0
    checksum: str = ""
    storage_engine: str = "sqlite"
    last_sync_utc: str
    source_site: str = ""


class RollbackRequest(BaseModel):
    snapshot_id: str = Field(min_length=1, max_length=220)


class MaintenanceRequest(BaseModel):
    max_age_seconds: int = Field(default=1800, ge=300, le=86400)
    purge_staging: bool = True


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
    storage_engine: str = "sqlite"
    schema_version: int = 4
    index_version: int = 0
    checksum: str = ""
    snapshot_count: int = 0
    staging_jobs: int = 0
    stalled_jobs: int = 0
    recovery_needed: bool = False
    last_recovery_utc: str = ""
    last_rollback_utc: str = ""
    last_ai_success_utc: str = ""
    last_ai_failure_utc: str = ""
    last_ai_error: str = ""
    startup_state: str = "ready"
    startup_phase: str = "ready"
    startup_progress: int = 100
    service_started_utc: str = ""
    uptime_seconds: int = 0
    ready: bool = True
