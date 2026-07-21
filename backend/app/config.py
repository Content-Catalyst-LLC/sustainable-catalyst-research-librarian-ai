from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("SC_RL_ENVIRONMENT", "production")
    api_key: str = os.getenv("SC_RL_BACKEND_API_KEY", "")
    data_dir: Path = Path(os.getenv("SC_RL_DATA_DIR", "/tmp/sc-research-librarian"))
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("SC_RL_CORS_ORIGINS", "https://sustainablecatalyst.com").split(",")
        if origin.strip()
    )
    provider: str = os.getenv("SC_RL_AI_PROVIDER", "gemini").strip().lower()
    gemini_api_key: str = os.getenv("SC_RL_GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("SC_RL_GEMINI_MODEL", "gemini-3.5-flash")
    gemini_embedding_model: str = os.getenv("SC_RL_GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    request_timeout: int = _int("SC_RL_REQUEST_TIMEOUT", 35, 10, 120)
    max_output_tokens: int = _int("SC_RL_MAX_OUTPUT_TOKENS", 1300, 200, 6000)
    temperature: float = _float("SC_RL_TEMPERATURE", 0.2, 0.0, 1.0)
    source_limit: int = _int("SC_RL_SOURCE_LIMIT", 10, 3, 25)
    related_limit: int = _int("SC_RL_RELATED_LIMIT", 8, 3, 20)
    semantic_enabled: bool = _bool("SC_RL_SEMANTIC_ENABLED", False)
    semantic_document_limit: int = _int("SC_RL_SEMANTIC_DOCUMENT_LIMIT", 500, 25, 2500)
    semantic_query_embeddings: bool = _bool("SC_RL_SEMANTIC_QUERY_EMBEDDINGS", True)
    chunk_max_words: int = _int("SC_RL_CHUNK_MAX_WORDS", 220, 80, 500)
    chunk_overlap_words: int = _int("SC_RL_CHUNK_OVERLAP_WORDS", 35, 0, 120)
    embedding_batch_limit: int = _int("SC_RL_EMBEDDING_BATCH_LIMIT", 50, 1, 250)
    citation_required: bool = _bool("SC_RL_CITATION_REQUIRED", True)
    session_ttl_seconds: int = _int("SC_RL_SESSION_TTL_SECONDS", 3600, 300, 86400)
    max_session_turns: int = _int("SC_RL_MAX_SESSION_TURNS", 6, 1, 20)
    max_runtime_snapshots: int = _int("SC_RL_MAX_RUNTIME_SNAPSHOTS", 5, 1, 20)
    startup_warmup_seconds: int = _int("SC_RL_STARTUP_WARMUP_SECONDS", 12, 0, 120)
    stalled_job_seconds: int = _int("SC_RL_STALLED_JOB_SECONDS", 1800, 300, 86400)
    max_rejection_details: int = _int("SC_RL_MAX_REJECTION_DETAILS", 100, 10, 500)
    release_version: str = os.getenv("SC_RL_RELEASE_VERSION", "7.0.1")
    handoff_source_limit: int = _int("SC_RL_HANDOFF_SOURCE_LIMIT", 8, 1, 25)
    handoff_ttl_seconds: int = _int("SC_RL_HANDOFF_TTL_SECONDS", 1800, 300, 86400)
    handoff_retry_limit: int = _int("SC_RL_HANDOFF_RETRY_LIMIT", 5, 1, 20)
    handoff_retry_base_seconds: int = _int("SC_RL_HANDOFF_RETRY_BASE_SECONDS", 30, 5, 3600)
    handoff_event_ttl_seconds: int = _int("SC_RL_HANDOFF_EVENT_TTL_SECONDS", 86400, 300, 604800)
    handoff_max_artifact_bytes: int = _int("SC_RL_HANDOFF_MAX_ARTIFACT_BYTES", 1048576, 1024, 10485760)
    governance_trace_days: int = _int("SC_RL_GOVERNANCE_TRACE_DAYS", 30, 1, 3650)
    governance_evaluation_days: int = _int("SC_RL_GOVERNANCE_EVALUATION_DAYS", 365, 30, 3650)
    governance_event_days: int = _int("SC_RL_GOVERNANCE_EVENT_DAYS", 365, 30, 3650)
    workbench_enabled: bool = _bool("SC_RL_WORKBENCH_ENABLED", True)
    workbench_url: str = os.getenv("SC_RL_WORKBENCH_URL", "https://sustainablecatalyst.com/modeling-analytics/workbench/")
    workbench_version: str = os.getenv("SC_RL_WORKBENCH_VERSION", "unknown")
    decision_studio_enabled: bool = _bool("SC_RL_DECISION_STUDIO_ENABLED", True)
    decision_studio_url: str = os.getenv("SC_RL_DECISION_STUDIO_URL", "https://sustainablecatalyst.com/platform/decision-studio/")
    decision_studio_version: str = os.getenv("SC_RL_DECISION_STUDIO_VERSION", "unknown")
    site_intelligence_enabled: bool = _bool("SC_RL_SITE_INTELLIGENCE_ENABLED", True)
    site_intelligence_url: str = os.getenv("SC_RL_SITE_INTELLIGENCE_URL", "https://sustainablecatalyst.com/platform/site-intelligence/")
    site_intelligence_version: str = os.getenv("SC_RL_SITE_INTELLIGENCE_VERSION", "unknown")
    lab_enabled: bool = _bool("SC_RL_LAB_ENABLED", True)
    lab_url: str = os.getenv("SC_RL_LAB_URL", "https://sustainablecatalyst.com/lab/")
    lab_version: str = os.getenv("SC_RL_LAB_VERSION", "unknown")
    feature_suggestions_enabled: bool = _bool("SC_RL_FEATURE_SUGGESTIONS_ENABLED", True)
    feature_suggestions_url: str = os.getenv("SC_RL_FEATURE_SUGGESTIONS_URL", "https://sustainablecatalyst.com/platform/feature-suggestions/")
    feature_suggestions_version: str = os.getenv("SC_RL_FEATURE_SUGGESTIONS_VERSION", "unknown")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
