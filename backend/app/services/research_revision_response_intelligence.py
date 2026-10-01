from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator, Callable

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.research_revision_response_intelligence import *

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None; dict_row=None; Jsonb=None

def _json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256(_json(v).encode()).hexdigest()
def _now(): return datetime.now(timezone.utc).isoformat()
def _id(prefix,v): return prefix+_sha(v)[:32]
def _uniq(values): return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))

class ResearchRevisionResponseIntelligenceStore:
    def __init__(self,sqlite_path:Path|None=None,critique_resolver:Callable[[str],dict[str,Any]]|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"research_revision_response_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self._lock=threading.RLock()
        self.critique_resolver=critique_resolver
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres revision-response storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()

    def _resolve_critique(self,ref):
        resolver=self.critique_resolver
        if resolver is None:
            from .peer_review_scholarly_critique_intelligence import get_peer_review_scholarly_critique_intelligence_store
            resolver=get_peer_review_scholarly_critique_intelligence_store().get
        try: record=resolver(ref)
        except Exception as exc: raise ValueError(f"critique project is not available: {ref}") from exc
        return record

    @contextmanager
    def _sqlite(self):
        c=sqlite3.connect(self.sqlite_path,timeout=30,isolation_level=None); c.row_factory=sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA busy_timeout=30000")
        try: yield c
        finally: c.close()

    @contextmanager
    def _postgres(self,migration=False):
        url=(settings.direct_database_url if migration else settings.database_url) or settings.database_url
        c=psycopg.connect(url,autocommit=False,row_factory=dict_row); c.execute(f'SET search_path TO "{self.database_schema}"')
        try: yield c
        finally: c.close()

    def _migrate_sqlite(self):
        with self._lock,self._sqlite() as c:
            c.executescript("""
CREATE TABLE IF NOT EXISTS revision_response_projects(revision_response_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS revision_response_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,revision_response_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS revision_response_snapshots(snapshot_id TEXT PRIMARY KEY,revision_response_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")

    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_revision_response_projects(revision_response_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_revision_response_events(event_id BIGSERIAL PRIMARY KEY,revision_response_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_revision_response_events_project ON sc_rl_revision_response_events(revision_response_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_revision_response_snapshots(snapshot_id TEXT PRIMARY KEY,revision_response_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()

    def _event(self,rid,typ,actor,payload):
        created=_now(); h=_sha({"revision_response_id":rid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_revision_response_events(revision_response_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(rid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute("INSERT INTO revision_response_events(revision_response_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(rid,typ,actor,_json(payload),h,created))

    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c:
                c.execute("INSERT INTO sc_rl_revision_response_projects(revision_response_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(revision_response_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["revision_response_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c:
                c.execute("INSERT OR REPLACE INTO revision_response_projects(revision_response_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["revision_response_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec

    def get(self,rid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_revision_response_projects WHERE revision_response_id=%s",(rid,)).fetchone()
            if not row: raise ValueError("Revision-response project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM revision_response_projects WHERE revision_response_id=?",(rid,)).fetchone()
        if not row: raise ValueError("Revision-response project not found.")
        return json.loads(row["record_json"])

    def create(self,req):
        body=req.model_dump(); actor=body.pop("actor_ref"); critique=self._resolve_critique(body["critique_project_ref"])
        critique_ids=[x.get("critique_id","") for x in critique.get("reviewer_critiques",[]) if x.get("critique_id")]
        requirement_ids=[x.get("revision_requirement_id","") for x in critique.get("revision_requirements",[]) if x.get("revision_requirement_id")]
        source_hash=str(critique.get("record_hash") or "")
        seed={**body,"critique_source_hash":source_hash}; rid=_id("revision-",seed)
        try:return self.get(rid)
        except ValueError:pass
        rec={"schema":REVISION_RESPONSE_SCHEMA,"revision_response_id":rid,**body,"critique_source_hash":source_hash,"known_critique_ids":critique_ids,"known_revision_requirement_ids":requirement_ids,"response_items":[],"change_claims":[],"artifact_receipts":[],"verification_requests":[],"verification_receipts":[],"resolution_reviews":[],"decisions":[],"review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),"governance":{"author_response_does_not_equal_reviewer_satisfaction":True,"change_claims_are_claims_until_supported_by_artifact_receipts":True,"artifact_receipts_are_observations_not_correctness_verdicts":True,"resolution_reviews_are_human_authored":True,"editorial_decision_remains_separate_human_action":True,"automatic_comment_satisfaction":False,"automatic_accept_reject":False,"automatic_editorial_decision":False,"automatic_scientific_validity_verdict":False,"automatic_misconduct_inference":False,"automatic_execution":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(rid,"revision-response.created",actor,{"critique_project_ref":body["critique_project_ref"]}); return self.get(rid)

    def _append(self,rid,key,idkey,prefix,body,event,extra=None):
        rec=self.get(rid); actor=body.pop("actor_ref"); oid=_id(prefix,body); item={idkey:oid,**body,**(extra or {}),"created_utc":_now()}
        if not any(x[idkey]==oid for x in rec[key]): rec[key].append(item); self._save(rec); self._event(rid,event,actor,{idkey:oid})
        return self.get(rid)

    def add_response_item(self,rid,req):
        rec=self.get(rid)
        unknown=[x for x in req.critique_ids if x not in rec["known_critique_ids"]]
        if unknown: raise ValueError(f"unknown critique_ids: {unknown}")
        unknown_req=[x for x in req.revision_requirement_ids if x not in rec["known_revision_requirement_ids"]]
        if unknown_req: raise ValueError(f"unknown revision_requirement_ids: {unknown_req}")
        return self._append(rid,"response_items","response_item_id","response-",req.model_dump(),"response-item.added",{"human_authored":True,"reviewer_satisfaction_not_inferred":True})

    def add_change_claim(self,rid,req):
        rec=self.get(rid)
        if req.response_item_id not in {x["response_item_id"] for x in rec["response_items"]}: raise ValueError("response_item_id is not registered.")
        return self._append(rid,"change_claims","change_claim_id","change-",req.model_dump(),"change-claim.added",{"claim_verified":False,"change_correctness_not_inferred":True})

    def add_artifact_receipt(self,rid,req):
        rec=self.get(rid)
        if req.response_item_id not in {x["response_item_id"] for x in rec["response_items"]}: raise ValueError("response_item_id is not registered.")
        return self._append(rid,"artifact_receipts","artifact_receipt_id","artifact-",req.model_dump(),"artifact-receipt.added",{"receipt_is_observation_not_resolution_verdict":True})

    def add_verification_request(self,rid,req):
        rec=self.get(rid); known={x["response_item_id"] for x in rec["response_items"]}
        unknown=[x for x in req.response_item_ids if x not in known]
        if unknown: raise ValueError(f"unknown response_item_ids: {unknown}")
        return self._append(rid,"verification_requests","verification_request_id","verify-",req.model_dump(),"verification-request.added",{"decision":"pending","execution_performed":False})

    def add_verification_receipt(self,rid,req):
        rec=self.get(rid); vr=next((x for x in rec["verification_requests"] if x["verification_request_id"]==req.verification_request_id),None)
        if vr is None: raise ValueError("verification_request_id is not registered.")
        if vr.get("decision")!="approved": raise ValueError("verification request requires explicit human approval.")
        return self._append(rid,"verification_receipts","verification_receipt_id","receipt-",req.model_dump(),"verification-receipt.added",{"receipt_is_observation_not_resolution_verdict":True})

    def add_resolution_review(self,rid,req):
        rec=self.get(rid)
        if req.response_item_id not in {x["response_item_id"] for x in rec["response_items"]}: raise ValueError("response_item_id is not registered.")
        return self._append(rid,"resolution_reviews","resolution_review_id","resolution-",req.model_dump(),"resolution-review.added",{"human_authored":True,"not_editorial_decision":True,"scientific_validity_not_inferred":True,"decision":"pending"})

    def decide(self,rid,req):
        rec=self.get(rid); mapping={"verification-request":("verification_requests","verification_request_id"),"resolution-review":("resolution_reviews","resolution_review_id")}
        if req.object_type=="response-package":
            obj={"response_package_id":"response-package-"+rid}
            if req.object_id!=obj["response_package_id"]: raise ValueError("response-package object_id must match the project package id.")
        else:
            key,idkey=mapping[req.object_type]; obj=next((x for x in rec[key] if x[idkey]==req.object_id),None)
            if obj is None: raise ValueError("decision object is not registered.")
            obj.update({"decision":req.decision,"decision_rationale":req.rationale,"decision_actor_ref":req.actor_ref,"decision_updated_utc":_now()})
        rec["decisions"].append({"decision_id":_id("decision-",req.model_dump()),**req.model_dump(),"created_utc":_now()}); self._save(rec); self._event(rid,"human-decision.recorded",req.actor_ref,req.model_dump()); return self.get(rid)

    def set_state(self,rid,req):
        rec=self.get(rid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(rid,"revision-response.state",req.actor_ref,{"state":req.state}); return self.get(rid)

    def response_matrix(self,rid):
        rec=self.get(rid); reviews={}
        for x in rec["resolution_reviews"]: reviews.setdefault(x["response_item_id"],[]).append(x)
        rows=[]
        for item in rec["response_items"]:
            rows.append({"response_item_id":item["response_item_id"],"critique_ids":item["critique_ids"],"revision_requirement_ids":item["revision_requirement_ids"],"response_position":item["response_position"],"change_claim_count":sum(1 for x in rec["change_claims"] if x["response_item_id"]==item["response_item_id"]),"artifact_receipt_count":sum(1 for x in rec["artifact_receipts"] if x["response_item_id"]==item["response_item_id"]),"resolution_reviews":reviews.get(item["response_item_id"],[])})
        return {"schema":REVISION_RESPONSE_SCHEMA,"revision_response_id":rid,"rows":rows,"governance":{"matrix_is_traceability_not_satisfaction_score":True}}

    def change_evidence_matrix(self,rid):
        rec=self.get(rid); rows=[]
        for claim in rec["change_claims"]:
            receipts=[x for x in rec["artifact_receipts"] if x["response_item_id"]==claim["response_item_id"]]
            rows.append({"change_claim_id":claim["change_claim_id"],"response_item_id":claim["response_item_id"],"change_type":claim["change_type"],"claimed_change":claim["claimed_change"],"before_hash":claim.get("before_hash",""),"after_hash":claim.get("after_hash",""),"artifact_receipts":receipts,"claim_supported_by_receipt":bool(receipts)})
        return {"schema":REVISION_RESPONSE_SCHEMA,"revision_response_id":rid,"rows":rows,"governance":{"receipt_support_does_not_certify_correctness":True}}

    def unresolved_register(self,rid):
        rec=self.get(rid); latest={}
        for rr in rec["resolution_reviews"]: latest[rr["response_item_id"]]=rr
        unresolved=[]
        for item in rec["response_items"]:
            rr=latest.get(item["response_item_id"])
            if rr is None or rr["judgment"] not in {"satisfied"}:
                unresolved.append({"response_item_id":item["response_item_id"],"critique_ids":item["critique_ids"],"response_position":item["response_position"],"latest_resolution_judgment":rr["judgment"] if rr else "not-assessed"})
        return {"schema":REVISION_RESPONSE_SCHEMA,"revision_response_id":rid,"unresolved":unresolved,"count":len(unresolved),"governance":{"unresolved_status_is_review_state_not_rejection":True}}

    def verification_handoffs(self,rid):
        rec=self.get(rid); packets=[]
        for v in rec["verification_requests"]:
            if v.get("decision")=="approved":
                packets.append({"schema":"sc-research-librarian-revision-verification-handoff/1.0","revision_response_id":rid,"verification_request_id":v["verification_request_id"],"runtime_target":v["runtime_target"],"requested_check":v["requested_check"],"response_item_ids":v["response_item_ids"],"expected_artifacts":v["expected_artifacts"],"execution_performed":False,"resolution_not_inferred":True})
        return {"schema":REVISION_RESPONSE_SCHEMA,"revision_response_id":rid,"packets":packets}

    def readiness(self,rid):
        rec=self.get(rid); dims={"critique_bound":bool(rec["critique_project_ref"]),"response_items_present":bool(rec["response_items"]),"traceable_revision_artifact":bool(rec.get("revised_artifact_ref") or rec.get("revised_artifact_hash")),"response_matrix_available":True,"change_evidence_matrix_available":True}
        blockers=[k.replace("_","-") for k in ["critique_bound","response_items_present"] if not dims[k]]
        return {"schema":REVISION_RESPONSE_SCHEMA,"revision_response_id":rid,"ready_for_human_review":not blockers,"dimensions":dims,"blockers":blockers,"unresolved_count":self.unresolved_register(rid)["count"],"governance":{"readiness_is_structural_not_acceptance_recommendation":True}}

    def response_package(self,rid):
        rec=self.get(rid)
        return {"schema":"sc-research-librarian-revision-response-package/1.0","response_package_id":"response-package-"+rid,"revision_response_id":rid,"critique_project_ref":rec["critique_project_ref"],"baseline_revision_ref":rec["baseline_revision_ref"],"baseline_revision_hash":rec["baseline_revision_hash"],"revised_artifact_ref":rec["revised_artifact_ref"],"revised_artifact_hash":rec["revised_artifact_hash"],"response_matrix":self.response_matrix(rid),"change_evidence_matrix":self.change_evidence_matrix(rid),"unresolved_register":self.unresolved_register(rid),"verification_receipts":rec["verification_receipts"],"editorial_decision":None,"governance":{"assembled_from_human_responses_not_auto_written":True,"human_editorial_decision_required":True,"no_accept_reject_recommendation_generated":True}}

    def core_candidate(self,rid):
        rec=self.get(rid)
        return {"schema":"sc-research-librarian-revision-response-core-candidate/1.0","revision_response_id":rid,"record_hash":rec["record_hash"],"critique_project_ref":rec["critique_project_ref"],"response_items":rec["response_items"],"change_claims":rec["change_claims"],"artifact_receipts":rec["artifact_receipts"],"resolution_reviews":rec["resolution_reviews"],"human_review_required":True,"reviewer_satisfaction_not_inferred":True,"scientific_validity_not_certified":True,"truth_promoted":False}

    def freeze_snapshot(self,req):
        rec=self.get(req.revision_response_id); payload={"schema":REVISION_RESPONSE_SNAPSHOT_SCHEMA,"revision_response_id":req.revision_response_id,"record":rec,"response_package":self.response_package(req.revision_response_id),"readiness":self.readiness(req.revision_response_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_preserves_revision_response_lineage_not_editorial_verdict":True}}
        h=_sha(payload); sid="revisionsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_revision_response_snapshots(snapshot_id,revision_response_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.revision_response_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO revision_response_snapshots(snapshot_id,revision_response_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.revision_response_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.revision_response_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities():
    return {"schema":REVISION_RESPONSE_SCHEMA,"release":settings.release_version,"milestone":"11.9","durable":True,"critique_to_response_traceability":True,"change_claims":True,"artifact_diff_receipts":True,"specialist_verification_handoffs":True,"human_resolution_reviews":True,"response_matrix":True,"change_evidence_matrix":True,"unresolved_register":True,"response_package":True,"author_response_does_not_equal_reviewer_satisfaction":True,"change_claims_are_claims_until_supported_by_artifact_receipts":True,"resolution_reviews_are_human_authored":True,"editorial_decision_remains_separate_human_action":True,"automatic_comment_satisfaction":False,"automatic_accept_reject":False,"automatic_editorial_decision":False,"automatic_scientific_validity_verdict":False,"automatic_misconduct_inference":False,"automatic_execution":False,"automatic_truth_promotion":False}

_store=None
def get_research_revision_response_intelligence_store():
    global _store
    if _store is None:_store=ResearchRevisionResponseIntelligenceStore()
    return _store
