from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.scholarly_literature_intelligence import (
    SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA, SCHOLARLY_LITERATURE_INTELLIGENCE_SNAPSHOT_SCHEMA,
    LiteratureIntelligenceCreateRequest, LiteratureWorkAddRequest, CitationContextAddRequest,
    LiteratureStrandAddRequest, LiteratureGapAddRequest, SeminalCandidateAddRequest,
    RelatedWorkCandidateAddRequest, RelatedWorkDecisionRequest, LiteratureIntelligenceStateRequest,
    LiteratureIntelligenceSnapshotRequest,
)
from .systematic_review_evidence_synthesis import get_systematic_review_evidence_synthesis_store
from .research_knowledge_graph import get_research_knowledge_graph_store

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover
    psycopg=None; dict_row=None; Jsonb=None

def _json(v:Any)->str: return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v:Any)->str: return hashlib.sha256(_json(v).encode()).hexdigest()
def _now()->str: return datetime.now(timezone.utc).isoformat()
def _uniq(values:list[str])->list[str]: return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))
def _id(prefix:str,payload:Any)->str: return prefix+_sha(payload)[:32]

class ScholarlyLiteratureIntelligenceStore:
    def __init__(self, sqlite_path:Path|None=None, systematic_review_store:Any|None=None, graph_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"scholarly_literature_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self.systematic_review_store=systematic_review_store; self.graph_store=graph_store
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres scholarly-literature storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _reviews(self): return self.systematic_review_store or get_systematic_review_evidence_synthesis_store()
    def _graph(self): return self.graph_store or get_research_knowledge_graph_store()
    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()
    @contextmanager
    def _postgres(self,migration:bool=False)->Iterator[Any]:
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()
    def _migrate_sqlite(self)->None:
        with self._lock,self._sqlite() as c: c.executescript("""
CREATE TABLE IF NOT EXISTS scholarly_literature_intelligence(intelligence_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scholarly_literature_intelligence_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,intelligence_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scholarly_literature_intelligence_snapshots(snapshot_id TEXT PRIMARY KEY,intelligence_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_scholarly_literature_intelligence(intelligence_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_scholarly_literature_intelligence_events(event_id BIGSERIAL PRIMARY KEY,intelligence_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_literature_events_intelligence ON sc_rl_scholarly_literature_intelligence_events(intelligence_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_scholarly_literature_intelligence_snapshots(snapshot_id TEXT PRIMARY KEY,intelligence_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,iid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"intelligence_id":iid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_literature_intelligence_events(intelligence_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(iid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO scholarly_literature_intelligence_events(intelligence_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(iid,typ,actor,_json(payload),h,created))
    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_literature_intelligence(intelligence_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(intelligence_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["intelligence_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO scholarly_literature_intelligence(intelligence_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["intelligence_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,iid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_scholarly_literature_intelligence WHERE intelligence_id=%s",(iid,)).fetchone()
            if not row: raise ValueError("Literature intelligence project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM scholarly_literature_intelligence WHERE intelligence_id=?",(iid,)).fetchone()
        if not row: raise ValueError("Literature intelligence project not found.")
        return json.loads(row["record_json"])
    def create(self,req:LiteratureIntelligenceCreateRequest)->dict[str,Any]:
        body=req.model_dump(); actor=body.pop("actor_ref"); review={}
        if body.get("systematic_review_id"):
            review=self._reviews().get(body["systematic_review_id"])
            body["question_plan_id"]=body.get("question_plan_id") or review.get("question_plan_id","")
            body["research_design_plan_id"]=body.get("research_design_plan_id") or review.get("research_design_plan_id","")
            body["evidence_search_strategy_id"]=body.get("evidence_search_strategy_id") or review.get("evidence_search_strategy_id","")
            body["research_question"]=body.get("research_question") or review.get("review_question","")
            included=[]
            decisions=review.get("screening_decisions") or []
            final={d.get("candidate_id"):d for d in decisions if d.get("stage")=="full-text"}
            for c in review.get("candidates") or []:
                if (final.get(c.get("candidate_id")) or {}).get("decision")=="include": included.append(c.get("source_ref", ""))
            body["seed_source_refs"]=_uniq((body.get("seed_source_refs") or [])+included)
        else: body["seed_source_refs"]=_uniq(body.get("seed_source_refs") or [])
        seed={k:v for k,v in body.items() if k!="metadata"}; iid=_id("litintel-",seed)
        try: return self.get(iid)
        except ValueError: pass
        rec={"schema":SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA,"intelligence_id":iid,**body,
             "systematic_review_fingerprint":review.get("record_hash","") if review else "",
             "works":[],"citation_contexts":[],"literature_strands":[],"gaps":[],"seminal_candidates":[],"related_work_candidates":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),
             "governance":{"citation_contexts_are_annotations_not_truth_claims":True,"human_gap_declaration_required":True,"human_seminal_candidate_declaration_required":True,"human_related_work_acceptance_required":True,"automatic_authority_ranking":False,"automatic_impact_scoring":False,"automatic_seminal_work_classification":False,"automatic_literature_gap_claims":False,"automatic_truth_promotion":False,"research_knowledge_graph_remains_citation_graph_authority":True,"knowledge_library_remains_source_authority":True,"platform_core_remains_authority":True}}
        for ref in body.get("seed_source_refs") or []:
            rec["works"].append(self._work_payload(LiteratureWorkAddRequest(actor_ref=actor,source_ref=ref,title=ref)))
        self._save(rec); self._event(iid,"literature-intelligence.created",actor,{"seed_work_count":len(rec["works"])}); return self.get(iid)
    def _work_payload(self,req:LiteratureWorkAddRequest)->dict[str,Any]:
        body=req.model_dump(); body.pop("actor_ref",None); key=body.get("source_ref") or body.get("identifiers") or body.get("title")
        return {"work_id":_id("work-",key),**body,"authors":_uniq(body.get("authors") or []),"registered_utc":_now(),"human_registered":True}
    def add_work(self,iid:str,req:LiteratureWorkAddRequest)->dict[str,Any]:
        rec=self.get(iid); work=self._work_payload(req)
        if not any(x["work_id"]==work["work_id"] for x in rec["works"]): rec["works"].append(work); self._save(rec); self._event(iid,"work.added",req.actor_ref,{"work_id":work["work_id"],"source_ref":work["source_ref"]})
        return self.get(iid)
    def _work(self,rec:dict[str,Any],wid:str)->dict[str,Any]:
        for w in rec.get("works",[]):
            if w.get("work_id")==wid: return w
        raise ValueError("Literature work not found.")
    def add_citation_context(self,iid:str,req:CitationContextAddRequest)->dict[str,Any]:
        rec=self.get(iid); self._work(rec,req.citing_work_id); self._work(rec,req.cited_work_id)
        if req.citing_work_id==req.cited_work_id: raise ValueError("Citation self-links are not permitted.")
        body=req.model_dump(); actor=body.pop("actor_ref"); cid=_id("citctx-",body)
        item={"citation_context_id":cid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["citation_context_id"]==cid for x in rec["citation_contexts"]): rec["citation_contexts"].append(item); self._save(rec); self._event(iid,"citation-context.added",actor,{"citation_context_id":cid})
        return self.get(iid)
    def add_strand(self,iid:str,req:LiteratureStrandAddRequest)->dict[str,Any]:
        rec=self.get(iid); ids=_uniq(req.work_ids); [self._work(rec,x) for x in ids]
        body=req.model_dump(); actor=body.pop("actor_ref"); body["work_ids"]=ids; sid=_id("strand-",body)
        item={"strand_id":sid,**body,"human_labeled":True,"created_utc":_now()}
        if not any(x["strand_id"]==sid for x in rec["literature_strands"]): rec["literature_strands"].append(item); self._save(rec); self._event(iid,"literature-strand.added",actor,{"strand_id":sid})
        return self.get(iid)
    def add_gap(self,iid:str,req:LiteratureGapAddRequest)->dict[str,Any]:
        rec=self.get(iid); ids=_uniq(req.work_ids); [self._work(rec,x) for x in ids]
        body=req.model_dump(); actor=body.pop("actor_ref"); body["work_ids"]=ids; gid=_id("gap-",body)
        item={"gap_id":gid,**body,"human_declared":True,"created_utc":_now()}
        if not any(x["gap_id"]==gid for x in rec["gaps"]): rec["gaps"].append(item); self._save(rec); self._event(iid,"literature-gap.added",actor,{"gap_id":gid})
        return self.get(iid)
    def add_seminal_candidate(self,iid:str,req:SeminalCandidateAddRequest)->dict[str,Any]:
        rec=self.get(iid); self._work(rec,req.work_id); body=req.model_dump(); actor=body.pop("actor_ref"); cid=_id("seminalcand-",body)
        item={"candidate_id":cid,**body,"human_declared":True,"classification_performed":False,"created_utc":_now()}
        if not any(x["candidate_id"]==cid for x in rec["seminal_candidates"]): rec["seminal_candidates"].append(item); self._save(rec); self._event(iid,"seminal-candidate.added",actor,{"candidate_id":cid})
        return self.get(iid)
    def add_related_work_candidate(self,iid:str,req:RelatedWorkCandidateAddRequest)->dict[str,Any]:
        rec=self.get(iid); self._work(rec,req.source_work_id); self._work(rec,req.target_work_id)
        if req.source_work_id==req.target_work_id: raise ValueError("Related-work self-links are not permitted.")
        body=req.model_dump(); actor=body.pop("actor_ref"); cid=_id("relcand-",body)
        item={"candidate_id":cid,**body,"decision":"pending","decision_rationale":"","decision_actor_ref":"","created_utc":_now()}
        if not any(x["candidate_id"]==cid for x in rec["related_work_candidates"]): rec["related_work_candidates"].append(item); self._save(rec); self._event(iid,"related-work-candidate.added",actor,{"candidate_id":cid})
        return self.get(iid)
    def decide_related_work(self,iid:str,req:RelatedWorkDecisionRequest)->dict[str,Any]:
        rec=self.get(iid); found=False
        for x in rec["related_work_candidates"]:
            if x["candidate_id"]==req.candidate_id:
                x.update({"decision":req.decision,"decision_rationale":req.rationale,"decision_actor_ref":req.actor_ref,"decided_utc":_now()}); found=True; break
        if not found: raise ValueError("Related-work candidate not found.")
        self._save(rec); self._event(iid,"related-work-candidate.decided",req.actor_ref,{"candidate_id":req.candidate_id,"decision":req.decision}); return self.get(iid)
    def set_state(self,iid:str,req:LiteratureIntelligenceStateRequest)->dict[str,Any]:
        rec=self.get(iid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(iid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(iid)
    def citation_matrix(self,iid:str)->dict[str,Any]:
        rec=self.get(iid); by={}; inbound={w["work_id"]:0 for w in rec["works"]}; outbound={w["work_id"]:0 for w in rec["works"]}
        for c in rec["citation_contexts"]:
            by[c["function"]]=by.get(c["function"],0)+1; outbound[c["citing_work_id"]]=outbound.get(c["citing_work_id"],0)+1; inbound[c["cited_work_id"]]=inbound.get(c["cited_work_id"],0)+1
        indicators=[{"work_id":w["work_id"],"source_ref":w["source_ref"],"publication_year":w.get("publication_year"),"inbound_registered_citations":inbound.get(w["work_id"],0),"outbound_registered_citations":outbound.get(w["work_id"],0)} for w in rec["works"]]
        return {"schema":SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA,"intelligence_id":iid,"citation_function_counts":by,"descriptive_visibility_indicators":indicators,"governance":{"counts_are_corpus_descriptors_not_quality_or_authority_scores":True,"automatic_impact_ranking":False,"automatic_seminal_work_classification":False}}
    def landscape(self,iid:str)->dict[str,Any]:
        rec=self.get(iid); accepted=[x for x in rec["related_work_candidates"] if x.get("decision")=="accepted"]
        return {"schema":SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA,"intelligence_id":iid,"works":rec["works"],"citation_contexts":rec["citation_contexts"],"literature_strands":rec["literature_strands"],"accepted_related_work":accepted,"seminal_candidates":rec["seminal_candidates"],"gaps":rec["gaps"],"governance":{"literature_strands_are_human_labeled":True,"related_work_requires_human_acceptance":True,"seminal_candidates_are_human_declared_not_classified":True}}
    def graph_handoffs(self,iid:str)->dict[str,Any]:
        rec=self.get(iid); works={w["work_id"]:w for w in rec["works"]}; edges=[]
        for c in rec["citation_contexts"]:
            edges.append({"source_ref":works[c["citing_work_id"]]["source_ref"],"target_ref":works[c["cited_work_id"]]["source_ref"],"relation":"cites","source_basis":"citation","evidence_refs":c.get("evidence_refs",[]),"annotation_ref":c["citation_context_id"]})
        for r in rec["related_work_candidates"]:
            if r.get("decision")=="accepted": edges.append({"source_ref":works[r["source_work_id"]]["source_ref"],"target_ref":works[r["target_work_id"]]["source_ref"],"relation":r.get("relation") or "related-to","source_basis":"declared","evidence_refs":r.get("evidence_refs",[]),"annotation_ref":r["candidate_id"]})
        return {"schema":SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA,"intelligence_id":iid,"target":"research-knowledge-graph","edge_candidates":edges,"write_performed":False,"governance":{"research_knowledge_graph_remains_citation_graph_authority":True,"human_acceptance_required_before_graph_write":True,"automatic_graph_write":False}}
    def readiness(self,iid:str)->dict[str,Any]:
        rec=self.get(iid); dimensions={"work_corpus_registered":bool(rec["works"]),"citation_context_available":bool(rec["citation_contexts"]),"human_review_approved":rec["review"]["state"]=="approved","systematic_review_bound":bool(rec.get("systematic_review_id"))}
        blockers=[k.replace("_","-") for k in ["work_corpus_registered","human_review_approved"] if not dimensions[k]]
        return {"schema":SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA,"intelligence_id":iid,"ready_for_governed_handoff":not blockers,"dimensions":dimensions,"blockers":blockers,"governance":{"readiness_is_structural_not_scholarly_quality_judgment":True}}
    def core_candidate(self,iid:str)->dict[str,Any]:
        rec=self.get(iid); candidate={"candidate_id":_id("corecand-",{"intelligence_id":iid,"type":"scholarly-literature-intelligence"}),"object_type":"scholarly-literature-intelligence","source_intelligence_id":iid,"payload":{"research_question":rec.get("research_question",""),"systematic_review_id":rec.get("systematic_review_id",""),"landscape":self.landscape(iid),"citation_matrix":self.citation_matrix(iid)}}
        return {"schema":SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA,"intelligence_id":iid,"handoff_status":"human-approved-candidate" if rec["review"]["state"]=="approved" else "draft-candidate","candidate":candidate,"promotion_performed":False,"governance":{"platform_core_remains_authority":True,"automatic_truth_promotion":False}}
    def freeze_snapshot(self,req:LiteratureIntelligenceSnapshotRequest)->dict[str,Any]:
        rec=self.get(req.intelligence_id); payload={"schema":SCHOLARLY_LITERATURE_INTELLIGENCE_SNAPSHOT_SCHEMA,"intelligence_id":req.intelligence_id,"record":rec,"landscape":self.landscape(req.intelligence_id),"citation_matrix":self.citation_matrix(req.intelligence_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_literature_record_not_quality_or_truth_certification":True}}
        h=_sha(payload); sid="litintsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_literature_intelligence_snapshots(snapshot_id,intelligence_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.intelligence_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO scholarly_literature_intelligence_snapshots(snapshot_id,intelligence_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.intelligence_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.intelligence_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":SCHOLARLY_LITERATURE_INTELLIGENCE_SCHEMA,"release":settings.release_version,"milestone":"10.5","durable":True,"citation_context_intelligence":True,"literature_strands":True,"research_gap_registry":True,"seminal_candidate_registry":True,"related_work_review":True,"descriptive_citation_topology":True,"human_gap_declaration_required":True,"human_seminal_candidate_declaration_required":True,"human_related_work_acceptance_required":True,"automatic_authority_ranking":False,"automatic_impact_scoring":False,"automatic_seminal_work_classification":False,"automatic_literature_gap_claims":False,"automatic_graph_write":False,"automatic_truth_promotion":False,"research_knowledge_graph_remains_citation_graph_authority":True,"knowledge_library_remains_source_authority":True,"platform_core_remains_authority":True}

_store:ScholarlyLiteratureIntelligenceStore|None=None
def get_scholarly_literature_intelligence_store()->ScholarlyLiteratureIntelligenceStore:
    global _store
    if _store is None: _store=ScholarlyLiteratureIntelligenceStore()
    return _store
