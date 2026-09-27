from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.simulation_model_study_planner import *
from .causal_research_design_intelligence import get_causal_research_design_intelligence_store
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

class SimulationModelStudyPlannerStore:
    def __init__(self,sqlite_path:Path|None=None,causal_design_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"simulation_model_study_planner.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self.causal_design_store=causal_design_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres simulation/model study storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _causal(self): return self.causal_design_store or get_causal_research_design_intelligence_store()
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
CREATE TABLE IF NOT EXISTS simulation_model_studies(simulation_study_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS simulation_model_study_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,simulation_study_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS simulation_model_study_snapshots(snapshot_id TEXT PRIMARY KEY,simulation_study_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_simulation_model_studies(simulation_study_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_simulation_model_study_events(event_id BIGSERIAL PRIMARY KEY,simulation_study_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_simulation_model_study_events_study ON sc_rl_simulation_model_study_events(simulation_study_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_simulation_model_study_snapshots(snapshot_id TEXT PRIMARY KEY,simulation_study_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,sid,typ,actor,payload):
        created=_now(); h=_sha({"simulation_study_id":sid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_simulation_model_study_events(simulation_study_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(sid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO simulation_model_study_events(simulation_study_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(sid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_simulation_model_studies(simulation_study_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(simulation_study_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["simulation_study_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO simulation_model_studies(simulation_study_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["simulation_study_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,sid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_simulation_model_studies WHERE simulation_study_id=%s",(sid,)).fetchone()
            if not row: raise ValueError("Simulation/model study not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM simulation_model_studies WHERE simulation_study_id=?",(sid,)).fetchone()
        if not row: raise ValueError("Simulation/model study not found.")
        return json.loads(row["record_json"])
    def create(self,req:SimulationModelStudyCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref")
        try: causal=self._causal().get(body["causal_design_id"])
        except Exception as exc: raise ValueError("causal_design_id is not available in Causal Research Design Intelligence.") from exc
        body["core_project_id"]=body.get("core_project_id") or causal.get("core_project_id","")
        sid=_id("simstudy-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(sid)
        except ValueError: pass
        rec={"schema":SIMULATION_MODEL_STUDY_SCHEMA,"simulation_study_id":sid,**body,
             "statistical_analysis_plan_id":causal.get("statistical_analysis_plan_id",""),"study_protocol_id":causal.get("study_protocol_id",""),"research_program_id":causal.get("research_program_id",""),
             "causal_design_fingerprint":causal.get("record_hash","") ,"causal_design_summary":{"variable_roles":causal.get("variable_roles",[]),"identification_strategies":causal.get("identification_strategies",[]),"causal_assumptions":causal.get("causal_assumptions",[])},
             "model_specifications":[],"variables":[],"parameters":[],"scenario_sets":[],"stochastic_assumptions":[],"calibration_plans":[],"validation_plans":[],"uncertainty_plans":[],"sensitivity_plans":[],"ensemble_plans":[],"compute_budget":{},"stopping_criteria":[],"output_commitments":[],"study_decisions":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),
             "governance":{"simulation_study_is_prospective_model_plan_not_execution_or_empirical_fact":True,"causal_design_lineage_is_inherited_not_rewritten":True,"human_model_study_approval_required":True,"model_assumptions_and_scenarios_remain_explicit":True,"specialist_runtimes_own_simulation_execution":True,"platform_core_remains_governed_model_object_authority":True,"automatic_model_selection":False,"automatic_calibration":False,"automatic_validation":False,"automatic_simulation_execution":False,"automatic_forecast_acceptance":False,"automatic_causal_inference":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(sid,"simulation-model-study.created",actor,{"causal_design_id":body["causal_design_id"]}); return self.get(sid)
    def _known(self,rec,key,idkey): return {x[idkey] for x in rec.get(key,[])}
    def _append(self,sid,key,idkey,prefix,body,event,extra=None):
        rec=self.get(sid); actor=body.pop("actor_ref"); oid=_id(prefix,body); item={idkey:oid,**body,**(extra or {}),"created_utc":_now()}
        if not any(x[idkey]==oid for x in rec[key]): rec[key].append(item); self._save(rec); self._event(sid,event,actor,{idkey:oid})
        return self.get(sid)
    def add_model_specification(self,sid,req:SimulationModelSpecificationAddRequest):
        return self._append(sid,"model_specifications","model_specification_id","simmodel-",req.model_dump(),"model-specification.added",{"human_specified":True,"model_not_selected_automatically":True,"execution_not_performed":True})
    def add_variable(self,sid,req:SimulationVariableAddRequest):
        return self._append(sid,"variables","simulation_variable_id","simvar-",req.model_dump(),"simulation-variable.added",{"human_specified":True})
    def add_parameter(self,sid,req:SimulationParameterAddRequest):
        return self._append(sid,"parameters","simulation_parameter_id","simparam-",req.model_dump(),"simulation-parameter.added",{"human_specified":True})
    def _require_models(self,rec,ids):
        missing=set(ids)-self._known(rec,"model_specifications","model_specification_id")
        if missing: raise ValueError("Simulation plan references an unknown model_specification_id.")
    def add_scenario_set(self,sid,req:SimulationScenarioSetAddRequest):
        rec=self.get(sid); self._require_models(rec,req.model_specification_ids)
        return self._append(sid,"scenario_sets","scenario_set_id","scenario-",req.model_dump(),"scenario-set.added",{"scenario_results_not_computed":True})
    def add_stochastic_assumption(self,sid,req:SimulationStochasticAssumptionAddRequest):
        return self._append(sid,"stochastic_assumptions","stochastic_assumption_id","stoch-",req.model_dump(),"stochastic-assumption.added",{"distribution_not_fitted_or_sampled":True})
    def add_calibration_plan(self,sid,req:SimulationCalibrationPlanAddRequest):
        rec=self.get(sid); self._require_models(rec,req.model_specification_ids)
        return self._append(sid,"calibration_plans","calibration_plan_id","calib-",req.model_dump(),"calibration-plan.added",{"calibration_not_executed":True})
    def add_validation_plan(self,sid,req:SimulationValidationPlanAddRequest):
        rec=self.get(sid); self._require_models(rec,req.model_specification_ids)
        return self._append(sid,"validation_plans","validation_plan_id","valid-",req.model_dump(),"validation-plan.added",{"validation_not_executed":True,"model_validity_not_certified":True})
    def add_uncertainty_plan(self,sid,req:SimulationUncertaintyPlanAddRequest):
        return self._append(sid,"uncertainty_plans","uncertainty_plan_id","uncert-",req.model_dump(),"uncertainty-plan.added",{"uncertainty_not_computed":True})
    def add_sensitivity_plan(self,sid,req:SimulationSensitivityPlanAddRequest):
        rec=self.get(sid); missing=set(req.parameter_ids)-self._known(rec,"parameters","simulation_parameter_id")
        if missing: raise ValueError("Sensitivity plan references an unknown simulation_parameter_id.")
        return self._append(sid,"sensitivity_plans","sensitivity_plan_id","simsens-",req.model_dump(),"sensitivity-plan.added",{"sensitivity_not_computed":True})
    def add_ensemble_plan(self,sid,req:SimulationEnsemblePlanAddRequest):
        rec=self.get(sid); self._require_models(rec,req.model_specification_ids)
        return self._append(sid,"ensemble_plans","ensemble_plan_id","ensemble-",req.model_dump(),"ensemble-plan.added",{"weights_not_estimated":True,"ensemble_not_executed":True})
    def set_compute_budget(self,sid,req:SimulationComputeBudgetRequest):
        rec=self.get(sid); body=req.model_dump(); actor=body.pop("actor_ref"); rec["compute_budget"]={**body,"human_specified":True,"updated_utc":_now()}; self._save(rec); self._event(sid,"compute-budget.updated",actor,body); return self.get(sid)
    def add_stopping_criterion(self,sid,req:SimulationStoppingCriterionAddRequest):
        return self._append(sid,"stopping_criteria","stopping_criterion_id","stop-",req.model_dump(),"stopping-criterion.added",{"human_specified":True})
    def add_output_commitment(self,sid,req:SimulationOutputCommitmentAddRequest):
        return self._append(sid,"output_commitments","output_commitment_id","simout-",req.model_dump(),"output-commitment.added",{"result_not_computed":True})
    def _object_exists(self,rec,typ,oid):
        maps={"model-specification":("model_specifications","model_specification_id"),"scenario-set":("scenario_sets","scenario_set_id"),"calibration-plan":("calibration_plans","calibration_plan_id"),"validation-plan":("validation_plans","validation_plan_id"),"uncertainty-plan":("uncertainty_plans","uncertainty_plan_id"),"sensitivity-plan":("sensitivity_plans","sensitivity_plan_id"),"ensemble-plan":("ensemble_plans","ensemble_plan_id")}
        key,idkey=maps[typ]; return oid in self._known(rec,key,idkey)
    def decide(self,sid,req:SimulationStudyDecisionRequest):
        rec=self.get(sid)
        if not self._object_exists(rec,req.object_type,req.object_id): raise ValueError("Simulation study decision references an unknown object_id.")
        item={"object_type":req.object_type,"object_id":req.object_id,"decision":req.decision,"rationale":req.rationale,"actor_ref":req.actor_ref,"decided_utc":_now()}
        rec["study_decisions"]=[x for x in rec["study_decisions"] if not(x["object_type"]==req.object_type and x["object_id"]==req.object_id)]+[item]; self._save(rec); self._event(sid,"simulation-study-object.decision",req.actor_ref,item); return self.get(sid)
    def study_matrix(self,sid):
        rec=self.get(sid); decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["study_decisions"]}
        return {"schema":SIMULATION_MODEL_STUDY_SCHEMA,"simulation_study_id":sid,"models":[{"model_specification_id":x["model_specification_id"],"label":x["label"],"model_class":x["model_class"],"preferred_runtime":x["preferred_runtime"],"decision":decisions.get(("model-specification",x["model_specification_id"]),"pending")} for x in rec["model_specifications"]],"scenario_sets":rec["scenario_sets"],"calibration_plans":rec["calibration_plans"],"validation_plans":rec["validation_plans"],"uncertainty_plans":rec["uncertainty_plans"],"sensitivity_plans":rec["sensitivity_plans"],"ensemble_plans":rec["ensemble_plans"],"output_commitments":rec["output_commitments"],"governance":{"matrix_is_planning_view_not_model_ranking_or_result":True}}
    def execution_graph(self,sid):
        rec=self.get(sid); nodes=[]; edges=[]
        for m in rec["model_specifications"]: nodes.append({"node_id":m["model_specification_id"],"kind":"model-specification","label":m["label"]})
        for s in rec["scenario_sets"]:
            nodes.append({"node_id":s["scenario_set_id"],"kind":"scenario-set","label":s["label"]})
            for m in s["model_specification_ids"]: edges.append({"source":m,"target":s["scenario_set_id"],"relation":"evaluated-under"})
        for p in rec["calibration_plans"]+rec["validation_plans"]:
            oid=p.get("calibration_plan_id") or p.get("validation_plan_id"); nodes.append({"node_id":oid,"kind":"calibration-plan" if "calibration_plan_id" in p else "validation-plan","label":p["label"]})
            for m in p["model_specification_ids"]: edges.append({"source":m,"target":oid,"relation":"uses"})
        return {"schema":"sc-research-librarian-simulation-execution-graph/1.0","simulation_study_id":sid,"nodes":nodes,"edges":edges,"execution_performed":False}
    def readiness(self,sid):
        rec=self.get(sid); blockers=[]; decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["study_decisions"]}
        if not rec["model_specifications"]: blockers.append("no-model-specifications")
        if rec["model_specifications"] and any(decisions.get(("model-specification",x["model_specification_id"]),"pending")!="approved" for x in rec["model_specifications"]): blockers.append("model-specifications-await-human-approval")
        if not rec["scenario_sets"]: blockers.append("no-scenario-sets")
        if not rec["validation_plans"]: blockers.append("no-validation-plans")
        if not rec["compute_budget"]: blockers.append("no-compute-budget")
        if not rec["output_commitments"]: blockers.append("no-output-commitments")
        return {"schema":SIMULATION_MODEL_STUDY_SCHEMA,"simulation_study_id":sid,"ready_for_simulation_handoff":not blockers,"blockers":blockers,"dimensions":{"models_declared":bool(rec["model_specifications"]),"models_human_approved":bool(rec["model_specifications"]) and all(decisions.get(("model-specification",x["model_specification_id"]))=="approved" for x in rec["model_specifications"]),"variables_declared":bool(rec["variables"]),"parameters_declared":bool(rec["parameters"]),"scenarios_declared":bool(rec["scenario_sets"]),"calibration_plans_declared":bool(rec["calibration_plans"]),"validation_plans_declared":bool(rec["validation_plans"]),"uncertainty_plans_declared":bool(rec["uncertainty_plans"]),"sensitivity_plans_declared":bool(rec["sensitivity_plans"]),"ensemble_plans_declared":bool(rec["ensemble_plans"]),"compute_budget_declared":bool(rec["compute_budget"]),"stopping_criteria_declared":bool(rec["stopping_criteria"]),"output_commitments_declared":bool(rec["output_commitments"])},"governance":{"readiness_is_structural_model-study-completeness_not_model_validity_or_result_quality":True,"automatic_execution":False}}
    def runtime_handoffs(self,sid):
        rec=self.get(sid); ready=self.readiness(sid); decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["study_decisions"]}; approved=[x for x in rec["model_specifications"] if decisions.get(("model-specification",x["model_specification_id"]))=="approved"]
        packets=[]
        for m in approved:
            packets.append({"schema":"sc-research-librarian-simulation-runtime-handoff/1.0","handoff_id":_id("simhand-",{"study":sid,"model":m["model_specification_id"]}),"target":"research-lab-simulation","secondary_targets":["workspace","workbench"],"preferred_runtime":m["preferred_runtime"],"model_specification":m,"variables":rec["variables"],"parameters":rec["parameters"],"scenario_sets":[x for x in rec["scenario_sets"] if m["model_specification_id"] in x["model_specification_ids"]],"stochastic_assumptions":rec["stochastic_assumptions"],"calibration_plans":[x for x in rec["calibration_plans"] if m["model_specification_id"] in x["model_specification_ids"]],"validation_plans":[x for x in rec["validation_plans"] if m["model_specification_id"] in x["model_specification_ids"]],"uncertainty_plans":rec["uncertainty_plans"],"sensitivity_plans":rec["sensitivity_plans"],"ensemble_plans":[x for x in rec["ensemble_plans"] if m["model_specification_id"] in x["model_specification_ids"]],"compute_budget":rec["compute_budget"],"stopping_criteria":rec["stopping_criteria"],"output_commitments":rec["output_commitments"],"causal_design_id":rec["causal_design_id"],"handoff_ready":ready["ready_for_simulation_handoff"],"execution_performed":False,"calibration_performed":False,"validation_performed":False,"model_output_accepted_as_empirical_truth":False})
        return {"schema":SIMULATION_MODEL_STUDY_SCHEMA,"simulation_study_id":sid,"packets":packets,"governance":{"handoffs_are_execution_inputs_not_simulation_results":True,"specialist_runtimes_own_execution":True}}
    def core_candidate(self,sid):
        rec=self.get(sid); return {"schema":"sc-research-librarian-core-simulation-model-study-candidate/1.0","candidate_id":_id("corecand-",{"simulation_study_id":sid,"type":"simulation-model-study"}),"object_type":"simulation-model-study","source_simulation_study_id":sid,"payload":{"title":rec["title"],"causal_design_id":rec["causal_design_id"],"model_specifications":rec["model_specifications"],"scenario_sets":rec["scenario_sets"],"calibration_plans":rec["calibration_plans"],"validation_plans":rec["validation_plans"],"uncertainty_plans":rec["uncertainty_plans"],"sensitivity_plans":rec["sensitivity_plans"],"ensemble_plans":rec["ensemble_plans"],"compute_budget":rec["compute_budget"],"output_commitments":rec["output_commitments"],"record_hash":rec["record_hash"]},"promotion_performed":False,"execution_performed":False,"model_validity_certified":False,"truth_promoted":False,"governance":{"platform_core_remains_governed_model_object_authority":True}}
    def set_state(self,sid,req:SimulationModelStudyStateRequest):
        rec=self.get(sid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(sid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(sid)
    def freeze_snapshot(self,req:SimulationModelStudySnapshotRequest):
        rec=self.get(req.simulation_study_id); payload={"schema":SIMULATION_MODEL_STUDY_SNAPSHOT_SCHEMA,"simulation_study_id":req.simulation_study_id,"study":rec,"study_matrix":self.study_matrix(req.simulation_study_id),"execution_graph":self.execution_graph(req.simulation_study_id),"readiness":self.readiness(req.simulation_study_id),"runtime_handoffs":self.runtime_handoffs(req.simulation_study_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_model-study-plan_not_model-result-or-validity-certification":True}}
        h=_sha(payload); snap="simstudysnap-"+h[:32]; payload.update({"snapshot_id":snap,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_simulation_model_study_snapshots(snapshot_id,simulation_study_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(snap,req.simulation_study_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO simulation_model_study_snapshots(snapshot_id,simulation_study_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(snap,req.simulation_study_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.simulation_study_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":snap,"snapshot_hash":h}); return payload

def capabilities():
    return {"schema":SIMULATION_MODEL_STUDY_SCHEMA,"release":settings.release_version,"milestone":"11.4","durable":True,"causal_design_lineage":True,"model_specification_registry":True,"variable_registry":True,"parameter_registry":True,"scenario_set_registry":True,"stochastic_assumption_registry":True,"calibration_planning":True,"validation_planning":True,"uncertainty_planning":True,"sensitivity_planning":True,"ensemble_planning":True,"compute_budget_planning":True,"stopping_criteria":True,"output_commitments":True,"study_matrix":True,"execution_graph":True,"runtime_handoffs":True,"human_model_study_approval_required":True,"specialist_runtimes_own_simulation_execution":True,"platform_core_remains_governed_model_object_authority":True,"automatic_model_selection":False,"automatic_calibration":False,"automatic_validation":False,"automatic_simulation_execution":False,"automatic_forecast_acceptance":False,"automatic_causal_inference":False,"automatic_truth_promotion":False}
_store=None
def get_simulation_model_study_planner_store():
    global _store
    if _store is None: _store=SimulationModelStudyPlannerStore()
    return _store
