from __future__ import annotations

from pydantic import BaseModel, Field

INDEPENDENT_DEPLOYMENT_CERTIFICATION_SCHEMA = "sc-research-librarian-independent-deployment-certification/1.0"
INDEPENDENT_DEPLOYMENT_REPORT_SCHEMA = "sc-research-librarian-independent-deployment-report/1.0"

class IndependentDeploymentCertificationRequest(BaseModel):
    note: str = Field(default="", max_length=10000)
    expected_database_backend: str = Field(default="", max_length=40)
    require_identity_runtime: bool = True
    require_web_app: bool = True
    require_migration_continuity: bool = True
