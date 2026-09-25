from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading, uuid
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.research_knowledge_graph import (
    RESEARCH_KNOWLEDGE_GRAPH_SCHEMA, RESEARCH_KNOWLEDGE_GRAPH_SNAPSHOT_SCHEMA, PUBLICATION_INTELLIGENCE_SCHEMA,
    KnowledgeGraphNodeRequest, KnowledgeGraphEdgeRequest, KnowledgeGraphProposalRequest,
    KnowledgeGraphProposalDecisionRequest, PublicationGraphMaterializationRequest, KnowledgeGraphSnapshotRequest,
)
from .scholarly_publication import get_scholarly_publication_store

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None; Jsonb=None

def _json(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v:Any)->str: return hashlib.sha256(_json(v).encode()).hexdigest()
def _now()->str: return datetime.now(timezone.utc).isoformat()
def _uid(prefix:str)->str: return f"{prefix}-{uuid.uuid4().hex}"

class ResearchKnowledgeGraphStore:
    def __init__(self, sqlite_path:Path|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"research_knowledge_graph.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres graph storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()

    @contextmanager
    def _postgres(self,migration:bool=False)->Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self)->None:
        with self._lock,self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS research_graph_nodes(node_ref TEXT PRIMARY KEY,kind TEXT NOT NULL,label TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_graph_edges(edge_id TEXT PRIMARY KEY,source_ref TEXT NOT NULL,target_ref TEXT NOT NULL,relation TEXT NOT NULL,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,UNIQUE(source_ref,target_ref,relation));
CREATE TABLE IF NOT EXISTS research_graph_proposals(proposal_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,status TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_graph_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_graph_snapshots(snapshot_id TEXT PRIMARY KEY,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_research_graph_nodes(node_ref TEXT PRIMARY KEY,kind TEXT NOT NULL,label TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_research_graph_edges(edge_id TEXT PRIMARY KEY,source_ref TEXT NOT NULL,target_ref TEXT NOT NULL,relation TEXT NOT NULL,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(source_ref,target_ref,relation))""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_research_graph_proposals(proposal_id TEXT PRIMARY KEY,record JSONB NOT NULL,status TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_research_graph_events(event_id BIGSERIAL PRIMARY KEY,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.execute("""CREATE TABLE IF NOT EXISTS sc_rl_research_graph_snapshots(snapshot_id TEXT PRIMARY KEY,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())""")
            c.commit()

    def _event(self,event_type:str,actor_ref:str,payload:dict[str,Any])->None:
        event_hash=_sha({"event_type":event_type,"actor_ref":actor_ref,"payload":payload})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_graph_events(event_type,actor_ref,payload,event_hash) VALUES(%s,%s,%s,%s)",(event_type,actor_ref,Jsonb(payload),event_hash)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO research_graph_events(event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?)",(event_type,actor_ref,_json(payload),event_hash,_now()))

    def upsert_node(self,req:KnowledgeGraphNodeRequest)->dict[str,Any]:
        rec={"schema":RESEARCH_KNOWLEDGE_GRAPH_SCHEMA,"node_ref":req.node_ref,"kind":req.kind,"label":req.label,"metadata":req.metadata,"updated_utc":_now(),"governance":{"identity_is_declared_or_existing":True}}
        rec["record_hash"]=_sha(rec)
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute("""INSERT INTO sc_rl_research_graph_nodes(node_ref,kind,label,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(node_ref) DO UPDATE SET kind=excluded.kind,label=excluded.label,record=excluded.record,record_hash=excluded.record_hash,updated_utc=excluded.updated_utc""",(req.node_ref,req.kind,req.label,Jsonb(rec),rec["record_hash"],rec["updated_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute("""INSERT INTO research_graph_nodes(node_ref,kind,label,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?,?,?) ON CONFLICT(node_ref) DO UPDATE SET kind=excluded.kind,label=excluded.label,record_json=excluded.record_json,record_hash=excluded.record_hash,updated_utc=excluded.updated_utc""",(req.node_ref,req.kind,req.label,_json(rec),rec["record_hash"],rec["updated_utc"],rec["updated_utc"]))
        self._event("node-upserted",req.actor_ref,{"node_ref":req.node_ref,"record_hash":rec["record_hash"]}); return rec

    def get_node(self,node_ref:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_research_graph_nodes WHERE node_ref=%s",(node_ref,)).fetchone(); c.commit()
            if not row: raise ValueError("Knowledge graph node not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM research_graph_nodes WHERE node_ref=?",(node_ref,)).fetchone()
        if not row: raise ValueError("Knowledge graph node not found.")
        return json.loads(row["record_json"])

    def add_edge(self,req:KnowledgeGraphEdgeRequest)->dict[str,Any]:
        self.get_node(req.source_ref); self.get_node(req.target_ref)
        edge={"schema":RESEARCH_KNOWLEDGE_GRAPH_SCHEMA,"edge_id":_uid("graph-edge"),"source_ref":req.source_ref,"target_ref":req.target_ref,"relation":req.relation,"evidence_refs":req.evidence_refs,"source_basis":req.source_basis,"note":req.note,"accepted_by":req.actor_ref,"created_utc":_now(),"governance":{"relation_is_explicit_not_machine_inferred":True}}
        edge["record_hash"]=_sha(edge)
        try:
            if self.backend=="postgres":
                with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_graph_edges(edge_id,source_ref,target_ref,relation,record,record_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s,%s)",(edge["edge_id"],req.source_ref,req.target_ref,req.relation,Jsonb(edge),edge["record_hash"],edge["created_utc"])); c.commit()
            else:
                with self._lock,self._sqlite() as c: c.execute("INSERT INTO research_graph_edges(edge_id,source_ref,target_ref,relation,record_json,record_hash,created_utc) VALUES(?,?,?,?,?,?,?)",(edge["edge_id"],req.source_ref,req.target_ref,req.relation,_json(edge),edge["record_hash"],edge["created_utc"]))
        except Exception:
            return next(e for e in self.neighborhood(req.source_ref,500)["edges"] if e["target_ref"]==req.target_ref and e["relation"]==req.relation)
        self._event("edge-accepted",req.actor_ref,{"edge_id":edge["edge_id"],"record_hash":edge["record_hash"]}); return edge

    def propose_edge(self,req:KnowledgeGraphProposalRequest)->dict[str,Any]:
        self.get_node(req.source_ref); self.get_node(req.target_ref)
        p={"schema":RESEARCH_KNOWLEDGE_GRAPH_SCHEMA,"proposal_id":_uid("graph-proposal"),"source_ref":req.source_ref,"target_ref":req.target_ref,"relation":req.relation,"evidence_refs":req.evidence_refs,"source_basis":req.source_basis,"note":req.note,"proposal_basis":req.proposal_basis,"confidence_note":req.confidence_note,"status":"pending-review","proposed_by":req.actor_ref,"created_utc":_now(),"updated_utc":_now(),"governance":{"proposal_is_not_graph_fact":True,"human_review_required":True}}
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_graph_proposals(proposal_id,record,status,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s)",(p["proposal_id"],Jsonb(p),p["status"],p["created_utc"],p["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO research_graph_proposals(proposal_id,record_json,status,created_utc,updated_utc) VALUES(?,?,?,?,?)",(p["proposal_id"],_json(p),p["status"],p["created_utc"],p["updated_utc"]))
        self._event("edge-proposed",req.actor_ref,{"proposal_id":p["proposal_id"]}); return p

    def _proposal(self,pid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_research_graph_proposals WHERE proposal_id=%s",(pid,)).fetchone(); c.commit()
            if not row: raise ValueError("Graph proposal not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM research_graph_proposals WHERE proposal_id=?",(pid,)).fetchone()
        if not row: raise ValueError("Graph proposal not found.")
        return json.loads(row["record_json"])

    def decide_proposal(self,pid:str,req:KnowledgeGraphProposalDecisionRequest)->dict[str,Any]:
        p=self._proposal(pid)
        if p["status"]!="pending-review": raise ValueError("Graph proposal has already been reviewed.")
        p.update({"status":"accepted" if req.decision=="accept" else "rejected","reviewed_by":req.actor_ref,"decision_rationale":req.rationale,"updated_utc":_now()})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("UPDATE sc_rl_research_graph_proposals SET record=%s,status=%s,updated_utc=%s WHERE proposal_id=%s",(Jsonb(p),p["status"],p["updated_utc"],pid)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("UPDATE research_graph_proposals SET record_json=?,status=?,updated_utc=? WHERE proposal_id=?",(_json(p),p["status"],p["updated_utc"],pid))
        if req.decision=="accept":
            self.add_edge(KnowledgeGraphEdgeRequest(actor_ref=req.actor_ref,source_ref=p["source_ref"],target_ref=p["target_ref"],relation=p["relation"],evidence_refs=p.get("evidence_refs",[]),source_basis=p.get("source_basis","declared"),note=p.get("note","")))
        self._event("proposal-reviewed",req.actor_ref,{"proposal_id":pid,"decision":req.decision}); return p

    def materialize_publication(self,publication_id:str,req:PublicationGraphMaterializationRequest)->dict[str,Any]:
        pub=get_scholarly_publication_store().get(publication_id)
        made_nodes=[]; made_edges=[]
        def node(ref,kind,label,metadata=None):
            made_nodes.append(self.upsert_node(KnowledgeGraphNodeRequest(actor_ref=req.actor_ref,node_ref=ref,kind=kind,label=label,metadata=metadata or {})))
        def edge(src,tgt,rel,basis="declared",evidence=None):
            made_edges.append(self.add_edge(KnowledgeGraphEdgeRequest(actor_ref=req.actor_ref,source_ref=src,target_ref=tgt,relation=rel,source_basis=basis,evidence_refs=evidence or [])))
        node(publication_id,"publication",pub["title"],{"study_id":pub["study_id"],"state":pub.get("state"),"canonical_url":pub.get("canonical_url","")})
        if req.include_study_lineage:
            node(pub["study_id"],"study",f"Study {pub['study_id']}"); edge(publication_id,pub["study_id"],"derived-from","study-lineage")
        if req.include_contributors:
            for c in pub.get("contributors",[]):
                cref=c.get("contributor_ref") or f"person:{_sha(c)[:16]}"; node(cref,"person",c.get("display_name") or cref,{"orcid":c.get("orcid","")}); edge(publication_id,cref,"authored-by" if c.get("role")=="author" else "contributed-by")
        if req.include_references:
            for idx,r in enumerate(pub.get("references",[])):
                rref=r.get("source_ref") or r.get("doi") or r.get("url") or f"reference:{publication_id}:{idx+1}"; node(rref,"source",r.get("title") or rref,{"doi":r.get("doi","")}); edge(publication_id,rref,"cites","citation",r.get("evidence_refs",[]))
        if req.include_research_objects:
            for ref in pub.get("core_evidence_refs",[]): node(ref,"evidence",ref); edge(publication_id,ref,"references","core-lineage")
            for ref in pub.get("core_research_object_refs",[]): node(ref,"research-object",ref); edge(publication_id,ref,"references","core-lineage")
            for ref in pub.get("statistical_reasoning_refs",[]): node(ref,"statistical-object",ref); edge(publication_id,ref,"analyzes","core-lineage")
        if req.include_visuals:
            for ref in pub.get("visual_refs",[]): node(ref,"visual-object",ref); edge(publication_id,ref,"visualizes","core-lineage")
        out={"schema":PUBLICATION_INTELLIGENCE_SCHEMA,"publication_id":publication_id,"node_count":len(made_nodes),"edge_count":len(made_edges),"node_refs":[n["node_ref"] for n in made_nodes],"edge_ids":[e["edge_id"] for e in made_edges],"governance":{"only_declared_and_existing_publication_lineage_materialized":True,"no_semantic_inference":True}}
        out["materialization_hash"]=_sha(out); self._event("publication-materialized",req.actor_ref,{"publication_id":publication_id,"materialization_hash":out["materialization_hash"]}); return out

    def neighborhood(self,node_ref:str,limit:int=200)->dict[str,Any]:
        node=self.get_node(node_ref); limit=max(1,min(limit,2000))
        if self.backend=="postgres":
            with self._postgres() as c: rows=c.execute("SELECT record FROM sc_rl_research_graph_edges WHERE source_ref=%s OR target_ref=%s ORDER BY created_utc DESC LIMIT %s",(node_ref,node_ref,limit)).fetchall(); c.commit()
            edges=[dict(r["record"]) for r in rows]
        else:
            with self._lock,self._sqlite() as c: rows=c.execute("SELECT record_json FROM research_graph_edges WHERE source_ref=? OR target_ref=? ORDER BY created_utc DESC LIMIT ?",(node_ref,node_ref,limit)).fetchall()
            edges=[json.loads(r["record_json"]) for r in rows]
        refs={node_ref}; [refs.update([e["source_ref"],e["target_ref"]]) for e in edges]
        nodes=[]
        for ref in refs:
            try:nodes.append(self.get_node(ref))
            except ValueError:pass
        return {"schema":PUBLICATION_INTELLIGENCE_SCHEMA,"focus":node,"nodes":nodes,"edges":edges,"governance":{"graph_contains_accepted_edges_only":True}}

    def publication_intelligence(self,publication_id:str)->dict[str,Any]:
        n=self.neighborhood(publication_id,1000)
        rels={}
        for e in n["edges"]: rels[e["relation"]]=rels.get(e["relation"],0)+1
        return {"schema":PUBLICATION_INTELLIGENCE_SCHEMA,"publication_id":publication_id,"node_count":len(n["nodes"]),"edge_count":len(n["edges"]),"relations":rels,"connected_node_kinds":sorted({x["kind"] for x in n["nodes"]}),"neighborhood":n,"governance":{"descriptive_not_evaluative":True,"no_impact_score":True,"no_truth_score":True,"no_inferred_authority":True}}

    def freeze_snapshot(self,req:KnowledgeGraphSnapshotRequest)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c:
                nodes=[dict(r["record"]) for r in c.execute("SELECT record FROM sc_rl_research_graph_nodes ORDER BY node_ref").fetchall()]; edges=[dict(r["record"]) for r in c.execute("SELECT record FROM sc_rl_research_graph_edges ORDER BY edge_id").fetchall()]; c.commit()
        else:
            with self._lock,self._sqlite() as c:
                nodes=[json.loads(r["record_json"]) for r in c.execute("SELECT record_json FROM research_graph_nodes ORDER BY node_ref").fetchall()]; edges=[json.loads(r["record_json"]) for r in c.execute("SELECT record_json FROM research_graph_edges ORDER BY edge_id").fetchall()]
        snap={"schema":RESEARCH_KNOWLEDGE_GRAPH_SNAPSHOT_SCHEMA,"snapshot_id":_uid("graph-snapshot"),"label":req.label,"note":req.note,"actor_ref":req.actor_ref,"nodes":nodes,"edges":edges,"created_utc":_now(),"governance":{"snapshot_contains_accepted_edges_only":True,"proposals_excluded":True}}
        snap["snapshot_hash"]=_sha(snap)
        if self.backend=="postgres":
            with self._postgres() as c:c.execute("INSERT INTO sc_rl_research_graph_snapshots(snapshot_id,snapshot_hash,record,created_utc) VALUES(%s,%s,%s,%s)",(snap["snapshot_id"],snap["snapshot_hash"],Jsonb(snap),snap["created_utc"]));c.commit()
        else:
            with self._lock,self._sqlite() as c:c.execute("INSERT INTO research_graph_snapshots(snapshot_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?)",(snap["snapshot_id"],snap["snapshot_hash"],_json(snap),snap["created_utc"]))
        self._event("graph-snapshot-frozen",req.actor_ref,{"snapshot_id":snap["snapshot_id"],"snapshot_hash":snap["snapshot_hash"]}); return snap

_graph_store:ResearchKnowledgeGraphStore|None=None
def get_research_knowledge_graph_store()->ResearchKnowledgeGraphStore:
    global _graph_store
    if _graph_store is None:_graph_store=ResearchKnowledgeGraphStore()
    return _graph_store

def capabilities()->dict[str,Any]:
    return {"schema":RESEARCH_KNOWLEDGE_GRAPH_SCHEMA,"release":settings.release_version,"durable_graph_registry":True,"publication_materialization":True,"accepted_edge_registry":True,"reviewable_edge_proposals":True,"publication_intelligence":True,"immutable_graph_snapshots":True,"automatic_semantic_inference":False,"automatic_edge_acceptance":False,"automatic_impact_ranking":False,"automatic_truth_scoring":False,"automatic_core_writes":False}
