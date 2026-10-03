from __future__ import annotations
from pydantic import BaseModel, Field

INDEPENDENT_WEB_APP_SCHEMA = "sc-research-librarian-independent-web-app/1.0"
INDEPENDENT_WEB_APP_RUNTIME_SCHEMA = "sc-research-librarian-independent-web-app-runtime/1.0"

class WebAppClientCapability(BaseModel):
    capability: str = Field(min_length=1, max_length=120)
    enabled: bool
    note: str = Field(default="", max_length=1000)
