from __future__ import annotations

from pydantic import BaseModel, Field

IDENTITY_SCHEMA = "sc-research-librarian-identity/1.0"
AUTH_SESSION_SCHEMA = "sc-research-librarian-auth-session/1.0"
ACCESS_CONTEXT_SCHEMA = "sc-research-librarian-access-context/1.0"

IDENTITY_ROLES = ("owner", "editor", "researcher", "viewer")

class IdentityProvisionRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=1024)
    role: str = Field(default="researcher", pattern="^(owner|editor|researcher|viewer)$")

class IdentityLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)
    client_mode: str = Field(default="cookie", pattern="^(cookie|bearer)$")
    client_label: str = Field(default="independent-web-app", max_length=160)

class IdentityRoleUpdateRequest(BaseModel):
    role: str = Field(pattern="^(owner|editor|researcher|viewer)$")

class IdentityStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(active|disabled)$")

class IdentityPasswordUpdateRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)

class IdentitySessionRevokeRequest(BaseModel):
    reason: str = Field(default="user-request", max_length=240)
