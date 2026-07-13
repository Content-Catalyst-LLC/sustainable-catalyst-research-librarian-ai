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


class RetrievalCalibrationUpdate(BaseModel):
    profile: str = Field(default="balanced-v6.4.1", max_length=100)
    weights: dict[str, float] = Field(default_factory=dict)
    rrf_k: int = Field(default=60, ge=1, le=500)
    thresholds: dict[str, float | int] = Field(default_factory=dict)
    limits: dict[str, int] = Field(default_factory=dict)
    post_type_weights: dict[str, float] = Field(default_factory=dict)
    source_weights: dict[str, float] = Field(default_factory=dict)
    exclusions: dict[str, list[str]] = Field(default_factory=dict)


class BenchmarkCase(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    expected_record_id: str = Field(default="", max_length=220)
    expected_title: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list)


class BenchmarkRequest(BaseModel):
    cases: list[BenchmarkCase] = Field(default_factory=list, max_length=100)
    include_semantic: bool = True
    limit: int = Field(default=5, ge=1, le=25)
    persist: bool = True


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=2, max_length=3000)
    limit: int = Field(default=10, ge=1, le=25)
    include_diagnostics: bool = False


class EmbeddingProcessRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    delay_ms: int = Field(default=150, ge=0, le=5000)


class KnowledgeChunk(BaseModel):
    chunk_id: str
    record_id: str
    heading: str = ""
    page: int | None = None
    passage: str = ""
    position: int = 0
    content_hash: str = ""
    embedding_model: str = ""
    embedding: list[float] | None = None


class EvidenceCitation(BaseModel):
    id: str
    record_id: str
    chunk_id: str = ""
    title: str
    url: str
    section: str = ""
    page: int | None = None
    passage: str = ""
    source_type: str = ""
    record_version: str = ""
    reason: str = ""


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
    evidence_id: str = ""
    chunk_id: str = ""
    section: str = ""
    page: int | None = None
    passage: str = ""
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    fusion_score: float = 0.0
    retrieval_reasons: list[str] = Field(default_factory=list)
    citation_label: str = ""


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
    evidence: list[EvidenceCitation] = Field(default_factory=list)
    citation_verification: dict[str, Any] = Field(default_factory=dict)
    retrieval_diagnostics: dict[str, Any] = Field(default_factory=dict)
    evidence_gate: dict[str, Any] = Field(default_factory=dict)
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
    schema_version: int = 6
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
    indexed_chunks: int = 0
    embedded_chunks: int = 0
    semantic_coverage: float = 0.0
    embedding_model: str = ""
    retrieval_profile: str = "balanced-v6.4.1"
    benchmark_runs: int = 0
