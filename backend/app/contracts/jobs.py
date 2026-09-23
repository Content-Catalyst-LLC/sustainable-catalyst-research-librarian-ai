from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator

from ..async_jobs import JOB_TYPES


class JobCreateRequest(BaseModel):
    job_type: str = Field(default="document-process", min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0, le=1000)
    max_attempts: int = Field(default=3, ge=1, le=20)
    idempotency_key: str = Field(default="", max_length=220)

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, value: str) -> str:
        clean = value.strip().lower()
        if clean not in JOB_TYPES:
            raise ValueError(f"job_type must be one of: {', '.join(sorted(JOB_TYPES))}")
        return clean


class DocumentJobRequest(BaseModel):
    document: dict[str, Any]
    source_site: str = Field(default="async-python-runtime", max_length=500)
    embed: bool = False
    priority: int = Field(default=100, ge=0, le=1000)
    max_attempts: int = Field(default=3, ge=1, le=20)
    idempotency_key: str = Field(default="", max_length=220)
