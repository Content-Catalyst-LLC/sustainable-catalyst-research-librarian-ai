from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

WORDPRESS_STATE_MIGRATION_SCHEMA = "sc-research-librarian-wordpress-state-migration/1.0"
WORDPRESS_MIGRATION_CANDIDATE_SCHEMA = "sc-research-librarian-wordpress-migration-candidate/1.0"
WORDPRESS_MIGRATION_RECEIPT_SCHEMA = "sc-research-librarian-wordpress-migration-receipt/1.0"
WORDPRESS_COMPATIBILITY_ALIAS_SCHEMA = "sc-research-librarian-wordpress-compatibility-alias/1.0"

MigrationSourceType = Literal[
    "project",
    "research-context",
    "research-room",
    "library-object",
    "persistent-session",
    "persistent-turn",
    "compatibility-record",
]

class WordPressMigrationCandidateInput(BaseModel):
    source_type: MigrationSourceType
    legacy_id: str = Field(min_length=1, max_length=500)
    owner_key: str = Field(default="", max_length=500)
    parent_legacy_id: str = Field(default="", max_length=500)
    source_locator: str = Field(default="", max_length=2000)
    payload: dict[str, Any] = Field(default_factory=dict)

class WordPressMigrationPrepareRequest(BaseModel):
    source_site: str = Field(min_length=1, max_length=1000)
    source_instance: str = Field(default="", max_length=500)
    actor_ref: str = Field(default="", max_length=255)
    owner_map: dict[str, str] = Field(default_factory=dict)
    inventory_hash: str = Field(default="", max_length=128)
    candidates: list[WordPressMigrationCandidateInput] = Field(default_factory=list, max_length=5000)
    note: str = Field(default="", max_length=10000)

class WordPressMigrationApplyRequest(BaseModel):
    confirm: bool = False
    candidate_ids: list[str] = Field(default_factory=list, max_length=5000)
    note: str = Field(default="", max_length=10000)

class WordPressCompatibilityResolveRequest(BaseModel):
    source_site: str = Field(min_length=1, max_length=1000)
    source_type: MigrationSourceType
    legacy_id: str = Field(min_length=1, max_length=500)
