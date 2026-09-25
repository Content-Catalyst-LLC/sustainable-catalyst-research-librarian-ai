from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator

RESEARCH_KNOWLEDGE_GRAPH_SCHEMA = "sc-research-librarian-research-knowledge-graph/1.0"
RESEARCH_KNOWLEDGE_GRAPH_SNAPSHOT_SCHEMA = "sc-research-librarian-research-knowledge-graph-snapshot/1.0"
PUBLICATION_INTELLIGENCE_SCHEMA = "sc-research-librarian-publication-intelligence/1.0"

NodeKind = Literal[
    "publication","study","person","organization","dataset","source","evidence","finding","claim","argument",
    "review","replication","statistical-object","visual-object","research-object","method","software","other"
]
EdgeRelation = Literal[
    "cites","authored-by","contributed-by","derived-from","uses","supports","challenges","contradicts","extends",
    "replicates","reviews","evaluates","visualizes","analyzes","produces","references","affiliated-with","related-to"
]

class KnowledgeGraphNodeRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    node_ref: str = Field(min_length=1,max_length=2000)
    kind: NodeKind
    label: str = Field(min_length=1,max_length=2000)
    metadata: dict[str,Any] = Field(default_factory=dict)

class KnowledgeGraphEdgeRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    source_ref: str = Field(min_length=1,max_length=2000)
    target_ref: str = Field(min_length=1,max_length=2000)
    relation: EdgeRelation
    evidence_refs: list[str] = Field(default_factory=list,max_length=5000)
    source_basis: Literal["declared","citation","study-lineage","review-lineage","replication-lineage","core-lineage","other"] = "declared"
    note: str = Field(default="",max_length=10000)

    @model_validator(mode="after")
    def no_self_edge(self):
        if self.source_ref == self.target_ref:
            raise ValueError("Knowledge graph self-edges are not permitted.")
        return self

class KnowledgeGraphProposalRequest(KnowledgeGraphEdgeRequest):
    proposal_basis: str = Field(min_length=1,max_length=20000)
    confidence_note: str = Field(default="",max_length=10000)

class KnowledgeGraphProposalDecisionRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    decision: Literal["accept","reject"]
    rationale: str = Field(min_length=1,max_length=20000)

class PublicationGraphMaterializationRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    include_references: bool = True
    include_contributors: bool = True
    include_study_lineage: bool = True
    include_research_objects: bool = True
    include_visuals: bool = True

class KnowledgeGraphSnapshotRequest(BaseModel):
    actor_ref: str = Field(min_length=1,max_length=255)
    label: str = Field(default="research-knowledge-graph-snapshot",max_length=255)
    note: str = Field(default="",max_length=10000)
