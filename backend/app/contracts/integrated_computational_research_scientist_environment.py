from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

SCIENTIST_ENVIRONMENT_SCHEMA = "sc-research-librarian-integrated-computational-research-scientist-environment/1.0"
SCIENTIST_ENVIRONMENT_SNAPSHOT_SCHEMA = "sc-research-librarian-integrated-computational-research-scientist-environment-snapshot/1.0"

ScientistState = Literal["draft","active","computation","analysis","review","revision","complete","archived"]
StageType = Literal[
    "research-question","research-design","evidence-search","literature-review","evidence-synthesis",
    "data-readiness","computational-planning","statistical-analysis","causal-analysis","simulation-modeling",
    "reproduction-replication","cross-study-synthesis","integrity-audit","peer-review","revision-response",
    "publication-preparation","other",
]
WorkPackageType = Literal[
    "retrieval","data-preparation","analysis","statistics","causal","simulation","visualization",
    "replication","synthesis","verification","publication-support","other",
]
RuntimeTarget = Literal["workspace","research-lab","workbench","site-intelligence","external-specialist-runtime","other"]
ExecutionStatus = Literal["completed","partial","failed-to-run","cancelled"]
CheckpointStatus = Literal["open","approved","rejected","needs-revision","waived"]
Decision = Literal["pending","approved","rejected","waived"]

class ScientistEnvironmentCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    title: str = Field(min_length=1,max_length=1000)
    project_ref: str = Field(min_length=1,max_length=2000)
    unified_environment_ref: str = Field(min_length=1,max_length=255)
    research_question: str = Field(default="",max_length=20000)
    objective: str = Field(default="",max_length=20000)
    metadata: dict[str,Any] = Field(default_factory=dict)

class ScientistStageAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    stage_type: StageType
    label: str = Field(min_length=1,max_length=1000)
    source_refs: list[str] = Field(default_factory=list,max_length=5000)
    entry_criteria: list[str] = Field(default_factory=list,max_length=5000)
    exit_criteria: list[str] = Field(default_factory=list,max_length=5000)
    notes: str = Field(default="",max_length=20000)

class ScientistWorkPackageAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    stage_id: str = Field(min_length=1,max_length=255)
    work_package_type: WorkPackageType
    label: str = Field(min_length=1,max_length=1000)
    research_task: str = Field(min_length=1,max_length=30000)
    input_refs: list[str] = Field(default_factory=list,max_length=5000)
    expected_outputs: list[str] = Field(default_factory=list,max_length=5000)
    assumptions: list[str] = Field(default_factory=list,max_length=5000)
    limitations: list[str] = Field(default_factory=list,max_length=5000)

class ScientistRuntimeHandoffAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    work_package_id: str = Field(min_length=1,max_length=255)
    runtime_target: RuntimeTarget
    execution_spec: dict[str,Any] = Field(default_factory=dict)
    expected_artifacts: list[str] = Field(default_factory=list,max_length=5000)
    rationale: str = Field(default="",max_length=20000)

class ScientistExecutionReceiptAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    runtime_handoff_id: str = Field(min_length=1,max_length=255)
    execution_ref: str = Field(min_length=1,max_length=2000)
    status: ExecutionStatus
    runtime_version: str = Field(default="",max_length=255)
    environment_ref: str = Field(default="",max_length=2000)
    observed_summary: str = Field(default="",max_length=30000)
    metrics: dict[str,Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list,max_length=5000)
    provenance_note: str = Field(default="",max_length=10000)

class ScientistInterpretationAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    work_package_id: str = Field(min_length=1,max_length=255)
    execution_receipt_ids: list[str] = Field(default_factory=list,max_length=5000)
    interpretation: str = Field(min_length=1,max_length=50000)
    evidence_refs: list[str] = Field(default_factory=list,max_length=5000)
    uncertainties: list[str] = Field(default_factory=list,max_length=5000)
    limitations: list[str] = Field(default_factory=list,max_length=5000)

class ScientistCheckpointAddRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    stage_id: str = Field(min_length=1,max_length=255)
    label: str = Field(min_length=1,max_length=1000)
    review_question: str = Field(min_length=1,max_length=20000)
    evidence_refs: list[str] = Field(default_factory=list,max_length=5000)

class ScientistCheckpointDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    checkpoint_id: str = Field(min_length=1,max_length=255)
    status: CheckpointStatus
    rationale: str = Field(default="",max_length=30000)

class ScientistObjectDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    object_type: Literal["stage","work-package","runtime-handoff","interpretation","dossier"]
    object_id: str = Field(min_length=1,max_length=255)
    decision: Decision
    rationale: str = Field(default="",max_length=20000)

class ScientistEnvironmentStateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    state: ScientistState
    note: str = Field(default="",max_length=20000)

class ScientistEnvironmentSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    scientist_environment_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="integrated-computational-research-scientist-environment-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
