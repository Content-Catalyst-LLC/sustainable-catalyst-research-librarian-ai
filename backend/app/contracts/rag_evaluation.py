from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

RAG_EVALUATION_SCHEMA = "sc-research-librarian-rag-evaluation/1.0"
RAG_EVALUATION_CASE_SCHEMA = "sc-research-librarian-rag-evaluation-case/1.0"
RAG_CLAIM_ASSESSMENT_SCHEMA = "sc-research-librarian-rag-claim-grounding-assessment/1.0"
RAG_CITATION_ASSESSMENT_SCHEMA = "sc-research-librarian-rag-citation-assessment/1.0"
RAG_EVALUATION_SNAPSHOT_SCHEMA = "sc-research-librarian-rag-evaluation-snapshot/1.0"

SupportStatus = Literal["supported", "partially-supported", "unsupported", "conflicting", "not-assessed"]
CitationStatus = Literal["correct", "partially-correct", "incorrect", "unverifiable", "not-assessed"]

class RAGEvaluationCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    context_id: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=500)
    evaluation_dataset_ref: str = Field(default="", max_length=2000)
    evaluation_dataset_version_ref: str = Field(default="", max_length=2000)
    rubric_ref: str = Field(default="", max_length=2000)
    benchmark_ref: str = Field(default="", max_length=2000)
    evaluator_ref: str = Field(default="", max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)

class RAGEvaluationCaseRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    query_ref: str = Field(default="", max_length=2000)
    query_text: str = Field(min_length=1, max_length=20000)
    retrieval_run_id: str = Field(default="", max_length=255)
    expected_evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    retrieved_evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    output_ref: str = Field(default="", max_length=2000)
    output_hash: str = Field(default="", max_length=255)
    latency_ms: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_amount: float | None = Field(default=None, ge=0)
    cost_currency: str = Field(default="", max_length=32)
    k: int = Field(default=10, ge=1, le=10000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_refs(self):
        for field_name in ("expected_evidence_refs", "retrieved_evidence_refs"):
            refs = getattr(self, field_name)
            if len(refs) != len(set(refs)):
                raise ValueError(f"{field_name} must contain unique references.")
        return self

class RAGClaimAssessmentRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    claim_ref: str = Field(min_length=1, max_length=2000)
    case_id: str = Field(default="", max_length=255)
    support_status: SupportStatus
    evidence_refs: list[str] = Field(default_factory=list, max_length=5000)
    citation_refs: list[str] = Field(default_factory=list, max_length=5000)
    rationale: str = Field(default="", max_length=20000)
    reviewer_ref: str = Field(default="", max_length=2000)

class RAGCitationAssessmentRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    citation_ref: str = Field(min_length=1, max_length=2000)
    case_id: str = Field(default="", max_length=255)
    evidence_ref: str = Field(default="", max_length=2000)
    status: CitationStatus
    rationale: str = Field(default="", max_length=20000)
    reviewer_ref: str = Field(default="", max_length=2000)

class RAGEvaluationComparisonRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    evaluation_ids: list[str] = Field(min_length=2, max_length=20)
    label: str = Field(default="comparison", max_length=500)

    @model_validator(mode="after")
    def unique_evaluations(self):
        if len(self.evaluation_ids) != len(set(self.evaluation_ids)):
            raise ValueError("evaluation_ids must be unique.")
        return self

class RAGEvaluationSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1, max_length=255)
    evaluation_id: str = Field(min_length=1, max_length=255)
    label: str = Field(default="rag-evaluation-snapshot", max_length=255)
    note: str = Field(default="", max_length=10000)
