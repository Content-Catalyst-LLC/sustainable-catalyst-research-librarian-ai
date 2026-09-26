from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.statistical_analysis_planning_intelligence import *
from .study_protocol_preregistration import get_study_protocol_preregistration_store
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

class StatisticalAnalysisPlanningIntelligenceStore:
    def __init__(self,sqlite_path:Path|None=None,study_protocol_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"statistical_analysis_planning_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self.study_protocol_store=study_protocol_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres statistical analysis planning storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _protocols(self): return self.study_protocol_store or get_study_protocol_preregistration_store()
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
CREATE TABLE IF NOT EXISTS statistical_analysis_planning(statistical_analysis_plan_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS statistical_analysis_planning_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,statistical_analysis_plan_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS statistical_analysis_planning_snapshots(snapshot_id TEXT PRIMARY KEY,statistical_analysis_plan_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_statistical_analysis_planning(statistical_analysis_plan_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_statistical_analysis_planning_events(event_id BIGSERIAL PRIMARY KEY,statistical_analysis_plan_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_statistical_analysis_planning_events_plan ON sc_rl_statistical_analysis_planning_events(statistical_analysis_plan_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_statistical_analysis_planning_snapshots(snapshot_id TEXT PRIMARY KEY,statistical_analysis_plan_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,pid,typ,actor,payload):
        created=_now(); h=_sha({"statistical_analysis_plan_id":pid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_statistical_analysis_planning_events(statistical_analysis_plan_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(pid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO statistical_analysis_planning_events(statistical_analysis_plan_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(pid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_statistical_analysis_planning(statistical_analysis_plan_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(statistical_analysis_plan_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["statistical_analysis_plan_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO statistical_analysis_planning(statistical_analysis_plan_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["statistical_analysis_plan_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,pid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_statistical_analysis_planning WHERE statistical_analysis_plan_id=%s",(pid,)).fetchone()
            if not row: raise ValueError("Statistical analysis planning record not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM statistical_analysis_planning WHERE statistical_analysis_plan_id=?",(pid,)).fetchone()
        if not row: raise ValueError("Statistical analysis planning record not found.")
        return json.loads(row["record_json"])
    def create(self,req:StatisticalAnalysisPlanningCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref")
        try: protocol=self._protocols().get(body["study_protocol_id"])
        except Exception as exc: raise ValueError("study_protocol_id is not available in Study Protocol & Preregistration Engine.") from exc
        body["core_project_id"]=body.get("core_project_id") or protocol.get("core_project_id","")
        if not body.get("computational_plan_id"):
            body["computational_plan_id"]=next((x.get("computational_plan_id","") for x in protocol.get("analysis_commitments",[]) if x.get("computational_plan_id")),"")
        pid=_id("statplan-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(pid)
        except ValueError: pass
        rec={"schema":STATISTICAL_ANALYSIS_PLANNING_SCHEMA,"statistical_analysis_plan_id":pid,**body,
             "research_program_id":protocol.get("research_program_id",""),"protocol_fingerprint":protocol.get("record_hash",""),
             "preregistration_baseline_snapshot_hash":protocol.get("registration",{}).get("baseline_snapshot_hash",""),
             "protocol_registration_status":protocol.get("registration",{}).get("status","not-preregistered"),
             "protocol_hypotheses":protocol.get("hypotheses",[]),"protocol_outcomes":protocol.get("outcomes",[]),"protocol_variables":protocol.get("variables",[]),
             "protocol_sampling_plan":protocol.get("sampling_plan"),"protocol_analysis_commitments":protocol.get("analysis_commitments",[]),
             "estimands":[],"model_specifications":[],"assumption_checks":[],"power_sample_size_plan":None,"multiplicity_plan":None,"missing_data_plan":None,
             "sensitivity_analyses":[],"reporting_commitments":[],"analysis_decisions":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),
             "governance":{"plan_is_prospective_statistical_specification_not_analysis_result":True,"preregistered_protocol_lineage_is_inherited_not_rewritten":True,
             "human_statistical_approval_required":True,"specialist_runtimes_own_statistical_execution":True,"existing_statistical_research_layer_remains_runtime_core_bridge":True,
             "platform_core_remains_statistical_reasoning_authority":True,"automatic_method_selection":False,"automatic_model_selection":False,"automatic_power_calculation":False,
             "automatic_significance_inference":False,"automatic_causality_inference":False,"automatic_result_interpretation":False,"automatic_execution":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(pid,"statistical-analysis-plan.created",actor,{"study_protocol_id":body["study_protocol_id"]}); return self.get(pid)
    def _known(self,rec,key,idkey): return {x[idkey] for x in rec.get(key,[])}
    def add_estimand(self,pid,req:StatisticalEstimandAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref")
        for k in ["protocol_hypothesis_ids","protocol_outcome_ids","protocol_variable_ids"]: body[k]=_uniq(body[k])
        known_h={x.get("hypothesis_id") for x in rec["protocol_hypotheses"]}; known_o={x.get("outcome_id") for x in rec["protocol_outcomes"]}; known_v={x.get("variable_id") for x in rec["protocol_variables"]}
        if any(x not in known_h for x in body["protocol_hypothesis_ids"]): raise ValueError("Estimand references an unknown protocol_hypothesis_id.")
        if any(x not in known_o for x in body["protocol_outcome_ids"]): raise ValueError("Estimand references an unknown protocol_outcome_id.")
        if any(x not in known_v for x in body["protocol_variable_ids"]): raise ValueError("Estimand references an unknown protocol_variable_id.")
        eid=_id("estimand-",body); item={"estimand_id":eid,**body,"human_specified":True,"estimate_not_computed":True,"created_utc":_now()}
        if not any(x["estimand_id"]==eid for x in rec["estimands"]): rec["estimands"].append(item); self._save(rec); self._event(pid,"estimand.added",actor,{"estimand_id":eid})
        return self.get(pid)
    def add_model_specification(self,pid,req:StatisticalModelSpecificationAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref")
        for k in ["estimand_ids","outcome_variable_refs","predictor_variable_refs","covariate_variable_refs","interaction_terms","computational_plan_step_ids"]: body[k]=_uniq(body[k])
        known=self._known(rec,"estimands","estimand_id")
        if any(x not in known for x in body["estimand_ids"]): raise ValueError("Model specification references an unknown estimand_id.")
        mid=_id("modelspec-",body); item={"model_specification_id":mid,**body,"human_specified":True,"fit_not_executed":True,"created_utc":_now()}
        if not any(x["model_specification_id"]==mid for x in rec["model_specifications"]): rec["model_specifications"].append(item); self._save(rec); self._event(pid,"model-specification.added",actor,{"model_specification_id":mid})
        return self.get(pid)
    def add_assumption_check(self,pid,req:StatisticalAssumptionCheckAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["model_specification_ids"]=_uniq(body["model_specification_ids"])
        known=self._known(rec,"model_specifications","model_specification_id")
        if any(x not in known for x in body["model_specification_ids"]): raise ValueError("Assumption check references an unknown model_specification_id.")
        aid=_id("assumptioncheck-",body); item={"assumption_check_id":aid,**body,"human_specified":True,"diagnostic_not_executed":True,"created_utc":_now()}
        if not any(x["assumption_check_id"]==aid for x in rec["assumption_checks"]): rec["assumption_checks"].append(item); self._save(rec); self._event(pid,"assumption-check.added",actor,{"assumption_check_id":aid})
        return self.get(pid)
    def set_power_sample_size_plan(self,pid,req:StatisticalPowerSampleSizePlanRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); sid=_id("powersize-",body); rec["power_sample_size_plan"]={"power_sample_size_plan_id":sid,**body,"human_specified":True,"calculation_not_performed_by_librarian":True,"created_utc":_now()}; self._save(rec); self._event(pid,"power-sample-size-plan.set",actor,{"power_sample_size_plan_id":sid}); return self.get(pid)
    def set_multiplicity_plan(self,pid,req:StatisticalMultiplicityPlanRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["hypothesis_or_estimand_ids"]=_uniq(body["hypothesis_or_estimand_ids"]); mid=_id("multiplicity-",body); rec["multiplicity_plan"]={"multiplicity_plan_id":mid,**body,"human_specified":True,"procedure_not_executed":True,"created_utc":_now()}; self._save(rec); self._event(pid,"multiplicity-plan.set",actor,{"multiplicity_plan_id":mid}); return self.get(pid)
    def set_missing_data_plan(self,pid,req:StatisticalMissingDataPlanRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["variables_or_outcomes"]=_uniq(body["variables_or_outcomes"]); body["missingness_assumptions"]=_uniq(body["missingness_assumptions"]); body["diagnostics"]=_uniq(body["diagnostics"]); mid=_id("missingdata-",body); rec["missing_data_plan"]={"missing_data_plan_id":mid,**body,"human_specified":True,"imputation_or_weighting_not_executed":True,"created_utc":_now()}; self._save(rec); self._event(pid,"missing-data-plan.set",actor,{"missing_data_plan_id":mid}); return self.get(pid)
    def add_sensitivity_analysis(self,pid,req:StatisticalSensitivityAnalysisAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["target_estimand_ids"]=_uniq(body["target_estimand_ids"]); body["target_model_specification_ids"]=_uniq(body["target_model_specification_ids"])
        if any(x not in self._known(rec,"estimands","estimand_id") for x in body["target_estimand_ids"]): raise ValueError("Sensitivity analysis references an unknown estimand_id.")
        if any(x not in self._known(rec,"model_specifications","model_specification_id") for x in body["target_model_specification_ids"]): raise ValueError("Sensitivity analysis references an unknown model_specification_id.")
        sid=_id("sensitivity-",body); item={"sensitivity_analysis_id":sid,**body,"human_specified":True,"analysis_not_executed":True,"created_utc":_now()}
        if not any(x["sensitivity_analysis_id"]==sid for x in rec["sensitivity_analyses"]): rec["sensitivity_analyses"].append(item); self._save(rec); self._event(pid,"sensitivity-analysis.added",actor,{"sensitivity_analysis_id":sid})
        return self.get(pid)
    def add_reporting_commitment(self,pid,req:StatisticalReportingCommitmentAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["required_outputs"]=_uniq(body["required_outputs"]); rid=_id("reportcommit-",body); item={"reporting_commitment_id":rid,**body,"human_specified":True,"created_utc":_now()}
        if not any(x["reporting_commitment_id"]==rid for x in rec["reporting_commitments"]): rec["reporting_commitments"].append(item); self._save(rec); self._event(pid,"reporting-commitment.added",actor,{"reporting_commitment_id":rid})
        return self.get(pid)
    def _object_exists(self,rec,typ,oid):
        if typ=="model-specification": return oid in self._known(rec,"model_specifications","model_specification_id")
        if typ=="power-sample-size-plan": return bool(rec.get("power_sample_size_plan")) and rec["power_sample_size_plan"]["power_sample_size_plan_id"]==oid
        if typ=="multiplicity-plan": return bool(rec.get("multiplicity_plan")) and rec["multiplicity_plan"]["multiplicity_plan_id"]==oid
        if typ=="missing-data-plan": return bool(rec.get("missing_data_plan")) and rec["missing_data_plan"]["missing_data_plan_id"]==oid
        if typ=="sensitivity-analysis": return oid in self._known(rec,"sensitivity_analyses","sensitivity_analysis_id")
        if typ=="reporting-commitment": return oid in self._known(rec,"reporting_commitments","reporting_commitment_id")
        return False
    def decide(self,pid,req:StatisticalAnalysisDecisionRequest):
        rec=self.get(pid)
        if not self._object_exists(rec,req.object_type,req.object_id): raise ValueError("Statistical analysis decision references an unknown object_id.")
        item={"object_type":req.object_type,"object_id":req.object_id,"decision":req.decision,"rationale":req.rationale,"actor_ref":req.actor_ref,"decided_utc":_now()}
        rec["analysis_decisions"]=[x for x in rec["analysis_decisions"] if not(x["object_type"]==req.object_type and x["object_id"]==req.object_id)]+[item]; self._save(rec); self._event(pid,"analysis-object.decision",req.actor_ref,item); return self.get(pid)
    def analysis_matrix(self,pid):
        rec=self.get(pid); decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["analysis_decisions"]}; rows=[]
        for m in rec["model_specifications"]:
            rows.append({"object_type":"model-specification","object_id":m["model_specification_id"],"label":m["label"],"estimand_ids":m["estimand_ids"],"method":m["method"],"model_family":m["model_family"],"decision":decisions.get(("model-specification",m["model_specification_id"]),"pending")})
        return {"schema":STATISTICAL_ANALYSIS_PLANNING_SCHEMA,"statistical_analysis_plan_id":pid,"rows":rows,"assumption_checks":rec["assumption_checks"],"governance":{"matrix_is_planned_analysis_structure_not_results_or_method_ranking":True}}
    def readiness(self,pid):
        rec=self.get(pid); blockers=[]; decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["analysis_decisions"]}
        if rec["protocol_registration_status"]!="preregistered": blockers.append("study-protocol-not-preregistered")
        if not rec["estimands"]: blockers.append("no-estimands")
        if not rec["model_specifications"]: blockers.append("no-model-specifications")
        if not rec["assumption_checks"]: blockers.append("no-assumption-checks")
        if rec["model_specifications"] and any(decisions.get(("model-specification",x["model_specification_id"]),"pending")!="approved" for x in rec["model_specifications"]): blockers.append("model-specifications-await-human-approval")
        if not rec["reporting_commitments"]: blockers.append("no-reporting-commitments")
        return {"schema":STATISTICAL_ANALYSIS_PLANNING_SCHEMA,"statistical_analysis_plan_id":pid,"ready_for_statistical_handoff":not blockers,"blockers":blockers,"dimensions":{"preregistered_protocol_bound":rec["protocol_registration_status"]=="preregistered","estimands_declared":bool(rec["estimands"]),"model_specifications_declared":bool(rec["model_specifications"]),"assumption_checks_declared":bool(rec["assumption_checks"]),"model_specifications_human_approved":bool(rec["model_specifications"]) and all(decisions.get(("model-specification",x["model_specification_id"]))=="approved" for x in rec["model_specifications"]),"power_sample_size_plan_declared":bool(rec["power_sample_size_plan"]),"multiplicity_plan_declared":bool(rec["multiplicity_plan"]),"missing_data_plan_declared":bool(rec["missing_data_plan"]),"sensitivity_analyses_declared":bool(rec["sensitivity_analyses"]),"reporting_commitments_declared":bool(rec["reporting_commitments"])},"governance":{"readiness_is_structural_planning_completeness_not_statistical_or_scientific_validity":True,"automatic_execution":False}}
    def runtime_handoffs(self,pid):
        rec=self.get(pid); ready=self.readiness(pid); decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["analysis_decisions"]}; approved=[x for x in rec["model_specifications"] if decisions.get(("model-specification",x["model_specification_id"]))=="approved"]
        return {"schema":STATISTICAL_ANALYSIS_PLANNING_SCHEMA,"statistical_analysis_plan_id":pid,"packets":[{"schema":"sc-research-librarian-statistical-runtime-handoff/1.0","handoff_id":_id("stathand-",{"plan":pid,"model":m["model_specification_id"]}),"target":"statistical-analysis-plan","preferred_runtime":"catalyst-analytics-r","existing_statistical_research_bridge":"v8.11","model_specification":m,"estimands":[e for e in rec["estimands"] if e["estimand_id"] in m["estimand_ids"]],"assumption_checks":[a for a in rec["assumption_checks"] if not a["model_specification_ids"] or m["model_specification_id"] in a["model_specification_ids"]],"power_sample_size_plan":rec["power_sample_size_plan"],"multiplicity_plan":rec["multiplicity_plan"],"missing_data_plan":rec["missing_data_plan"],"sensitivity_analyses":rec["sensitivity_analyses"],"reporting_commitments":rec["reporting_commitments"],"computational_plan_id":rec["computational_plan_id"],"handoff_ready":ready["ready_for_statistical_handoff"],"execution_performed":False,"method_selection_performed":False,"significance_inference_performed":False} for m in approved],"governance":{"handoffs_are_execution_inputs_not_results":True,"specialist_runtimes_own_execution":True,"existing_statistical_research_layer_remains_runtime_core_bridge":True}}
    def core_candidate(self,pid):
        rec=self.get(pid)
        return {"schema":"sc-research-librarian-core-statistical-analysis-plan-candidate/1.0","candidate_id":_id("corecand-",{"statistical_analysis_plan_id":pid,"type":"statistical-analysis-plan"}),"object_type":"statistical-analysis-plan","source_statistical_analysis_plan_id":pid,"payload":{"title":rec["title"],"study_protocol_id":rec["study_protocol_id"],"preregistration_baseline_snapshot_hash":rec["preregistration_baseline_snapshot_hash"],"estimands":rec["estimands"],"model_specifications":rec["model_specifications"],"assumption_checks":rec["assumption_checks"],"power_sample_size_plan":rec["power_sample_size_plan"],"multiplicity_plan":rec["multiplicity_plan"],"missing_data_plan":rec["missing_data_plan"],"sensitivity_analyses":rec["sensitivity_analyses"],"reporting_commitments":rec["reporting_commitments"],"analysis_decisions":rec["analysis_decisions"]},"handoff_status":"approved-candidate" if self.readiness(pid)["ready_for_statistical_handoff"] else "draft-candidate","promotion_performed":False,"execution_performed":False,"governance":{"platform_core_remains_statistical_reasoning_authority":True,"candidate_is_not_promoted_object":True,"plan_is_not_analysis_result":True}}
    def set_state(self,pid,req:StatisticalAnalysisPlanningStateRequest):
        rec=self.get(pid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(pid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(pid)
    def freeze_snapshot(self,req:StatisticalAnalysisPlanningSnapshotRequest):
        rec=self.get(req.statistical_analysis_plan_id); payload={"schema":STATISTICAL_ANALYSIS_PLANNING_SNAPSHOT_SCHEMA,"statistical_analysis_plan_id":req.statistical_analysis_plan_id,"plan":rec,"analysis_matrix":self.analysis_matrix(req.statistical_analysis_plan_id),"readiness":self.readiness(req.statistical_analysis_plan_id),"runtime_handoffs":self.runtime_handoffs(req.statistical_analysis_plan_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_analysis_plan_not_results_or_validity_certification":True}}
        h=_sha(payload); sid="statplansnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_statistical_analysis_planning_snapshots(snapshot_id,statistical_analysis_plan_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.statistical_analysis_plan_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO statistical_analysis_planning_snapshots(snapshot_id,statistical_analysis_plan_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.statistical_analysis_plan_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.statistical_analysis_plan_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities():
    return {"schema":STATISTICAL_ANALYSIS_PLANNING_SCHEMA,"release":settings.release_version,"milestone":"11.2","durable":True,"study_protocol_lineage":True,"estimand_registry":True,"model_specification_registry":True,"assumption_check_registry":True,"power_and_sample_size_planning":True,"multiplicity_planning":True,"missing_data_planning":True,"sensitivity_analysis_registry":True,"reporting_commitments":True,"analysis_matrix":True,"runtime_handoffs":True,"human_statistical_approval_required":True,"preregistered_protocol_lineage_is_inherited_not_rewritten":True,"specialist_runtimes_own_statistical_execution":True,"existing_statistical_research_layer_remains_runtime_core_bridge":True,"platform_core_remains_statistical_reasoning_authority":True,"automatic_method_selection":False,"automatic_model_selection":False,"automatic_power_calculation":False,"automatic_significance_inference":False,"automatic_causality_inference":False,"automatic_result_interpretation":False,"automatic_execution":False,"automatic_truth_promotion":False}
_store=None
def get_statistical_analysis_planning_intelligence_store():
    global _store
    if _store is None: _store=StatisticalAnalysisPlanningIntelligenceStore()
    return _store
