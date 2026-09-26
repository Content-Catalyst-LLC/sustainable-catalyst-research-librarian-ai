from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.study_protocol_preregistration import *
from .research_program_intelligence import get_research_program_intelligence_store
try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg=None; dict_row=None; Jsonb=None

def _json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),default=str)
def _sha(v): return hashlib.sha256(_json(v).encode()).hexdigest()
def _now(): return datetime.now(timezone.utc).isoformat()
def _uniq(v): return list(dict.fromkeys(str(x).strip() for x in v if str(x).strip()))
def _id(p,v): return p+_sha(v)[:32]

class StudyProtocolPreregistrationStore:
    def __init__(self,sqlite_path:Path|None=None,research_program_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"study_protocol_preregistration.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self.research_program_store=research_program_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres study protocol storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _programs(self): return self.research_program_store or get_research_program_intelligence_store()
    @contextmanager
    def _sqlite(self)->Iterator[sqlite3.Connection]:
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
CREATE TABLE IF NOT EXISTS study_protocols(study_protocol_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS study_protocol_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,study_protocol_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS study_protocol_snapshots(snapshot_id TEXT PRIMARY KEY,study_protocol_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_study_protocols(study_protocol_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_study_protocol_events(event_id BIGSERIAL PRIMARY KEY,study_protocol_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_study_protocol_events_protocol ON sc_rl_study_protocol_events(study_protocol_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_study_protocol_snapshots(snapshot_id TEXT PRIMARY KEY,study_protocol_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,pid,typ,actor,payload):
        created=_now(); h=_sha({"study_protocol_id":pid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_study_protocol_events(study_protocol_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(pid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO study_protocol_events(study_protocol_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(pid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_study_protocols(study_protocol_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(study_protocol_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["study_protocol_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO study_protocols(study_protocol_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["study_protocol_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,pid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_study_protocols WHERE study_protocol_id=%s",(pid,)).fetchone()
            if not row: raise ValueError("Study protocol not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM study_protocols WHERE study_protocol_id=?",(pid,)).fetchone()
        if not row: raise ValueError("Study protocol not found.")
        return json.loads(row["record_json"])
    def create(self,req:StudyProtocolCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref")
        try: program=self._programs().get(body["research_program_id"])
        except Exception as exc: raise ValueError("research_program_id is not available in Research Program Intelligence.") from exc
        if body.get("workstream_id") and body["workstream_id"] not in {x.get("workstream_id") for x in program.get("workstreams",[])}: raise ValueError("workstream_id is not present in the bound research program.")
        body["research_question"]=body.get("research_question") or next((x.get("objective","") for x in program.get("workstreams",[]) if x.get("workstream_id")==body.get("workstream_id")),"")
        body["core_project_id"]=body.get("core_project_id") or program.get("core_project_id","")
        pid=_id("protocol-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(pid)
        except ValueError: pass
        rec={"schema":STUDY_PROTOCOL_PREREGISTRATION_SCHEMA,"study_protocol_id":pid,**body,"research_program_fingerprint":program.get("record_hash",""),"hypotheses":[],"outcomes":[],"variables":[],"sampling_plan":None,"analysis_commitments":[],"commitment_decisions":[],"amendments":[],"deviations":[],"registration":{"status":"not-preregistered","baseline_snapshot_id":"","baseline_snapshot_hash":"","registration_target":body.get("registration_target",""),"registration_identifier":"","registration_url":"","registered_utc":"","actor_ref":""},"protocol_version":1,"review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),"governance":{"protocol_is_declared_method_commitment_not_validity_certification":True,"preregistration_baseline_is_immutable_once_frozen":True,"amendments_are_append_only_and_linked_to_baseline":True,"deviations_are_disclosed_not_auto_judged":True,"human_preregistration_approval_required":True,"program_authority_remains_with_research_program_intelligence":True,"specialist_runtimes_own_execution":True,"platform_core_remains_research_object_authority":True,"automatic_hypothesis_acceptance":False,"automatic_method_selection":False,"automatic_preregistration":False,"automatic_amendment_acceptance":False,"automatic_deviation_judgment":False,"automatic_execution":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(pid,"study-protocol.created",actor,{"research_program_id":body["research_program_id"]}); return self.get(pid)
    def _assert_editable(self,rec):
        if rec["registration"]["status"]=="preregistered": raise ValueError("Preregistered baseline is immutable; record a protocol amendment instead of rewriting committed sections.")
    def add_hypothesis(self,pid,req:ProtocolHypothesisAddRequest):
        rec=self.get(pid); self._assert_editable(rec); body=req.model_dump(); actor=body.pop("actor_ref"); body["source_refs"]=_uniq(body["source_refs"]); hid=_id("phyp-",{k:v for k,v in body.items()}); item={"hypothesis_id":hid,**body,"human_recorded":True,"accepted_as_true":False,"created_utc":_now()}
        if not any(x["hypothesis_id"]==hid for x in rec["hypotheses"]): rec["hypotheses"].append(item); self._save(rec); self._event(pid,"hypothesis.added",actor,{"hypothesis_id":hid})
        return self.get(pid)
    def add_outcome(self,pid,req:ProtocolOutcomeAddRequest):
        rec=self.get(pid); self._assert_editable(rec); body=req.model_dump(); actor=body.pop("actor_ref"); body["source_refs"]=_uniq(body["source_refs"]); oid=_id("pout-",body); item={"outcome_id":oid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["outcome_id"]==oid for x in rec["outcomes"]): rec["outcomes"].append(item); self._save(rec); self._event(pid,"outcome.added",actor,{"outcome_id":oid})
        return self.get(pid)
    def add_variable(self,pid,req:ProtocolVariableAddRequest):
        rec=self.get(pid); self._assert_editable(rec); body=req.model_dump(); actor=body.pop("actor_ref"); body["source_refs"]=_uniq(body["source_refs"]); vid=_id("pvar-",body); item={"variable_id":vid,**body,"human_recorded":True,"semantic_validity_certified":False,"created_utc":_now()}
        if not any(x["variable_id"]==vid for x in rec["variables"]): rec["variables"].append(item); self._save(rec); self._event(pid,"variable.added",actor,{"variable_id":vid})
        return self.get(pid)
    def set_sampling_plan(self,pid,req:ProtocolSamplingPlanRequest):
        rec=self.get(pid); self._assert_editable(rec); body=req.model_dump(); actor=body.pop("actor_ref"); body["inclusion_criteria"]=_uniq(body["inclusion_criteria"]); body["exclusion_criteria"]=_uniq(body["exclusion_criteria"]); rec["sampling_plan"]={**body,"human_recorded":True,"adequacy_certified":False,"updated_utc":_now()}; self._save(rec); self._event(pid,"sampling-plan.recorded",actor,{"target_sample_size":body.get("target_sample_size")}); return self.get(pid)
    def add_analysis_commitment(self,pid,req:ProtocolAnalysisCommitmentAddRequest):
        rec=self.get(pid); self._assert_editable(rec); body=req.model_dump(); actor=body.pop("actor_ref")
        for k in ["hypothesis_ids","outcome_ids","variable_ids","robustness_checks"]: body[k]=_uniq(body[k])
        known_h={x["hypothesis_id"] for x in rec["hypotheses"]}; known_o={x["outcome_id"] for x in rec["outcomes"]}; known_v={x["variable_id"] for x in rec["variables"]}
        if any(x not in known_h for x in body["hypothesis_ids"]): raise ValueError("Analysis commitment references an unknown hypothesis_id.")
        if any(x not in known_o for x in body["outcome_ids"]): raise ValueError("Analysis commitment references an unknown outcome_id.")
        if any(x not in known_v for x in body["variable_ids"]): raise ValueError("Analysis commitment references an unknown variable_id.")
        cid=_id("commit-",{k:v for k,v in body.items()}); item={"commitment_id":cid,**body,"human_recorded":True,"method_not_executed":True,"created_utc":_now()}
        if not any(x["commitment_id"]==cid for x in rec["analysis_commitments"]): rec["analysis_commitments"].append(item); self._save(rec); self._event(pid,"analysis-commitment.added",actor,{"commitment_id":cid})
        return self.get(pid)
    def decide_commitment(self,pid,req:ProtocolCommitmentDecisionRequest):
        rec=self.get(pid); self._assert_editable(rec)
        if req.commitment_id not in {x["commitment_id"] for x in rec["analysis_commitments"]}: raise ValueError("Commitment decision references an unknown commitment_id.")
        item={"commitment_id":req.commitment_id,"decision":req.decision,"rationale":req.rationale,"actor_ref":req.actor_ref,"human_recorded":True,"scientific_validity_certified":False,"updated_utc":_now()}
        old=next((x for x in rec["commitment_decisions"] if x["commitment_id"]==req.commitment_id),None)
        if old: old.update(item)
        else: rec["commitment_decisions"].append(item)
        self._save(rec); self._event(pid,"analysis-commitment.decision",req.actor_ref,{"commitment_id":req.commitment_id,"decision":req.decision}); return self.get(pid)
    def protocol_matrix(self,pid):
        rec=self.get(pid); decisions={x["commitment_id"]:x["decision"] for x in rec["commitment_decisions"]}
        rows=[]
        for c in rec["analysis_commitments"]: rows.append({"commitment_id":c["commitment_id"],"label":c["label"],"method":c["method"],"hypothesis_ids":c["hypothesis_ids"],"outcome_ids":c["outcome_ids"],"variable_ids":c["variable_ids"],"decision":decisions.get(c["commitment_id"],"pending"),"computational_plan_id":c.get("computational_plan_id","")})
        return {"schema":STUDY_PROTOCOL_PREREGISTRATION_SCHEMA,"study_protocol_id":pid,"rows":rows,"governance":{"matrix_is_declared_commitment_structure_not_method_validity_or_results":True}}
    def readiness(self,pid):
        rec=self.get(pid); blockers=[]; decisions={x["commitment_id"]:x["decision"] for x in rec["commitment_decisions"]}
        if not rec["hypotheses"]: blockers.append("no-hypotheses")
        if not rec["outcomes"]: blockers.append("no-outcomes")
        if not rec["variables"]: blockers.append("no-variables")
        if not rec["sampling_plan"]: blockers.append("no-sampling-plan")
        if not rec["analysis_commitments"]: blockers.append("no-analysis-commitments")
        if rec["analysis_commitments"] and any(decisions.get(x["commitment_id"],"pending")!="approved" for x in rec["analysis_commitments"]): blockers.append("analysis-commitments-await-human-approval")
        return {"schema":STUDY_PROTOCOL_PREREGISTRATION_SCHEMA,"study_protocol_id":pid,"ready_for_preregistration":not blockers,"blockers":blockers,"dimensions":{"hypotheses_declared":bool(rec["hypotheses"]),"outcomes_declared":bool(rec["outcomes"]),"variables_declared":bool(rec["variables"]),"sampling_plan_declared":bool(rec["sampling_plan"]),"analysis_commitments_declared":bool(rec["analysis_commitments"]),"analysis_commitments_human_approved":bool(rec["analysis_commitments"]) and all(decisions.get(x["commitment_id"])=="approved" for x in rec["analysis_commitments"]),"already_preregistered":rec["registration"]["status"]=="preregistered"},"governance":{"readiness_is_structural_preregistration_completeness_not_scientific_validity":True,"automatic_preregistration":False}}
    def _snapshot_payload(self,rec,label,note):
        return {"schema":STUDY_PROTOCOL_SNAPSHOT_SCHEMA,"study_protocol_id":rec["study_protocol_id"],"protocol":rec,"protocol_matrix":self.protocol_matrix(rec["study_protocol_id"]),"readiness":self.readiness(rec["study_protocol_id"]),"label":label,"note":note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_protocol_record_not_validity_certification":True}}
    def freeze_snapshot(self,req:StudyProtocolSnapshotRequest):
        rec=self.get(req.study_protocol_id); payload=self._snapshot_payload(rec,req.label,req.note); h=_sha(payload); sid="protocolsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        self._store_snapshot(req.study_protocol_id,sid,h,payload); self._event(req.study_protocol_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload
    def _store_snapshot(self,pid,sid,h,payload):
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_study_protocol_snapshots(snapshot_id,study_protocol_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,pid,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO study_protocol_snapshots(snapshot_id,study_protocol_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,pid,h,_json(payload),payload["frozen_utc"]))
    def preregister(self,pid,req:ProtocolPreregisterRequest):
        rec=self.get(pid)
        if rec["registration"]["status"]=="preregistered": return rec
        ready=self.readiness(pid)
        if not ready["ready_for_preregistration"]: raise ValueError("Study protocol is not structurally ready for preregistration.")
        # freeze the exact pre-registration baseline before mutating registration metadata
        baseline=self._snapshot_payload(rec,"preregistration-baseline",req.note); h=_sha(baseline); sid="preregbaseline-"+h[:32]; baseline.update({"snapshot_id":sid,"snapshot_hash":h}); self._store_snapshot(pid,sid,h,baseline)
        rec["registration"]={"status":"preregistered","baseline_snapshot_id":sid,"baseline_snapshot_hash":h,"registration_target":req.registration_target or rec.get("registration_target","") ,"registration_identifier":req.registration_identifier,"registration_url":req.registration_url,"registered_utc":_now(),"actor_ref":req.actor_ref}
        rec["review"]={"state":"preregistered","note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(pid,"protocol.preregistered",req.actor_ref,{"baseline_snapshot_id":sid,"baseline_snapshot_hash":h,"registration_identifier":req.registration_identifier}); return self.get(pid)
    def add_amendment(self,pid,req:ProtocolAmendmentAddRequest):
        rec=self.get(pid)
        if rec["registration"]["status"]!="preregistered": raise ValueError("Protocol amendments are append-only records for a preregistered protocol; preregister first.")
        body=req.model_dump(); actor=body.pop("actor_ref"); body["affected_sections"]=_uniq(body["affected_sections"]); aid=_id("amend-",{"baseline":rec["registration"]["baseline_snapshot_hash"],**body}); item={"amendment_id":aid,**body,"baseline_snapshot_id":rec["registration"]["baseline_snapshot_id"],"baseline_snapshot_hash":rec["registration"]["baseline_snapshot_hash"],"human_recorded":True,"acceptance_not_inferred":True,"created_utc":_now()}
        if not any(x["amendment_id"]==aid for x in rec["amendments"]): rec["amendments"].append(item); rec["protocol_version"]+=1; rec["review"]={"state":"amended","note":"","actor_ref":actor,"updated_utc":_now()}; self._save(rec); self._event(pid,"protocol.amendment-recorded",actor,{"amendment_id":aid,"impact":body["impact"]})
        return self.get(pid)
    def add_deviation(self,pid,req:ProtocolDeviationAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["affected_commitment_ids"]=_uniq(body["affected_commitment_ids"]); known={x["commitment_id"] for x in rec["analysis_commitments"]}
        if any(x not in known for x in body["affected_commitment_ids"]): raise ValueError("Deviation references an unknown commitment_id.")
        did=_id("deviation-",body); item={"deviation_id":did,**body,"human_recorded":True,"invalidity_not_inferred":True,"created_utc":_now()}
        if not any(x["deviation_id"]==did for x in rec["deviations"]): rec["deviations"].append(item); self._save(rec); self._event(pid,"protocol.deviation-recorded",actor,{"deviation_id":did,"category":body["category"]})
        return self.get(pid)
    def set_state(self,pid,req:StudyProtocolStateRequest):
        rec=self.get(pid)
        if rec["registration"]["status"]=="preregistered" and req.state in {"draft","in_review"}: raise ValueError("A preregistered protocol cannot be reverted to a pre-registration state; use amendments/deviations.")
        rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(pid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(pid)
    def handoffs(self,pid):
        rec=self.get(pid); ready=self.readiness(pid); return {"schema":STUDY_PROTOCOL_PREREGISTRATION_SCHEMA,"study_protocol_id":pid,"packets":[{"schema":"sc-research-librarian-study-protocol-handoff/1.0","handoff_id":_id("protocolhand-",{"protocol":pid,"target":"computational-research"}),"target":"computational-research-planning","protocol_version":rec["protocol_version"],"baseline_snapshot_hash":rec["registration"]["baseline_snapshot_hash"],"analysis_commitments":rec["analysis_commitments"],"sampling_plan":rec["sampling_plan"],"amendments":rec["amendments"],"deviations":rec["deviations"],"handoff_ready":rec["registration"]["status"]=="preregistered" and ready["ready_for_preregistration"],"write_performed":False,"execution_performed":False,"method_selection_performed":False}],"governance":{"handoff_is_protocol_context_not_execution_order":True,"specialist_runtime_execution_preserved":True}}
    def core_candidate(self,pid):
        rec=self.get(pid); registered=rec["registration"]["status"]=="preregistered"
        return {"schema":"sc-research-librarian-core-study-protocol-candidate/1.0","candidate_id":_id("corecand-",{"study_protocol_id":pid,"type":"study-protocol"}),"object_type":"study-protocol","source_study_protocol_id":pid,"payload":{"title":rec["title"],"protocol_ref":rec["protocol_ref"],"research_program_id":rec["research_program_id"],"research_question":rec["research_question"],"study_type":rec["study_type"],"hypotheses":rec["hypotheses"],"outcomes":rec["outcomes"],"variables":rec["variables"],"sampling_plan":rec["sampling_plan"],"analysis_commitments":rec["analysis_commitments"],"registration":rec["registration"],"amendments":rec["amendments"],"deviations":rec["deviations"]},"handoff_status":"preregistered-candidate" if registered else "draft-candidate","promotion_performed":False,"execution_performed":False,"governance":{"platform_core_remains_authoritative":True,"candidate_is_not_promoted_object":True,"preregistration_is_not_scientific_validity_certification":True}}

def capabilities():
    return {"schema":STUDY_PROTOCOL_PREREGISTRATION_SCHEMA,"release":settings.release_version,"milestone":"11.1","durable":True,"research_program_lineage":True,"hypothesis_registry":True,"outcome_registry":True,"variable_registry":True,"sampling_plan":True,"analysis_commitment_registry":True,"preregistration_baseline_snapshot":True,"append_only_amendments":True,"deviation_registry":True,"protocol_matrix":True,"human_preregistration_approval_required":True,"preregistration_baseline_is_immutable_once_frozen":True,"program_authority_remains_with_research_program_intelligence":True,"specialist_runtimes_own_execution":True,"platform_core_remains_research_object_authority":True,"automatic_hypothesis_acceptance":False,"automatic_method_selection":False,"automatic_preregistration":False,"automatic_amendment_acceptance":False,"automatic_deviation_judgment":False,"automatic_execution":False,"automatic_truth_promotion":False}
_store=None
def get_study_protocol_preregistration_store():
    global _store
    if _store is None: _store=StudyProtocolPreregistrationStore()
    return _store
