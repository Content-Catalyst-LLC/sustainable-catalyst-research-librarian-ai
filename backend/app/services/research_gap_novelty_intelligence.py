from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.research_gap_novelty_intelligence import (
    RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA, RESEARCH_GAP_NOVELTY_SNAPSHOT_SCHEMA,
    ResearchGapNoveltyCreateRequest, ResearchGapCandidateAddRequest, ResearchGapDecisionRequest,
    NoveltyCandidateAddRequest, NoveltyDecisionRequest, OriginalResearchOpportunityAddRequest,
    ResearchGapNoveltyStateRequest, ResearchGapNoveltySnapshotRequest,
)
from .argument_claim_counterclaim_intelligence import get_argument_claim_counterclaim_intelligence_store
from .scholarly_literature_intelligence import get_scholarly_literature_intelligence_store

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

class ResearchGapNoveltyIntelligenceStore:
    def __init__(self, sqlite_path:Path|None=None, argument_store:Any|None=None, literature_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"research_gap_novelty_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self.argument_store=argument_store; self.literature_store=literature_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres research gap/novelty storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _arguments(self): return self.argument_store or get_argument_claim_counterclaim_intelligence_store()
    def _literature(self): return self.literature_store or get_scholarly_literature_intelligence_store()
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
CREATE TABLE IF NOT EXISTS research_gap_novelty_intelligence(gap_novelty_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_gap_novelty_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,gap_novelty_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_gap_novelty_snapshots(snapshot_id TEXT PRIMARY KEY,gap_novelty_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_research_gap_novelty_intelligence(gap_novelty_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_gap_novelty_events(event_id BIGSERIAL PRIMARY KEY,gap_novelty_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_research_gap_novelty_events_project ON sc_rl_research_gap_novelty_events(gap_novelty_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_gap_novelty_snapshots(snapshot_id TEXT PRIMARY KEY,gap_novelty_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,gid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"gap_novelty_id":gid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_gap_novelty_events(gap_novelty_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(gid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO research_gap_novelty_events(gap_novelty_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(gid,typ,actor,_json(payload),h,created))
    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_gap_novelty_intelligence(gap_novelty_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(gap_novelty_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["gap_novelty_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO research_gap_novelty_intelligence(gap_novelty_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["gap_novelty_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,gid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_research_gap_novelty_intelligence WHERE gap_novelty_id=%s",(gid,)).fetchone()
            if not row: raise ValueError("Research gap/novelty project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM research_gap_novelty_intelligence WHERE gap_novelty_id=?",(gid,)).fetchone()
        if not row: raise ValueError("Research gap/novelty project not found.")
        return json.loads(row["record_json"])
    def create(self,req:ResearchGapNoveltyCreateRequest)->dict[str,Any]:
        body=req.model_dump(); actor=body.pop("actor_ref"); arg={}; lit={}
        if body.get("argument_intelligence_id"):
            arg=self._arguments().get(body["argument_intelligence_id"])
            body["research_question"]=body.get("research_question") or arg.get("research_question","")
            body["literature_intelligence_id"]=body.get("literature_intelligence_id") or arg.get("literature_intelligence_id","")
            body["systematic_review_id"]=body.get("systematic_review_id") or arg.get("systematic_review_id","")
            body["core_project_id"]=body.get("core_project_id") or arg.get("core_project_id","")
        if body.get("literature_intelligence_id"):
            lit=self._literature().get(body["literature_intelligence_id"])
            body["research_question"]=body.get("research_question") or lit.get("research_question","")
            body["systematic_review_id"]=body.get("systematic_review_id") or lit.get("systematic_review_id","")
            body["research_design_plan_id"]=body.get("research_design_plan_id") or lit.get("research_design_plan_id","")
        seed={k:v for k,v in body.items() if k!="metadata"}; gid=_id("gapnov-",seed)
        try: return self.get(gid)
        except ValueError: pass
        rec={"schema":RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA,"gap_novelty_id":gid,**body,
             "argument_intelligence_fingerprint":arg.get("record_hash","") if arg else "","literature_intelligence_fingerprint":lit.get("record_hash","") if lit else "",
             "gap_candidates":[],"novelty_candidates":[],"research_opportunities":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),
             "governance":{"gap_signals_are_descriptive_candidates_not_validated_gaps":True,"human_gap_acceptance_required":True,"human_novelty_acceptance_required":True,"novelty_requires_explicit_comparison_basis":True,"research_opportunities_are_planning_candidates_not_originality_certification":True,"absence_of_evidence_is_not_evidence_of_absence":True,"automatic_gap_certification":False,"automatic_novelty_certification":False,"automatic_originality_claims":False,"automatic_priority_ranking":False,"automatic_truth_promotion":False,"platform_core_remains_research_object_authority":True}}
        self._save(rec); self._event(gid,"research-gap-novelty.created",actor,{"argument_intelligence_id":body.get("argument_intelligence_id","")}); return self.get(gid)
    def _argument(self,rec): return self._arguments().get(rec["argument_intelligence_id"]) if rec.get("argument_intelligence_id") else {}
    def _literature_rec(self,rec): return self._literature().get(rec["literature_intelligence_id"]) if rec.get("literature_intelligence_id") else {}
    def _known(self,items,key): return {x.get(key) for x in items}
    def _validate_refs(self,rec,claim_ids=None,work_ids=None,tension_ids=None):
        arg=self._argument(rec); lit=self._literature_rec(rec)
        checks=[("claim_ids",claim_ids or [],self._known(arg.get("claims",[]),"claim_id")),("tension_ids",tension_ids or [],self._known(arg.get("tensions",[]),"tension_id")),("work_ids",work_ids or [],self._known(lit.get("works",[]),"work_id"))]
        for label,vals,known in checks:
            missing=[v for v in vals if v not in known]
            if missing: raise ValueError(f"One or more {label} are not present in the bound upstream project.")
    def add_gap_candidate(self,gid:str,req:ResearchGapCandidateAddRequest)->dict[str,Any]:
        rec=self.get(gid); body=req.model_dump(); actor=body.pop("actor_ref"); body["claim_ids"]=_uniq(body["claim_ids"]); body["work_ids"]=_uniq(body["work_ids"]); body["tension_ids"]=_uniq(body["tension_ids"]); body["evidence_refs"]=_uniq(body["evidence_refs"])
        self._validate_refs(rec,body["claim_ids"],body["work_ids"],body["tension_ids"]); gap_id=_id("rgap-",body)
        item={"gap_id":gap_id,**body,"decision":"pending","decision_rationale":"","human_recorded":True,"validated_gap":False,"created_utc":_now()}
        if not any(x["gap_id"]==gap_id for x in rec["gap_candidates"]): rec["gap_candidates"].append(item); self._save(rec); self._event(gid,"gap-candidate.added",actor,{"gap_id":gap_id,"gap_type":req.gap_type})
        return self.get(gid)
    def decide_gap(self,gid:str,req:ResearchGapDecisionRequest)->dict[str,Any]:
        rec=self.get(gid); gap=next((x for x in rec["gap_candidates"] if x["gap_id"]==req.gap_id),None)
        if gap is None: raise ValueError("Gap candidate not found.")
        gap.update({"decision":req.decision,"decision_rationale":req.rationale,"decision_actor_ref":req.actor_ref,"decided_utc":_now(),"validated_gap":req.decision=="accepted"})
        self._save(rec); self._event(gid,"gap-candidate.decision-recorded",req.actor_ref,{"gap_id":req.gap_id,"decision":req.decision}); return self.get(gid)
    def add_novelty_candidate(self,gid:str,req:NoveltyCandidateAddRequest)->dict[str,Any]:
        rec=self.get(gid); body=req.model_dump(); actor=body.pop("actor_ref"); body["gap_ids"]=_uniq(body["gap_ids"]); body["claim_ids"]=_uniq(body["claim_ids"]); body["work_ids"]=_uniq(body["work_ids"]); body["evidence_refs"]=_uniq(body["evidence_refs"])
        known_gaps={x["gap_id"] for x in rec["gap_candidates"]}; missing=[x for x in body["gap_ids"] if x not in known_gaps]
        if missing: raise ValueError("One or more gap_ids are not present in the research gap/novelty project.")
        self._validate_refs(rec,body["claim_ids"],body["work_ids"],[])
        if not body.get("comparison_basis").strip(): raise ValueError("comparison_basis is required for a novelty candidate.")
        nid=_id("novel-",body); item={"novelty_candidate_id":nid,**body,"decision":"pending","human_recorded":True,"novelty_certified":False,"created_utc":_now()}
        if not any(x["novelty_candidate_id"]==nid for x in rec["novelty_candidates"]): rec["novelty_candidates"].append(item); self._save(rec); self._event(gid,"novelty-candidate.added",actor,{"novelty_candidate_id":nid,"novelty_type":req.novelty_type})
        return self.get(gid)
    def decide_novelty(self,gid:str,req:NoveltyDecisionRequest)->dict[str,Any]:
        rec=self.get(gid); item=next((x for x in rec["novelty_candidates"] if x["novelty_candidate_id"]==req.novelty_candidate_id),None)
        if item is None: raise ValueError("Novelty candidate not found.")
        item.update({"decision":req.decision,"decision_rationale":req.rationale,"decision_actor_ref":req.actor_ref,"decided_utc":_now(),"novelty_certified":False})
        self._save(rec); self._event(gid,"novelty-candidate.decision-recorded",req.actor_ref,{"novelty_candidate_id":req.novelty_candidate_id,"decision":req.decision}); return self.get(gid)
    def add_research_opportunity(self,gid:str,req:OriginalResearchOpportunityAddRequest)->dict[str,Any]:
        rec=self.get(gid); body=req.model_dump(); actor=body.pop("actor_ref"); body["gap_ids"]=_uniq(body["gap_ids"]); body["novelty_candidate_ids"]=_uniq(body["novelty_candidate_ids"]); body["method_candidate_refs"]=_uniq(body["method_candidate_refs"]); body["data_requirement_refs"]=_uniq(body["data_requirement_refs"])
        gaps={x["gap_id"]:x for x in rec["gap_candidates"]}; novels={x["novelty_candidate_id"]:x for x in rec["novelty_candidates"]}
        if any(x not in gaps for x in body["gap_ids"]): raise ValueError("Research opportunity references an unknown gap_id.")
        if any(x not in novels for x in body["novelty_candidate_ids"]): raise ValueError("Research opportunity references an unknown novelty_candidate_id.")
        oid=_id("opportunity-",body); item={"opportunity_id":oid,**body,"human_recorded":True,"originality_certified":False,"created_utc":_now()}
        if not any(x["opportunity_id"]==oid for x in rec["research_opportunities"]): rec["research_opportunities"].append(item); self._save(rec); self._event(gid,"research-opportunity.added",actor,{"opportunity_id":oid})
        return self.get(gid)
    def structural_signals(self,gid:str)->dict[str,Any]:
        rec=self.get(gid); arg=self._argument(rec); lit=self._literature_rec(rec); signals=[]
        for t in arg.get("tensions",[]):
            if t.get("state")=="open": signals.append({"signal_type":"unresolved-contradiction-or-tension","source_ref":t.get("tension_id",""),"description":t.get("description","")})
        links_by_claim={c.get("claim_id"):0 for c in arg.get("claims",[])}
        for e in arg.get("evidence_links",[]): links_by_claim[e.get("claim_id")]=links_by_claim.get(e.get("claim_id"),0)+1
        for cid,count in links_by_claim.items():
            if cid and count==0: signals.append({"signal_type":"claim-without-recorded-evidence-link","source_ref":cid,"description":"No evidence link is recorded for this claim in the bound argument project."})
        for g in lit.get("gaps",[]): signals.append({"signal_type":"human-declared-literature-gap","source_ref":g.get("gap_id",""),"description":g.get("description","")})
        for strand in lit.get("literature_strands",[]):
            if len(strand.get("work_ids") or [])<=1: signals.append({"signal_type":"sparse-literature-strand","source_ref":strand.get("strand_id",""),"description":"This human-labeled literature strand contains one or fewer registered works."})
        return {"schema":RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA,"gap_novelty_id":gid,"signals":signals,"governance":{"signals_are_structural_observations_not_validated_research_gaps":True,"absence_of_evidence_is_not_evidence_of_absence":True,"human_gap_acceptance_required":True,"automatic_gap_certification":False}}
    def landscape(self,gid:str)->dict[str,Any]:
        rec=self.get(gid); by_type={}; by_decision={}
        for g in rec["gap_candidates"]: by_type[g["gap_type"]]=by_type.get(g["gap_type"],0)+1; by_decision[g["decision"]]=by_decision.get(g["decision"],0)+1
        novelty_by_type={}; novelty_by_decision={}
        for n in rec["novelty_candidates"]: novelty_by_type[n["novelty_type"]]=novelty_by_type.get(n["novelty_type"],0)+1; novelty_by_decision[n["decision"]]=novelty_by_decision.get(n["decision"],0)+1
        return {"schema":RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA,"gap_novelty_id":gid,"gap_counts_by_type":by_type,"gap_counts_by_decision":by_decision,"novelty_counts_by_type":novelty_by_type,"novelty_counts_by_decision":novelty_by_decision,"research_opportunity_count":len(rec["research_opportunities"]),"structural_signal_count":len(self.structural_signals(gid)["signals"]),"governance":{"landscape_is_descriptive_not_priority_or_novelty_score":True,"automatic_priority_ranking":False}}
    def set_state(self,gid:str,req:ResearchGapNoveltyStateRequest)->dict[str,Any]:
        rec=self.get(gid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(gid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(gid)
    def readiness(self,gid:str)->dict[str,Any]:
        rec=self.get(gid); dims={"gap_candidate_registered":bool(rec["gap_candidates"]),"human_accepted_gap":any(x["decision"]=="accepted" for x in rec["gap_candidates"]),"human_review_approved":rec["review"]["state"]=="approved","argument_or_literature_lineage_bound":bool(rec.get("argument_intelligence_id") or rec.get("literature_intelligence_id"))}
        required=["gap_candidate_registered","human_accepted_gap","human_review_approved","argument_or_literature_lineage_bound"]; blockers=[k.replace("_","-") for k in required if not dims[k]]
        return {"schema":RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA,"gap_novelty_id":gid,"ready_for_governed_handoff":not blockers,"dimensions":dims,"blockers":blockers,"governance":{"readiness_is_structural_not_novelty_or_originality_certification":True}}
    def research_planning_handoff(self,gid:str)->dict[str,Any]:
        rec=self.get(gid); accepted_gaps=[x for x in rec["gap_candidates"] if x["decision"]=="accepted"]; accepted_novelty=[x for x in rec["novelty_candidates"] if x["decision"]=="accepted"]
        return {"schema":RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA,"gap_novelty_id":gid,"target":"research-question-and-design-planning","research_question":rec.get("research_question",""),"accepted_gap_candidates":accepted_gaps,"accepted_novelty_candidates":accepted_novelty,"research_opportunities":rec["research_opportunities"],"write_performed":False,"governance":{"human_review_required_before_new_research_plan":True,"novelty_acceptance_is_not_originality_certification":True,"automatic_execution":False}}
    def core_candidate(self,gid:str)->dict[str,Any]:
        rec=self.get(gid); candidate={"candidate_id":_id("corecand-",{"gap_novelty_id":gid,"type":"research-gap-novelty-intelligence"}),"object_type":"research-gap-novelty-intelligence","source_gap_novelty_id":gid,"payload":{"research_question":rec.get("research_question",""),"argument_intelligence_id":rec.get("argument_intelligence_id",""),"literature_intelligence_id":rec.get("literature_intelligence_id",""),"landscape":self.landscape(gid),"accepted_gaps":[x for x in rec["gap_candidates"] if x["decision"]=="accepted"],"accepted_novelty_candidates":[x for x in rec["novelty_candidates"] if x["decision"]=="accepted"],"research_opportunities":rec["research_opportunities"]}}
        return {"schema":RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA,"gap_novelty_id":gid,"handoff_status":"human-approved-candidate" if rec["review"]["state"]=="approved" else "draft-candidate","candidate":candidate,"promotion_performed":False,"governance":{"platform_core_remains_research_object_authority":True,"automatic_novelty_certification":False,"automatic_truth_promotion":False}}
    def freeze_snapshot(self,req:ResearchGapNoveltySnapshotRequest)->dict[str,Any]:
        rec=self.get(req.gap_novelty_id); payload={"schema":RESEARCH_GAP_NOVELTY_SNAPSHOT_SCHEMA,"gap_novelty_id":req.gap_novelty_id,"record":rec,"structural_signals":self.structural_signals(req.gap_novelty_id),"landscape":self.landscape(req.gap_novelty_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_gap_novelty_record_not_originality_certification":True}}
        h=_sha(payload); sid="gapnovsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_gap_novelty_snapshots(snapshot_id,gap_novelty_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.gap_novelty_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO research_gap_novelty_snapshots(snapshot_id,gap_novelty_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.gap_novelty_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.gap_novelty_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":RESEARCH_GAP_NOVELTY_INTELLIGENCE_SCHEMA,"release":settings.release_version,"milestone":"10.7","durable":True,"structural_gap_signals":True,"research_gap_candidate_registry":True,"novelty_candidate_registry":True,"original_research_opportunity_registry":True,"argument_and_literature_lineage":True,"human_gap_acceptance_required":True,"human_novelty_acceptance_required":True,"novelty_requires_explicit_comparison_basis":True,"gap_signals_are_descriptive_candidates_not_validated_gaps":True,"research_opportunities_are_planning_candidates_not_originality_certification":True,"absence_of_evidence_is_not_evidence_of_absence":True,"automatic_gap_certification":False,"automatic_novelty_certification":False,"automatic_originality_claims":False,"automatic_priority_ranking":False,"automatic_truth_promotion":False,"platform_core_remains_research_object_authority":True}

_store:ResearchGapNoveltyIntelligenceStore|None=None
def get_research_gap_novelty_intelligence_store()->ResearchGapNoveltyIntelligenceStore:
    global _store
    if _store is None: _store=ResearchGapNoveltyIntelligenceStore()
    return _store
