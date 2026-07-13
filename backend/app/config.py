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
    session_ttl_seconds: int = _int("SC_RL_SESSION_TTL_SECONDS", 3600, 300, 86400)
    max_session_turns: int = _int("SC_RL_MAX_SESSION_TURNS", 6, 1, 20)
    max_runtime_snapshots: int = _int("SC_RL_MAX_RUNTIME_SNAPSHOTS", 5, 1, 20)


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
