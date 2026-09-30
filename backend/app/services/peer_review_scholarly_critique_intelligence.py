from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator, Callable
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.peer_review_scholarly_critique_intelligence import *
try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None; dict_row=None; Jsonb=None

def _json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256(_json(v).encode()).hexdigest()
def _now(): return datetime.now(timezone.utc).isoformat()
def _id(p,v): return p+_sha(v)[:32]
def _uniq(values): return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))

class PeerReviewScholarlyCritiqueIntelligenceStore:
    def __init__(self,sqlite_path:Path|None=None,target_resolvers:dict[str,Callable[[str],dict[str,Any]]]|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"peer_review_scholarly_critique_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self._lock=threading.RLock(); self.target_resolvers=target_resolvers or {}
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres scholarly critique storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _default_resolver(self,target_type):
        try:
            if target_type=="scholarly-study":
                from .scholarly_research import get_scholarly_research_store; return get_scholarly_research_store().get
            if target_type=="research-integrity-audit":
                from .research_integrity_methodological_audit import get_research_integrity_methodological_audit_store; return get_research_integrity_methodological_audit_store().get
            if target_type=="cross-study-synthesis-plan":
                from .cross_study_synthesis_meta_research import get_cross_study_synthesis_meta_research_store; return get_cross_study_synthesis_meta_research_store().get
            if target_type=="reproduction-replication-plan":
                from .reproduction_replication_intelligence import get_reproduction_replication_intelligence_store; return get_reproduction_replication_intelligence_store().get
            if target_type=="study-protocol":
                from .study_protocol_preregistration import get_study_protocol_preregistration_store; return get_study_protocol_preregistration_store().get
            if target_type=="statistical-analysis-plan-intelligence":
                from .statistical_analysis_planning_intelligence import get_statistical_analysis_planning_intelligence_store; return get_statistical_analysis_planning_intelligence_store().get
            if target_type=="causal-research-design":
                from .causal_research_design_intelligence import get_causal_research_design_intelligence_store; return get_causal_research_design_intelligence_store().get
            if target_type=="simulation-model-study-plan":
                from .simulation_model_study_planner import get_simulation_model_study_planner_store; return get_simulation_model_study_planner_store().get
        except Exception: return None
        return None
    def _resolve_target(self,item):
        typ=str(item.get("target_type") or ""); ref=str(item.get("target_ref") or ""); resolver=self.target_resolvers.get(typ) or self._default_resolver(typ)
        resolved_hash=str(item.get("source_hash") or ""); resolved=False
        if resolver is not None:
            try: record=resolver(ref)
            except Exception as exc: raise ValueError(f"critique target is not available for {typ}: {ref}") from exc
            resolved_hash=str(record.get("record_hash") or record.get("snapshot_hash") or record.get("study_fingerprint") or resolved_hash); resolved=True
        return {**item,"resolved":resolved,"resolved_hash":resolved_hash,"lineage_checked_utc":_now()}
    @contextmanager
    def _sqlite(self):
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()
    @contextmanager
    def _postgres(self,migration=False):
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()
    def _migrate_sqlite(self):
        with self._lock,self._sqlite() as c: c.executescript("""
CREATE TABLE IF NOT EXISTS scholarly_critique_projects(critique_project_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scholarly_critique_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,critique_project_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scholarly_critique_snapshots(snapshot_id TEXT PRIMARY KEY,critique_project_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_scholarly_critique_projects(critique_project_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_scholarly_critique_events(event_id BIGSERIAL PRIMARY KEY,critique_project_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_scholarly_critique_events_project ON sc_rl_scholarly_critique_events(critique_project_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_scholarly_critique_snapshots(snapshot_id TEXT PRIMARY KEY,critique_project_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,pid,typ,actor,payload):
        created=_now(); h=_sha({"critique_project_id":pid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_critique_events(critique_project_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(pid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO scholarly_critique_events(critique_project_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(pid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_critique_projects(critique_project_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(critique_project_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["critique_project_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO scholarly_critique_projects(critique_project_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["critique_project_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,pid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_scholarly_critique_projects WHERE critique_project_id=%s",(pid,)).fetchone()
            if not row: raise ValueError("Scholarly critique project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM scholarly_critique_projects WHERE critique_project_id=?",(pid,)).fetchone()
        if not row: raise ValueError("Scholarly critique project not found.")
        return json.loads(row["record_json"])
    def create(self,req):
        body=req.model_dump(); actor=body.pop("actor_ref"); targets=[self._resolve_target(x) for x in body.pop("targets")]
        for k in ["upstream_peer_review_refs","research_integrity_audit_refs","review_standard_refs"]: body[k]=_uniq(body.get(k,[]))
        pid=_id("critique-",{**body,"targets":targets})
        try: return self.get(pid)
        except ValueError: pass
        rec={"schema":SCHOLARLY_CRITIQUE_SCHEMA,"critique_project_id":pid,**body,"targets":targets,"review_rounds":[],"critique_dimensions":[],"reviewer_critiques":[],"author_responses":[],"revision_requirements":[],"verification_requests":[],"verification_receipts":[],"critique_syntheses":[],"decisions":[],"review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),"governance":{"reviewer_critiques_are_human_authored":True,"author_responses_are_preserved_separately":True,"cross_review_synthesis_preserves_disagreement":True,"specialist_runtimes_own_verification_execution":True,"editorial_decision_remains_separate_human_action":True,"anonymous_labels_do_not_deanonymize_reviewers":True,"automatic_accept_reject":False,"automatic_editorial_decision":False,"automatic_reviewer_ranking":False,"automatic_scientific_validity_verdict":False,"automatic_misconduct_inference":False,"automatic_comment_resolution":False,"automatic_publication_block":False,"automatic_execution":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(pid,"scholarly-critique.created",actor,{"target_count":len(targets)}); return self.get(pid)
    def _append(self,pid,key,idkey,prefix,body,event,extra=None):
        rec=self.get(pid); actor=body.pop("actor_ref"); oid=_id(prefix,body); item={idkey:oid,**body,**(extra or {}),"created_utc":_now()}
        if not any(x[idkey]==oid for x in rec[key]): rec[key].append(item); self._save(rec); self._event(pid,event,actor,{idkey:oid})
        return self.get(pid)
    def add_round(self,pid,req): return self._append(pid,"review_rounds","round_id","round-",req.model_dump(),"review-round.added",{"state":"open","decision":"pending"})
    def add_dimension(self,pid,req): return self._append(pid,"critique_dimensions","dimension_id","dimension-",req.model_dump(),"critique-dimension.added",{"decision":"pending"})
    def add_reviewer_critique(self,pid,req):
        rec=self.get(pid)
        if req.round_id not in {x["round_id"] for x in rec["review_rounds"]}: raise ValueError("round_id is not registered in this critique project.")
        if req.dimension_id not in {x["dimension_id"] for x in rec["critique_dimensions"]}: raise ValueError("dimension_id is not registered in this critique project.")
        return self._append(pid,"reviewer_critiques","critique_id","comment-",req.model_dump(),"reviewer-critique.added",{"resolution_status":"open","human_authored":True,"not_editorial_decision":True,"not_scientific_validity_verdict":True,"reviewer_score":None})
    def add_author_response(self,pid,req):
        rec=self.get(pid)
        if req.critique_id not in {x["critique_id"] for x in rec["reviewer_critiques"]}: raise ValueError("critique_id is not registered in this critique project.")
        self._append(pid,"author_responses","author_response_id","response-",req.model_dump(),"author-response.added",{"human_authored":True,"does_not_auto_resolve_critique":True})
        rec=self.get(pid)
        for item in rec["reviewer_critiques"]:
            if item["critique_id"]==req.critique_id: item["latest_response_status"]=req.response_status; item["latest_response_utc"]=_now(); break
        self._save(rec); return self.get(pid)
    def add_revision_requirement(self,pid,req):
        rec=self.get(pid); known={x["critique_id"] for x in rec["reviewer_critiques"]}; unknown=[x for x in req.critique_ids if x not in known]
        if unknown: raise ValueError(f"unknown critique_ids: {unknown}")
        return self._append(pid,"revision_requirements","revision_requirement_id","requirement-",req.model_dump(),"revision-requirement.added",{"status":"open","decision":"pending","completion_is_not_acceptance":True})
    def set_revision_requirement_status(self,pid,req):
        rec=self.get(pid); found=False
        for item in rec["revision_requirements"]:
            if item["revision_requirement_id"]==req.revision_requirement_id: item.update({"status":req.status,"status_note":req.note,"status_actor_ref":req.actor_ref,"status_updated_utc":_now()}); found=True; break
        if not found: raise ValueError("revision_requirement_id is not registered in this critique project.")
        self._save(rec); self._event(pid,"revision-requirement.status",req.actor_ref,{"revision_requirement_id":req.revision_requirement_id,"status":req.status}); return self.get(pid)
    def add_verification_request(self,pid,req):
        rec=self.get(pid); known={x["critique_id"] for x in rec["reviewer_critiques"]}; unknown=[x for x in req.critique_ids if x not in known]
        if unknown: raise ValueError(f"unknown critique_ids: {unknown}")
        return self._append(pid,"verification_requests","verification_request_id","verify-",req.model_dump(),"verification-request.added",{"decision":"pending","execution_performed":False})
    def add_verification_receipt(self,pid,req):
        rec=self.get(pid); request=next((x for x in rec["verification_requests"] if x["verification_request_id"]==req.verification_request_id),None)
        if request is None: raise ValueError("verification_request_id is not registered in this critique project.")
        if request.get("decision")!="approved": raise ValueError("verification request requires an explicit human approval before accepting an execution receipt.")
        return self._append(pid,"verification_receipts","verification_receipt_id","receipt-",req.model_dump(),"verification-receipt.added",{"receipt_is_observation_not_review_verdict":True,"automatic_critique_resolution":False})
    def add_critique_synthesis(self,pid,req):
        rec=self.get(pid); known={x["critique_id"] for x in rec["reviewer_critiques"]}; unknown=[x for x in req.critique_ids if x not in known]
        if unknown: raise ValueError(f"unknown critique_ids: {unknown}")
        if req.round_id and req.round_id not in {x["round_id"] for x in rec["review_rounds"]}: raise ValueError("round_id is not registered in this critique project.")
        return self._append(pid,"critique_syntheses","critique_synthesis_id","synthesis-",req.model_dump(),"critique-synthesis.added",{"human_authored":True,"preserves_disagreement":True,"not_editorial_decision":True,"decision":"pending"})
    def decide(self,pid,req):
        rec=self.get(pid); mapping={"round":("review_rounds","round_id"),"dimension":("critique_dimensions","dimension_id"),"critique":("reviewer_critiques","critique_id"),"revision-requirement":("revision_requirements","revision_requirement_id"),"verification-request":("verification_requests","verification_request_id"),"critique-synthesis":("critique_syntheses","critique_synthesis_id")}
        key,idkey=mapping[req.object_type]; found=False
        for item in rec[key]:
            if item[idkey]==req.object_id: item.update({"decision":req.decision,"decision_rationale":req.rationale,"decision_actor_ref":req.actor_ref,"decision_updated_utc":_now()}); found=True; break
        if not found: raise ValueError("decision object is not registered in this critique project.")
        rec["decisions"].append({"decision_id":_id("decision-",req.model_dump()),**req.model_dump(),"created_utc":_now()}); self._save(rec); self._event(pid,"human-decision.recorded",req.actor_ref,{"object_type":req.object_type,"object_id":req.object_id,"decision":req.decision}); return self.get(pid)
    def set_state(self,pid,req):
        rec=self.get(pid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(pid,"critique-project.state",req.actor_ref,{"state":req.state}); return self.get(pid)
    def cross_review_matrix(self,pid):
        rec=self.get(pid); dims={x["dimension_id"]:x for x in rec["critique_dimensions"]}; rows=[]
        for item in rec["reviewer_critiques"]:
            d=dims.get(item["dimension_id"],{}); rows.append({"critique_id":item["critique_id"],"round_id":item["round_id"],"domain":d.get("domain",""),"dimension_label":d.get("label",""),"reviewer_ref":item["reviewer_ref"],"anonymous_label":item.get("anonymous_label",""),"comment_kind":item["comment_kind"],"significance":item["significance"],"resolution_status":item.get("resolution_status","open"),"latest_response_status":item.get("latest_response_status",""),"requested_actions":item.get("requested_actions",[])})
        return {"schema":SCHOLARLY_CRITIQUE_SCHEMA,"critique_project_id":pid,"rows":rows,"governance":{"matrix_is_descriptive_not_reviewer_ranking":True,"no_majority_vote":True}}
    def issue_register(self,pid):
        rec=self.get(pid); responses={}
        for r in rec["author_responses"]: responses.setdefault(r["critique_id"],[]).append(r)
        open_items=[]
        for c in rec["reviewer_critiques"]:
            latest=responses.get(c["critique_id"],[]); status=latest[-1]["response_status"] if latest else c.get("resolution_status","open")
            if status not in {"addressed","accepted-with-rationale","not-applicable"}: open_items.append({"critique_id":c["critique_id"],"significance":c["significance"],"comment_kind":c["comment_kind"],"critique":c["critique"],"response_status":status})
        return {"schema":SCHOLARLY_CRITIQUE_SCHEMA,"critique_project_id":pid,"open_items":open_items,"count":len(open_items),"governance":{"open_issue_is_review_state_not_rejection":True}}
    def response_coverage(self,pid):
        rec=self.get(pid); ids={x["critique_id"] for x in rec["reviewer_critiques"]}; responded={x["critique_id"] for x in rec["author_responses"]}
        return {"schema":SCHOLARLY_CRITIQUE_SCHEMA,"critique_project_id":pid,"critique_count":len(ids),"responded_count":len(ids & responded),"unanswered_critique_ids":sorted(ids-responded),"governance":{"coverage_is_descriptive_not_acceptance_metric":True}}
    def verification_handoffs(self,pid):
        rec=self.get(pid); packets=[]
        for v in rec["verification_requests"]:
            if v.get("decision")=="approved": packets.append({"schema":"sc-research-librarian-scholarly-critique-verification-handoff/1.0","critique_project_id":pid,"verification_request_id":v["verification_request_id"],"runtime_target":v["runtime_target"],"requested_check":v["requested_check"],"target_refs":v["target_refs"],"critique_ids":v["critique_ids"],"expected_artifacts":v["expected_artifacts"],"execution_performed":False,"editorial_decision_not_inferred":True,"scientific_validity_not_inferred":True})
        return {"schema":SCHOLARLY_CRITIQUE_SCHEMA,"critique_project_id":pid,"packets":packets}
    def readiness(self,pid):
        rec=self.get(pid); issues=self.issue_register(pid); coverage=self.response_coverage(pid); dims={"target_bound":bool(rec["targets"]),"review_round_present":bool(rec["review_rounds"]),"critique_dimensions_present":bool(rec["critique_dimensions"]),"human_critiques_present":bool(rec["reviewer_critiques"]),"response_coverage_available":coverage["critique_count"]>0,"cross_review_matrix_available":True}
        blockers=[k.replace("_","-") for k in ["target_bound","review_round_present","critique_dimensions_present","human_critiques_present"] if not dims[k]]
        return {"schema":SCHOLARLY_CRITIQUE_SCHEMA,"critique_project_id":pid,"ready_for_editorial_review":not blockers,"dimensions":dims,"blockers":blockers,"open_issue_count":issues["count"],"governance":{"readiness_is_structural_not_accept_reject_recommendation":True,"automatic_editorial_decision":False}}
    def editorial_handoff(self,pid):
        rec=self.get(pid); return {"schema":"sc-research-librarian-editorial-critique-handoff/1.0","critique_project_id":pid,"targets":rec["targets"],"cross_review_matrix":self.cross_review_matrix(pid),"issue_register":self.issue_register(pid),"response_coverage":self.response_coverage(pid),"critique_syntheses":rec["critique_syntheses"],"revision_requirements":rec["revision_requirements"],"verification_receipts":rec["verification_receipts"],"editorial_decision":None,"governance":{"human_editorial_decision_required":True,"no_accept_reject_recommendation_generated":True,"reviewer_ranking":False}}
    def core_candidate(self,pid):
        rec=self.get(pid); return {"schema":"sc-research-librarian-scholarly-critique-core-candidate/1.0","critique_project_id":pid,"record_hash":rec["record_hash"],"targets":rec["targets"],"critique_dimensions":rec["critique_dimensions"],"reviewer_critiques":rec["reviewer_critiques"],"author_responses":rec["author_responses"],"revision_requirements":rec["revision_requirements"],"critique_syntheses":rec["critique_syntheses"],"human_review_required":True,"editorial_decision_not_inferred":True,"scientific_validity_not_certified":True,"truth_promoted":False}
    def freeze_snapshot(self,req):
        rec=self.get(req.critique_project_id); payload={"schema":SCHOLARLY_CRITIQUE_SNAPSHOT_SCHEMA,"critique_project_id":req.critique_project_id,"record":rec,"cross_review_matrix":self.cross_review_matrix(req.critique_project_id),"issue_register":self.issue_register(req.critique_project_id),"response_coverage":self.response_coverage(req.critique_project_id),"readiness":self.readiness(req.critique_project_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_preserves_review_lineage_not_editorial_verdict":True}}
        h=_sha(payload); sid="critiquesnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_scholarly_critique_snapshots(snapshot_id,critique_project_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.critique_project_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO scholarly_critique_snapshots(snapshot_id,critique_project_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.critique_project_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.critique_project_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities():
    return {"schema":SCHOLARLY_CRITIQUE_SCHEMA,"release":settings.release_version,"milestone":"11.8","durable":True,"review_rounds":True,"structured_critique_dimensions":True,"human_reviewer_critiques":True,"author_response_lineage":True,"revision_requirement_tracking":True,"cross_review_matrix":True,"critique_synthesis":True,"specialist_verification_handoffs":True,"editorial_handoff":True,"reviewer_critiques_are_human_authored":True,"cross_review_synthesis_preserves_disagreement":True,"specialist_runtimes_own_verification_execution":True,"editorial_decision_remains_separate_human_action":True,"automatic_accept_reject":False,"automatic_editorial_decision":False,"automatic_reviewer_ranking":False,"automatic_scientific_validity_verdict":False,"automatic_misconduct_inference":False,"automatic_comment_resolution":False,"automatic_publication_block":False,"automatic_execution":False,"automatic_truth_promotion":False}

_store=None
def get_peer_review_scholarly_critique_intelligence_store():
    global _store
    if _store is None: _store=PeerReviewScholarlyCritiqueIntelligenceStore()
    return _store
