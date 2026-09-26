from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.argument_claim_counterclaim_intelligence import (
    ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA, ARGUMENT_CLAIM_COUNTERCLAIM_SNAPSHOT_SCHEMA,
    ArgumentIntelligenceCreateRequest, ArgumentClaimAddRequest, ClaimEvidenceLinkRequest,
    ClaimRelationAddRequest, ClaimAssumptionAddRequest, ClaimDecisionRequest,
    ArgumentTensionAddRequest, ArgumentIntelligenceStateRequest, ArgumentIntelligenceSnapshotRequest,
)
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

class ArgumentClaimCounterclaimIntelligenceStore:
    def __init__(self, sqlite_path:Path|None=None, literature_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"argument_claim_counterclaim_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self.literature_store=literature_store
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres argument intelligence storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
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
CREATE TABLE IF NOT EXISTS argument_claim_counterclaim_intelligence(argument_intelligence_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS argument_claim_counterclaim_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,argument_intelligence_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS argument_claim_counterclaim_snapshots(snapshot_id TEXT PRIMARY KEY,argument_intelligence_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_argument_claim_counterclaim_intelligence(argument_intelligence_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_argument_claim_counterclaim_events(event_id BIGSERIAL PRIMARY KEY,argument_intelligence_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_argument_claim_counterclaim_events_project ON sc_rl_argument_claim_counterclaim_events(argument_intelligence_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_argument_claim_counterclaim_snapshots(snapshot_id TEXT PRIMARY KEY,argument_intelligence_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,aid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"argument_intelligence_id":aid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_argument_claim_counterclaim_events(argument_intelligence_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(aid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO argument_claim_counterclaim_events(argument_intelligence_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(aid,typ,actor,_json(payload),h,created))
    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_argument_claim_counterclaim_intelligence(argument_intelligence_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(argument_intelligence_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["argument_intelligence_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO argument_claim_counterclaim_intelligence(argument_intelligence_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["argument_intelligence_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,aid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_argument_claim_counterclaim_intelligence WHERE argument_intelligence_id=%s",(aid,)).fetchone()
            if not row: raise ValueError("Argument intelligence project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM argument_claim_counterclaim_intelligence WHERE argument_intelligence_id=?",(aid,)).fetchone()
        if not row: raise ValueError("Argument intelligence project not found.")
        return json.loads(row["record_json"])
    def create(self,req:ArgumentIntelligenceCreateRequest)->dict[str,Any]:
        body=req.model_dump(); actor=body.pop("actor_ref"); literature={}
        if body.get("literature_intelligence_id"):
            literature=self._literature().get(body["literature_intelligence_id"])
            body["research_question"]=body.get("research_question") or literature.get("research_question","")
            body["systematic_review_id"]=body.get("systematic_review_id") or literature.get("systematic_review_id","")
        seed={k:v for k,v in body.items() if k!="metadata"}; aid=_id("arginte-",seed)
        try: return self.get(aid)
        except ValueError: pass
        rec={"schema":ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA,"argument_intelligence_id":aid,**body,
             "literature_intelligence_fingerprint":literature.get("record_hash","") if literature else "",
             "claims":[],"evidence_links":[],"claim_relations":[],"assumptions":[],"tensions":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),
             "governance":{"claims_are_researcher_recorded_not_truth_certified":True,"counterclaims_are_not_automatically_generated":True,"evidence_relations_require_explicit_recording":True,"claim_acceptance_is_for_analysis_not_truth_status":True,"contradictions_are_preserved_not_resolved":True,"automatic_argument_ranking":False,"automatic_best_argument_selection":False,"automatic_claim_acceptance":False,"automatic_counterclaim_rejection":False,"automatic_truth_promotion":False,"platform_core_remains_argument_object_authority":True}}
        self._save(rec); self._event(aid,"argument-intelligence.created",actor,{"literature_intelligence_id":body.get("literature_intelligence_id","")}); return self.get(aid)
    def _claim(self,rec:dict[str,Any],cid:str)->dict[str,Any]:
        for c in rec.get("claims",[]):
            if c.get("claim_id")==cid: return c
        raise ValueError("Claim not found.")
    def _validate_work_ids(self,rec:dict[str,Any],work_ids:list[str])->None:
        if not work_ids or not rec.get("literature_intelligence_id"): return
        lit=self._literature().get(rec["literature_intelligence_id"]); known={w.get("work_id") for w in lit.get("works",[])}
        missing=[w for w in work_ids if w not in known]
        if missing: raise ValueError("One or more work_ids are not present in the bound literature intelligence project.")
    def add_claim(self,aid:str,req:ArgumentClaimAddRequest)->dict[str,Any]:
        rec=self.get(aid); work_ids=_uniq(req.work_ids); self._validate_work_ids(rec,work_ids)
        body=req.model_dump(); actor=body.pop("actor_ref"); body["work_ids"]=work_ids; body["source_refs"]=_uniq(body.get("source_refs") or []); body["evidence_refs"]=_uniq(body.get("evidence_refs") or [])
        cid=_id("claim-",{"argument_intelligence_id":aid,"statement":body["statement"],"role":body["role"],"claim_type":body["claim_type"]})
        item={"claim_id":cid,**body,"decision":"pending","decision_rationale":"","decision_actor_ref":"","human_recorded":True,"truth_status":"undetermined","created_utc":_now()}
        if not any(x["claim_id"]==cid for x in rec["claims"]): rec["claims"].append(item); self._save(rec); self._event(aid,"claim.added",actor,{"claim_id":cid,"role":body["role"]})
        return self.get(aid)
    def add_evidence_link(self,aid:str,req:ClaimEvidenceLinkRequest)->dict[str,Any]:
        rec=self.get(aid); self._claim(rec,req.claim_id); body=req.model_dump(); actor=body.pop("actor_ref"); lid=_id("clev-",body)
        item={"evidence_link_id":lid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["evidence_link_id"]==lid for x in rec["evidence_links"]): rec["evidence_links"].append(item); self._save(rec); self._event(aid,"claim-evidence.added",actor,{"evidence_link_id":lid,"claim_id":req.claim_id,"relation":req.relation})
        return self.get(aid)
    def add_claim_relation(self,aid:str,req:ClaimRelationAddRequest)->dict[str,Any]:
        rec=self.get(aid); self._claim(rec,req.source_claim_id); self._claim(rec,req.target_claim_id); body=req.model_dump(); actor=body.pop("actor_ref"); rid=_id("clrel-",body)
        item={"claim_relation_id":rid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["claim_relation_id"]==rid for x in rec["claim_relations"]): rec["claim_relations"].append(item); self._save(rec); self._event(aid,"claim-relation.added",actor,{"claim_relation_id":rid,"relation":req.relation})
        return self.get(aid)
    def add_assumption(self,aid:str,req:ClaimAssumptionAddRequest)->dict[str,Any]:
        rec=self.get(aid)
        if req.claim_id: self._claim(rec,req.claim_id)
        body=req.model_dump(); actor=body.pop("actor_ref"); sid=_id("assump-",body); item={"assumption_id":sid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["assumption_id"]==sid for x in rec["assumptions"]): rec["assumptions"].append(item); self._save(rec); self._event(aid,"assumption.added",actor,{"assumption_id":sid,"claim_id":req.claim_id})
        return self.get(aid)
    def decide_claim(self,aid:str,req:ClaimDecisionRequest)->dict[str,Any]:
        rec=self.get(aid); claim=self._claim(rec,req.claim_id); claim.update({"decision":req.decision,"decision_rationale":req.rationale,"decision_actor_ref":req.actor_ref,"decided_utc":_now(),"truth_status":"undetermined"})
        self._save(rec); self._event(aid,"claim.decision-recorded",req.actor_ref,{"claim_id":req.claim_id,"decision":req.decision}); return self.get(aid)
    def add_tension(self,aid:str,req:ArgumentTensionAddRequest)->dict[str,Any]:
        rec=self.get(aid); ids=_uniq(req.claim_ids); [self._claim(rec,c) for c in ids]
        body=req.model_dump(); actor=body.pop("actor_ref"); body["claim_ids"]=ids; tid=_id("tension-",body); item={"tension_id":tid,**body,"human_recorded":True,"resolution_not_inferred":True,"created_utc":_now()}
        if not any(x["tension_id"]==tid for x in rec["tensions"]): rec["tensions"].append(item); self._save(rec); self._event(aid,"tension.added",actor,{"tension_id":tid,"state":req.state})
        return self.get(aid)
    def set_state(self,aid:str,req:ArgumentIntelligenceStateRequest)->dict[str,Any]:
        rec=self.get(aid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(aid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(aid)
    def claim_evidence_matrix(self,aid:str)->dict[str,Any]:
        rec=self.get(aid); links={c["claim_id"]:[] for c in rec["claims"]}
        for e in rec["evidence_links"]: links.setdefault(e["claim_id"],[]).append(e)
        rows=[]
        for c in rec["claims"]:
            rel_counts={}
            for e in links.get(c["claim_id"],[]): rel_counts[e["relation"]]=rel_counts.get(e["relation"],0)+1
            rows.append({"claim_id":c["claim_id"],"role":c["role"],"claim_type":c["claim_type"],"decision":c["decision"],"truth_status":"undetermined","evidence_relation_counts":rel_counts,"evidence_links":links.get(c["claim_id"],[])})
        return {"schema":ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA,"argument_intelligence_id":aid,"rows":rows,"governance":{"matrix_is_descriptive_not_evidence_strength_or_truth_score":True,"automatic_claim_ranking":False}}
    def argument_map(self,aid:str)->dict[str,Any]:
        rec=self.get(aid)
        nodes=[{"claim_id":c["claim_id"],"title":c.get("title") or c["statement"][:160],"statement":c["statement"],"role":c["role"],"claim_type":c["claim_type"],"decision":c["decision"],"truth_status":"undetermined"} for c in rec["claims"]]
        edges=[{"edge_id":r["claim_relation_id"],"source_claim_id":r["source_claim_id"],"target_claim_id":r["target_claim_id"],"relation":r["relation"],"rationale":r.get("rationale","")} for r in rec["claim_relations"]]
        return {"schema":ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA,"argument_intelligence_id":aid,"nodes":nodes,"edges":edges,"tensions":rec["tensions"],"assumptions":rec["assumptions"],"governance":{"map_preserves_disagreement":True,"automatic_best_argument_selection":False,"automatic_contradiction_resolution":False}}
    def contradiction_register(self,aid:str)->dict[str,Any]:
        rec=self.get(aid); contradictions=[e for e in rec["evidence_links"] if e["relation"]=="contradicts"]
        challenges=[r for r in rec["claim_relations"] if r["relation"] in {"challenges","rebuts","is_alternative_to"}]
        return {"schema":ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA,"argument_intelligence_id":aid,"evidence_contradictions":contradictions,"claim_challenges":challenges,"tensions":rec["tensions"],"governance":{"contradictions_are_registered_not_resolved":True,"resolution_requires_human_judgment":True}}
    def argument_synthesis_handoff(self,aid:str)->dict[str,Any]:
        rec=self.get(aid); nodes=[]
        for c in rec["claims"]:
            nodes.append({"local_ref":c["claim_id"],"core_object_type":"claim","core_object_id":"","role":"objection" if c["role"]=="counterclaim" else ("support" if c["role"] in {"subclaim","rebuttal","qualification"} else "premise"),"statement_text":c["statement"],"citation_refs":c.get("source_refs",[]),"uncertainty":c.get("uncertainty",{}),"metadata":{"source_role":c["role"],"decision":c["decision"],"truth_status":"undetermined"}})
        relations=[]
        mapping={"supports":"supports","challenges":"contradicts","rebuts":"contradicts","qualifies":"qualifies","depends_on":"contextualizes","is_alternative_to":"contradicts"}
        for r in rec["claim_relations"]: relations.append({"source_local_ref":r["source_claim_id"],"target_local_ref":r["target_claim_id"],"relation":mapping[r["relation"]],"rationale":r.get("rationale","") ,"evidence_refs":r.get("evidence_refs",[])})
        return {"schema":ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA,"argument_intelligence_id":aid,"target":"argument-synthesis-plan","core_project_id":rec.get("core_project_id",""),"title":rec["title"],"thesis_text":next((c["statement"] for c in rec["claims"] if c["role"]=="thesis"),""),"nodes":nodes,"relations":relations,"tensions":rec["tensions"],"write_performed":False,"governance":{"human_review_required_before_core_promotion":True,"automatic_relation_inference":False,"automatic_truth_determination":False}}
    def readiness(self,aid:str)->dict[str,Any]:
        rec=self.get(aid); dims={"claims_registered":bool(rec["claims"]),"counterclaim_or_challenge_registered":any(c["role"]=="counterclaim" for c in rec["claims"]) or any(r["relation"] in {"challenges","rebuts","is_alternative_to"} for r in rec["claim_relations"]),"evidence_links_registered":bool(rec["evidence_links"]),"human_review_approved":rec["review"]["state"]=="approved","literature_intelligence_bound":bool(rec.get("literature_intelligence_id"))}
        required=["claims_registered","evidence_links_registered","human_review_approved"]; blockers=[k.replace("_","-") for k in required if not dims[k]]
        return {"schema":ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA,"argument_intelligence_id":aid,"ready_for_governed_handoff":not blockers,"dimensions":dims,"blockers":blockers,"governance":{"readiness_is_structural_not_argument_quality_or_truth_judgment":True}}
    def core_candidate(self,aid:str)->dict[str,Any]:
        rec=self.get(aid); candidate={"candidate_id":_id("corecand-",{"argument_intelligence_id":aid,"type":"argument-claim-counterclaim-intelligence"}),"object_type":"argument-claim-counterclaim-intelligence","source_argument_intelligence_id":aid,"payload":{"research_question":rec.get("research_question",""),"literature_intelligence_id":rec.get("literature_intelligence_id",""),"argument_map":self.argument_map(aid),"claim_evidence_matrix":self.claim_evidence_matrix(aid)}}
        return {"schema":ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA,"argument_intelligence_id":aid,"handoff_status":"human-approved-candidate" if rec["review"]["state"]=="approved" else "draft-candidate","candidate":candidate,"promotion_performed":False,"governance":{"platform_core_remains_argument_object_authority":True,"automatic_truth_promotion":False}}
    def freeze_snapshot(self,req:ArgumentIntelligenceSnapshotRequest)->dict[str,Any]:
        rec=self.get(req.argument_intelligence_id); payload={"schema":ARGUMENT_CLAIM_COUNTERCLAIM_SNAPSHOT_SCHEMA,"argument_intelligence_id":req.argument_intelligence_id,"record":rec,"argument_map":self.argument_map(req.argument_intelligence_id),"claim_evidence_matrix":self.claim_evidence_matrix(req.argument_intelligence_id),"contradiction_register":self.contradiction_register(req.argument_intelligence_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_argument_record_not_truth_certification":True}}
        h=_sha(payload); sid="argintsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_argument_claim_counterclaim_snapshots(snapshot_id,argument_intelligence_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.argument_intelligence_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO argument_claim_counterclaim_snapshots(snapshot_id,argument_intelligence_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.argument_intelligence_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.argument_intelligence_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":ARGUMENT_CLAIM_COUNTERCLAIM_INTELLIGENCE_SCHEMA,"release":settings.release_version,"milestone":"10.6","durable":True,"claim_registry":True,"counterclaim_registry":True,"claim_evidence_matrix":True,"argument_maps":True,"assumption_registry":True,"contradiction_and_tension_registry":True,"argument_synthesis_handoffs":True,"human_claim_recording_required":True,"human_evidence_relation_recording_required":True,"claim_acceptance_is_for_analysis_not_truth_status":True,"automatic_argument_ranking":False,"automatic_best_argument_selection":False,"automatic_claim_acceptance":False,"automatic_counterclaim_rejection":False,"automatic_contradiction_resolution":False,"automatic_truth_promotion":False,"platform_core_remains_argument_object_authority":True}

_store:ArgumentClaimCounterclaimIntelligenceStore|None=None
def get_argument_claim_counterclaim_intelligence_store()->ArgumentClaimCounterclaimIntelligenceStore:
    global _store
    if _store is None: _store=ArgumentClaimCounterclaimIntelligenceStore()
    return _store
