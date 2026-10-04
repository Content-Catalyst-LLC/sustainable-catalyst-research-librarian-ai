from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

THIN_WORDPRESS_ADAPTER_SCHEMA = "sc-research-librarian-wordpress-thin-adapter/2.0"
THIN_WORDPRESS_ADAPTER_CONTEXT_SCHEMA = "sc-research-librarian-wordpress-actor-context/1.0"

READ_OPERATIONS = (
    "status",
    "capabilities",
    "projects",
    "project",
    "project-investigations",
    "sessions",
    "session",
    "session-turns",
    "session-summary",
    "retrieve",
)

WRITE_OPERATIONS = (
    "project-create",
    "session-create",
    "session-turn-add",
    "session-snapshot-freeze",
)

ALL_OPERATIONS = READ_OPERATIONS + WRITE_OPERATIONS

class WordPressActorContext(BaseModel):
    schema: str = THIN_WORDPRESS_ADAPTER_CONTEXT_SCHEMA
    source: str = "wordpress"
    site_url: str = Field(default="", max_length=1000)
    wp_user_id: int = Field(default=0, ge=0)
    display_name: str = Field(default="", max_length=160)
    roles: list[str] = Field(default_factory=list, max_length=32)

class ThinWordPressAdapterEnvelope(BaseModel):
    schema: str = THIN_WORDPRESS_ADAPTER_SCHEMA
    operation: str = Field(pattern="^(status|capabilities|projects|project|project-investigations|sessions|session|session-turns|session-summary|retrieve|project-create|session-create|session-turn-add|session-snapshot-freeze)$")
    actor: WordPressActorContext
    payload: dict[str, Any] = Field(default_factory=dict)
