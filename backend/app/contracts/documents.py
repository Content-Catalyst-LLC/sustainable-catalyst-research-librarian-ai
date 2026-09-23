from __future__ import annotations

import base64
from pydantic import BaseModel, Field, model_validator


class DocumentParseRequest(BaseModel):
    content: str = Field(default="", max_length=2_700_000)
    content_base64: str = Field(default="", max_length=30_000_000)
    media_type: str = Field(default="text/plain", max_length=200)
    filename: str = Field(default="", max_length=500)
    source_url: str = Field(default="", max_length=1600)
    title: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_payload(self) -> "DocumentParseRequest":
        if not self.content and not self.content_base64:
            raise ValueError("content or content_base64 is required")
        if self.content_base64:
            try:
                decoded = base64.b64decode(self.content_base64, validate=True)
            except Exception as exc:
                raise ValueError("content_base64 must be valid base64") from exc
            if len(decoded) > 20 * 1024 * 1024:
                raise ValueError("decoded document exceeds the 20 MiB parse limit")
        return self

    def decoded_bytes(self) -> bytes | None:
        return base64.b64decode(self.content_base64) if self.content_base64 else None
