from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

AI_RESEARCH_CONTEXT_SCHEMA = "sc-research-librarian-ai-research-context/1.0"
AI_RETRIEVAL_RUN_SCHEMA = "sc-research-librarian-ai-retrieval-run/1.0"
AI_CONTEXT_SNAPSHOT_SCHEMA = "sc-research-librarian-ai-context-snapshot/1.0"

class AIResearchContextCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    research_question: str = Field(min_length=1,max_length=20000)
    project_ref: str = Field(default="",max_length=2000)
    corpus_ref: str = Field(min_length=1,max_length=2000)
    corpus_version_ref: str = Field(default="",max_length=2000)
    dataset_ref: str = Field(default="",max_length=2000)
    chunking_strategy_ref: str = Field(min_length=1,max_length=2000)
    embedding_model_ref: str = Field(min_length=1,max_length=2000)
    retriever_ref: str = Field(min_length=1,max_length=2000)
    reranker_ref: str = Field(default="",max_length=2000)
    prompt_ref: str = Field(min_length=1,max_length=2000)
    prompt_version_ref: str = Field(min_length=1,max_length=2000)
    model_ref: str = Field(min_length=1,max_length=2000)
    model_version_ref: str = Field(min_length=1,max_length=2000)
    generation_parameters: dict[str,Any] = Field(default_factory=dict)
    metadata: dict[str,Any] = Field(default_factory=dict)

class RetrievedEvidenceItem(BaseModel):
    evidence_ref: str = Field(min_length=1,max_length=2000)
    source_ref: str = Field(default="",max_length=2000)
    chunk_ref: str = Field(default="",max_length=2000)
    rank: int = Field(ge=1,le=100000)
    score: float|None = None
    score_kind: str = Field(default="",max_length=255)
    content_hash: str = Field(default="",max_length=255)
    citation_ref: str = Field(default="",max_length=2000)

class AIRetrievalRunCreateRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    context_id: str = Field(min_length=1,max_length=255)
    query_text: str = Field(min_length=1,max_length=20000)
    retrieval_parameters: dict[str,Any] = Field(default_factory=dict)
    evidence: list[RetrievedEvidenceItem] = Field(default_factory=list,max_length=5000)
    inference_run_ref: str = Field(default="",max_length=2000)
    output_ref: str = Field(default="",max_length=2000)
    output_hash: str = Field(default="",max_length=255)
    notes: str = Field(default="",max_length=20000)

    @model_validator(mode="after")
    def unique_evidence(self):
        refs=[x.evidence_ref for x in self.evidence]
        if len(refs)!=len(set(refs)):
            raise ValueError("Retrieved evidence references must be unique within a run.")
        return self

class AIContextSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    context_id: str = Field(min_length=1,max_length=255)
    label: str = Field(default="ai-research-context-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
