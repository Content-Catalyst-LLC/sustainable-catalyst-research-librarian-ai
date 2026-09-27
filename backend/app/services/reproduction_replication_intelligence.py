from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.reproduction_replication_intelligence import *
from .study_protocol_preregistration import get_study_protocol_preregistration_store
from .statistical_analysis_planning_intelligence import get_statistical_analysis_planning_intelligence_store
from .causal_research_design_intelligence import get_causal_research_design_intelligence_store
from .simulation_model_study_planner import get_simulation_model_study_planner_store
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

class ReproductionReplicationIntelligenceStore:
    def __init__(self,sqlite_path:Path|None=None,study_protocol_store:Any|None=None,statistical_store:Any|None=None,causal_store:Any|None=None,simulation_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"reproduction_replication_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self.study_protocol_store=study_protocol_store; self.statistical_store=statistical_store; self.causal_store=causal_store; self.simulation_store=simulation_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres reproduction/replication storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _protocols(self): return self.study_protocol_store or get_study_protocol_preregistration_store()
    def _stats(self): return self.statistical_store or get_statistical_analysis_planning_intelligence_store()
    def _causal(self): return self.causal_store or get_causal_research_design_intelligence_store()
    def _simulation(self): return self.simulation_store or get_simulation_model_study_planner_store()
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
CREATE TABLE IF NOT EXISTS reproduction_replication_projects(reproduction_replication_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reproduction_replication_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,reproduction_replication_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reproduction_replication_snapshots(snapshot_id TEXT PRIMARY KEY,reproduction_replication_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_reproduction_replication_projects(reproduction_replication_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_reproduction_replication_events(event_id BIGSERIAL PRIMARY KEY,reproduction_replication_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_reproduction_replication_events_project ON sc_rl_reproduction_replication_events(reproduction_replication_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_reproduction_replication_snapshots(snapshot_id TEXT PRIMARY KEY,reproduction_replication_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,rid,typ,actor,payload):
        created=_now(); h=_sha({"reproduction_replication_id":rid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_reproduction_replication_events(reproduction_replication_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(rid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO reproduction_replication_events(reproduction_replication_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(rid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_reproduction_replication_projects(reproduction_replication_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(reproduction_replication_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["reproduction_replication_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO reproduction_replication_projects(reproduction_replication_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["reproduction_replication_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,rid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_reproduction_replication_projects WHERE reproduction_replication_id=%s",(rid,)).fetchone()
            if not row: raise ValueError("Reproduction/replication project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM reproduction_replication_projects WHERE reproduction_replication_id=?",(rid,)).fetchone()
        if not row: raise ValueError("Reproduction/replication project not found.")
        return json.loads(row["record_json"])
    def create(self,req:ReproductionReplicationCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref")
        try: protocol=self._protocols().get(body["study_protocol_id"])
        except Exception as exc: raise ValueError("study_protocol_id is not available in Study Protocol & Preregistration Engine.") from exc
        stat=causal=sim=None
        if body.get("statistical_analysis_plan_id"):
            try: stat=self._stats().get(body["statistical_analysis_plan_id"])
            except Exception as exc: raise ValueError("statistical_analysis_plan_id is not available in Statistical Analysis Planning Intelligence.") from exc
            if stat.get("study_protocol_id")!=body["study_protocol_id"]: raise ValueError("statistical_analysis_plan_id does not belong to study_protocol_id.")
        if body.get("causal_design_id"):
            try: causal=self._causal().get(body["causal_design_id"])
            except Exception as exc: raise ValueError("causal_design_id is not available in Causal Research Design Intelligence.") from exc
            if body.get("statistical_analysis_plan_id") and causal.get("statistical_analysis_plan_id")!=body["statistical_analysis_plan_id"]: raise ValueError("causal_design_id does not belong to statistical_analysis_plan_id.")
        if body.get("simulation_study_id"):
            try: sim=self._simulation().get(body["simulation_study_id"])
            except Exception as exc: raise ValueError("simulation_study_id is not available in Simulation & Model Study Planner.") from exc
            if body.get("causal_design_id") and sim.get("causal_design_id")!=body["causal_design_id"]: raise ValueError("simulation_study_id does not belong to causal_design_id.")
        body["core_project_id"]=body.get("core_project_id") or protocol.get("core_project_id","")
        rid=_id("reprpl-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(rid)
        except ValueError: pass
        rec={"schema":REPRODUCTION_REPLICATION_SCHEMA,"reproduction_replication_id":rid,**body,
             "research_program_id":protocol.get("research_program_id",""),"protocol_fingerprint":protocol.get("record_hash",""),
             "statistical_plan_fingerprint":(stat or {}).get("record_hash",""),"causal_design_fingerprint":(causal or {}).get("record_hash",""),"simulation_study_fingerprint":(sim or {}).get("record_hash",""),
             "source_lineage":{"protocol_registration":protocol.get("registration",{}),"statistical_analysis_plan_id":body.get("statistical_analysis_plan_id",""),"causal_design_id":body.get("causal_design_id",""),"simulation_study_id":body.get("simulation_study_id","")},
             "reproduction_attempts":[],"replication_studies":[],"comparability_criteria":[],"environment_manifest":{},"deviations":[],"execution_receipts":[],"human_assessments":[],"decisions":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),
             "governance":{"reproduction_and_replication_are_distinct":True,"reproduction_output_match_does_not_establish_independent_replication":True,"replication_difference_does_not_automatically_falsify_source_claim":True,"human_outcome_assessment_required":True,"comparability_is_explicit_and_scope_bounded":True,"execution_receipts_are_observations_not_scholarly_verdicts":True,"specialist_runtimes_own_execution":True,"platform_core_remains_governed_research_object_authority":True,"automatic_replication_verdict":False,"automatic_reproduction_verdict":False,"automatic_claim_acceptance":False,"automatic_causal_inference":False,"automatic_execution":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(rid,"reproduction-replication.created",actor,{"study_protocol_id":body["study_protocol_id"],"source_study_ref":body["source_study_ref"]}); return self.get(rid)
    def _known(self,rec,key,idkey): return {x[idkey] for x in rec.get(key,[])}
    def _append(self,rid,key,idkey,prefix,body,event,extra=None):
        rec=self.get(rid); actor=body.pop("actor_ref"); oid=_id(prefix,body); item={idkey:oid,**body,**(extra or {}),"created_utc":_now()}
        if not any(x[idkey]==oid for x in rec[key]): rec[key].append(item); self._save(rec); self._event(rid,event,actor,{idkey:oid})
        return self.get(rid)
    def add_reproduction_attempt(self,rid,req:ReproductionAttemptAddRequest):
        return self._append(rid,"reproduction_attempts","reproduction_attempt_id","repro-",req.model_dump(),"reproduction-attempt.added",{"execution_performed":False,"output_match_not_assessed":True})
    def add_replication_study(self,rid,req:ReplicationStudyAddRequest):
        return self._append(rid,"replication_studies","replication_study_id","repstudy-",req.model_dump(),"replication-study.added",{"execution_performed":False,"replication_outcome_not_assessed":True})
    def add_comparability_criterion(self,rid,req:ComparabilityCriterionAddRequest):
        return self._append(rid,"comparability_criteria","comparability_criterion_id","compare-",req.model_dump(),"comparability-criterion.added",{"criterion_is_declared_not_automatically_satisfied":True})
    def set_environment_manifest(self,rid,req:ReproductionEnvironmentManifestRequest):
        rec=self.get(rid); body=req.model_dump(); actor=body.pop("actor_ref"); rec["environment_manifest"]={**body,"captured_utc":_now(),"environment_reconstructed":False}; self._save(rec); self._event(rid,"environment-manifest.updated",actor,body); return self.get(rid)
    def _target_exists(self,rec,typ,oid):
        maps={"reproduction-attempt":("reproduction_attempts","reproduction_attempt_id"),"replication-study":("replication_studies","replication_study_id")}; key,idkey=maps[typ]; return oid in self._known(rec,key,idkey)
    def add_deviation(self,rid,req:ReproductionReplicationDeviationAddRequest):
        rec=self.get(rid)
        if not self._target_exists(rec,req.target_type,req.target_id): raise ValueError("Deviation references an unknown target_id.")
        return self._append(rid,"deviations","deviation_id","rrdev-",req.model_dump(),"reproduction-replication.deviation-added",{"materiality_not_auto_judged":True})
    def add_execution_receipt(self,rid,req:ReproductionReplicationReceiptAddRequest):
        rec=self.get(rid)
        if not self._target_exists(rec,req.target_type,req.target_id): raise ValueError("Execution receipt references an unknown target_id.")
        return self._append(rid,"execution_receipts","execution_receipt_id","rrreceipt-",req.model_dump(),"reproduction-replication.execution-receipt-added",{"receipt_is_observation_not_verdict":True,"truth_not_promoted":True})
    def add_human_assessment(self,rid,req:ReproductionReplicationAssessmentRequest):
        rec=self.get(rid)
        if not self._target_exists(rec,req.target_type,req.target_id): raise ValueError("Assessment references an unknown target_id.")
        return self._append(rid,"human_assessments","assessment_id","rrassess-",req.model_dump(),"reproduction-replication.human-assessment-added",{"human_authored":True,"assessment_is_scope_bounded_not_global_truth":True})
    def decide(self,rid,req:ReproductionReplicationDecisionRequest):
        rec=self.get(rid); maps={"reproduction-attempt":("reproduction_attempts","reproduction_attempt_id"),"replication-study":("replication_studies","replication_study_id"),"comparability-criterion":("comparability_criteria","comparability_criterion_id")}; key,idkey=maps[req.object_type]
        if req.object_id not in self._known(rec,key,idkey): raise ValueError("Decision references an unknown object_id.")
        item={"object_type":req.object_type,"object_id":req.object_id,"decision":req.decision,"rationale":req.rationale,"actor_ref":req.actor_ref,"decided_utc":_now()}
        rec["decisions"]=[x for x in rec["decisions"] if not(x["object_type"]==req.object_type and x["object_id"]==req.object_id)]+[item]; self._save(rec); self._event(rid,"reproduction-replication-object.decision",req.actor_ref,item); return self.get(rid)
    def comparison_matrix(self,rid):
        rec=self.get(rid); decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["decisions"]}; assessments={(x["target_type"],x["target_id"]):x for x in rec["human_assessments"]}
        return {"schema":REPRODUCTION_REPLICATION_SCHEMA,"reproduction_replication_id":rid,
                "reproduction_attempts":[{"reproduction_attempt_id":x["reproduction_attempt_id"],"label":x["label"],"kind":x["kind"],"decision":decisions.get(("reproduction-attempt",x["reproduction_attempt_id"]),"pending"),"assessment":assessments.get(("reproduction-attempt",x["reproduction_attempt_id"]),{}).get("assessment","not-assessed")} for x in rec["reproduction_attempts"]],
                "replication_studies":[{"replication_study_id":x["replication_study_id"],"label":x["label"],"kind":x["kind"],"decision":decisions.get(("replication-study",x["replication_study_id"]),"pending"),"assessment":assessments.get(("replication-study",x["replication_study_id"]),{}).get("assessment","not-assessed")} for x in rec["replication_studies"]],
                "comparability_criteria":rec["comparability_criteria"],"deviations":rec["deviations"],"execution_receipts":rec["execution_receipts"],
                "governance":{"matrix_is_descriptive_comparison_not_automatic_replication_verdict":True}}
    def lineage_map(self,rid):
        rec=self.get(rid); nodes=[{"node_id":rec["study_protocol_id"],"kind":"study-protocol"}]; edges=[]
        for field,kind in [("statistical_analysis_plan_id","statistical-analysis-plan"),("causal_design_id","causal-research-design"),("simulation_study_id","simulation-model-study")]:
            if rec.get(field): nodes.append({"node_id":rec[field],"kind":kind}); edges.append({"source":rec["study_protocol_id"],"target":rec[field],"relation":"upstream-lineage"})
        for x in rec["reproduction_attempts"]: nodes.append({"node_id":x["reproduction_attempt_id"],"kind":"reproduction-attempt"}); edges.append({"source":rec["source_study_ref"],"target":x["reproduction_attempt_id"],"relation":"reproduces"})
        for x in rec["replication_studies"]: nodes.append({"node_id":x["replication_study_id"],"kind":"replication-study"}); edges.append({"source":rec["source_study_ref"],"target":x["replication_study_id"],"relation":"replicates"})
        return {"schema":"sc-research-librarian-reproduction-replication-lineage-map/1.0","reproduction_replication_id":rid,"source_study_ref":rec["source_study_ref"],"nodes":nodes,"edges":edges,"execution_performed":False,"outcome_inferred":False}
    def readiness(self,rid):
        rec=self.get(rid); blockers=[]; decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["decisions"]}
        if not rec["reproduction_attempts"] and not rec["replication_studies"]: blockers.append("no-reproduction-or-replication-work")
        for x in rec["reproduction_attempts"]:
            if decisions.get(("reproduction-attempt",x["reproduction_attempt_id"]),"pending")!="approved": blockers.append("reproduction-attempts-await-human-approval"); break
        for x in rec["replication_studies"]:
            if decisions.get(("replication-study",x["replication_study_id"]),"pending")!="approved": blockers.append("replication-studies-await-human-approval"); break
        if rec["replication_studies"] and not rec["comparability_criteria"]: blockers.append("no-comparability-criteria")
        if rec["reproduction_attempts"] and not rec["environment_manifest"]: blockers.append("no-environment-manifest")
        return {"schema":REPRODUCTION_REPLICATION_SCHEMA,"reproduction_replication_id":rid,"ready_for_execution_handoff":not blockers,"blockers":blockers,"dimensions":{"reproduction_attempts_declared":bool(rec["reproduction_attempts"]),"replication_studies_declared":bool(rec["replication_studies"]),"comparability_criteria_declared":bool(rec["comparability_criteria"]),"environment_manifest_declared":bool(rec["environment_manifest"]),"deviations_disclosed":bool(rec["deviations"]),"execution_receipts_recorded":bool(rec["execution_receipts"]),"human_assessments_recorded":bool(rec["human_assessments"])},"governance":{"readiness_is_structural_execution-readiness_not_replication_success":True,"automatic_execution":False,"automatic_verdict":False}}
    def runtime_handoffs(self,rid):
        rec=self.get(rid); ready=self.readiness(rid); decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["decisions"]}; packets=[]
        for x in rec["reproduction_attempts"]:
            if decisions.get(("reproduction-attempt",x["reproduction_attempt_id"]))=="approved": packets.append({"schema":"sc-research-librarian-reproduction-runtime-handoff/1.0","handoff_id":_id("rrhand-",{"rid":rid,"target":x["reproduction_attempt_id"]}),"target":x["runtime_target"],"secondary_targets":["workspace","research-lab"],"attempt":x,"environment_manifest":rec["environment_manifest"],"source_lineage":rec["source_lineage"],"deviations":[d for d in rec["deviations"] if d["target_type"]=="reproduction-attempt" and d["target_id"]==x["reproduction_attempt_id"]],"handoff_ready":ready["ready_for_execution_handoff"],"execution_performed":False,"reproduction_assessed":False})
        for x in rec["replication_studies"]:
            if decisions.get(("replication-study",x["replication_study_id"]))=="approved": packets.append({"schema":"sc-research-librarian-replication-runtime-handoff/1.0","handoff_id":_id("rrhand-",{"rid":rid,"target":x["replication_study_id"]}),"target":"research-lab","secondary_targets":["workspace","statistical-runtime"],"replication_study":x,"comparability_criteria":rec["comparability_criteria"],"source_lineage":rec["source_lineage"],"deviations":[d for d in rec["deviations"] if d["target_type"]=="replication-study" and d["target_id"]==x["replication_study_id"]],"handoff_ready":ready["ready_for_execution_handoff"],"execution_performed":False,"replication_assessed":False})
        return {"schema":REPRODUCTION_REPLICATION_SCHEMA,"reproduction_replication_id":rid,"packets":packets,"governance":{"handoffs_are_execution_inputs_not_reproduction_or_replication_verdicts":True,"specialist_runtimes_own_execution":True}}
    def core_candidate(self,rid):
        rec=self.get(rid); return {"schema":"sc-research-librarian-core-reproduction-replication-candidate/1.0","candidate_id":_id("corecand-",{"reproduction_replication_id":rid,"type":"reproduction-replication-plan"}),"object_type":"reproduction-replication-plan","source_reproduction_replication_id":rid,"payload":{"title":rec["title"],"source_study_ref":rec["source_study_ref"],"study_protocol_id":rec["study_protocol_id"],"reproduction_attempts":rec["reproduction_attempts"],"replication_studies":rec["replication_studies"],"comparability_criteria":rec["comparability_criteria"],"deviations":rec["deviations"],"execution_receipts":rec["execution_receipts"],"human_assessments":rec["human_assessments"],"record_hash":rec["record_hash"]},"promotion_performed":False,"execution_performed":False,"replication_verdict_generated":False,"truth_promoted":False,"governance":{"platform_core_remains_governed_research_object_authority":True}}
    def set_state(self,rid,req:ReproductionReplicationStateRequest):
        rec=self.get(rid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(rid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(rid)
    def freeze_snapshot(self,req:ReproductionReplicationSnapshotRequest):
        rec=self.get(req.reproduction_replication_id); payload={"schema":REPRODUCTION_REPLICATION_SNAPSHOT_SCHEMA,"reproduction_replication_id":req.reproduction_replication_id,"project":rec,"comparison_matrix":self.comparison_matrix(req.reproduction_replication_id),"lineage_map":self.lineage_map(req.reproduction_replication_id),"readiness":self.readiness(req.reproduction_replication_id),"runtime_handoffs":self.runtime_handoffs(req.reproduction_replication_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_reproduction-replication-record_not_success-or-truth-certification":True}}
        h=_sha(payload); sid="reprplsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_reproduction_replication_snapshots(snapshot_id,reproduction_replication_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.reproduction_replication_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO reproduction_replication_snapshots(snapshot_id,reproduction_replication_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.reproduction_replication_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.reproduction_replication_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities():
    return {"schema":REPRODUCTION_REPLICATION_SCHEMA,"release":settings.release_version,"milestone":"11.5","durable":True,"reproduction_replication_distinction":True,"study_protocol_lineage":True,"statistical_plan_lineage":True,"causal_design_lineage":True,"simulation_model_study_lineage":True,"reproduction_attempt_registry":True,"replication_study_registry":True,"comparability_criteria":True,"environment_manifest":True,"deviation_disclosure":True,"execution_receipts":True,"human_outcome_assessment":True,"comparison_matrix":True,"lineage_map":True,"runtime_handoffs":True,"human_execution_plan_approval_required":True,"specialist_runtimes_own_execution":True,"platform_core_remains_governed_research_object_authority":True,"automatic_reproduction_verdict":False,"automatic_replication_verdict":False,"automatic_claim_acceptance":False,"automatic_causal_inference":False,"automatic_execution":False,"automatic_truth_promotion":False}
_store=None
def get_reproduction_replication_intelligence_store():
    global _store
    if _store is None: _store=ReproductionReplicationIntelligenceStore()
    return _store
