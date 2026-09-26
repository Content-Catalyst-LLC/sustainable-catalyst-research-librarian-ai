from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.computational_research_planning import *
from .dataset_discovery_data_fitness import get_dataset_discovery_data_fitness_store
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

class ComputationalResearchPlanningStore:
    def __init__(self,sqlite_path:Path|None=None,dataset_fitness_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"computational_research_planning.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self.dataset_fitness_store=dataset_fitness_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres computational research planning storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _fitness(self): return self.dataset_fitness_store or get_dataset_discovery_data_fitness_store()
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
CREATE TABLE IF NOT EXISTS computational_research_plans(computational_plan_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS computational_research_plan_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,computational_plan_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS computational_research_plan_snapshots(snapshot_id TEXT PRIMARY KEY,computational_plan_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_computational_research_plans(computational_plan_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_computational_research_plan_events(event_id BIGSERIAL PRIMARY KEY,computational_plan_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_computational_research_plan_events_project ON sc_rl_computational_research_plan_events(computational_plan_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_computational_research_plan_snapshots(snapshot_id TEXT PRIMARY KEY,computational_plan_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,pid,typ,actor,payload):
        created=_now(); h=_sha({"computational_plan_id":pid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_computational_research_plan_events(computational_plan_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(pid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO computational_research_plan_events(computational_plan_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(pid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_computational_research_plans(computational_plan_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(computational_plan_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["computational_plan_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO computational_research_plans(computational_plan_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["computational_plan_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,pid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_computational_research_plans WHERE computational_plan_id=%s",(pid,)).fetchone()
            if not row: raise ValueError("Computational research plan not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM computational_research_plans WHERE computational_plan_id=?",(pid,)).fetchone()
        if not row: raise ValueError("Computational research plan not found.")
        return json.loads(row["record_json"])
    def create(self,req:ComputationalResearchPlanCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref"); upstream={}
        if body.get("data_fitness_id"):
            upstream=self._fitness().get(body["data_fitness_id"]); body["research_question"]=body.get("research_question") or upstream.get("research_question",""); body["core_project_id"]=body.get("core_project_id") or upstream.get("core_project_id","")
            known={x.get("dataset_id") for x in upstream.get("dataset_candidates",[])}; missing=[x for x in body["dataset_ids"] if x not in known]
            if missing: raise ValueError("One or more dataset_ids are not present in the bound data-fitness project.")
        body["dataset_ids"]=_uniq(body["dataset_ids"]); pid=_id("compplan-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(pid)
        except ValueError: pass
        accepted=set()
        for a in upstream.get("fitness_assessments",[]) if upstream else []:
            if a.get("decision") in {"fit","fit-with-limitations"}: accepted.add(a.get("dataset_id"))
        rec={"schema":COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA,"computational_plan_id":pid,**body,"data_fitness_fingerprint":upstream.get("record_hash","") if upstream else "","human_accepted_dataset_ids":sorted(x for x in accepted if x),"runtime_targets":[],"analysis_steps":[],"step_decisions":[],"reproducibility_requirements":[],"constraints":[],"review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),"governance":{"plan_is_candidate_execution_specification_not_execution":True,"human_method_and_runtime_approval_required":True,"upstream_dataset_fitness_is_inherited_not_rejudged":True,"specialist_runtimes_own_execution":True,"automatic_method_selection":False,"automatic_runtime_selection":False,"automatic_execution":False,"automatic_result_interpretation":False,"automatic_truth_promotion":False,"platform_core_remains_research_object_authority":True}}
        self._save(rec); self._event(pid,"computational-plan.created",actor,{"data_fitness_id":body.get("data_fitness_id","")}); return self.get(pid)
    def add_runtime_target(self,pid,req:ComputationalRuntimeTargetAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); body["capabilities"]=_uniq(body["capabilities"]); body["restrictions"]=_uniq(body["restrictions"]); rid=_id("runtime-",{k:v for k,v in body.items() if k!="metadata"}); item={"runtime_target_id":rid,**body,"candidate_only":True,"availability_verified":False,"created_utc":_now()}
        if not any(x["runtime_target_id"]==rid for x in rec["runtime_targets"]): rec["runtime_targets"].append(item); self._save(rec); self._event(pid,"runtime-target.added",actor,{"runtime_target_id":rid})
        return self.get(pid)
    def add_step(self,pid,req:ComputationalAnalysisStepAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref")
        runtime_ids={x["runtime_target_id"] for x in rec["runtime_targets"]}
        if body["runtime_target_id"] not in runtime_ids: raise ValueError("Analysis step references an unknown runtime_target_id.")
        body["dataset_ids"]=_uniq(body["dataset_ids"]); body["variable_ids"]=_uniq(body["variable_ids"]); body["dependency_step_ids"]=_uniq(body["dependency_step_ids"]); body["preprocessing"]=_uniq(body["preprocessing"]); body["expected_outputs"]=_uniq(body["expected_outputs"]); body["validation_checks"]=_uniq(body["validation_checks"]); body["limitations"]=_uniq(body["limitations"])
        upstream=self._fitness().get(rec["data_fitness_id"]) if rec.get("data_fitness_id") else {"dataset_candidates":[],"variables":[]}
        known_ds={x.get("dataset_id") for x in upstream.get("dataset_candidates",[])} | set(rec.get("dataset_ids",[])); missing_ds=[x for x in body["dataset_ids"] if x not in known_ds]
        if missing_ds: raise ValueError("Analysis step references an unknown dataset_id.")
        known_vars={x.get("variable_id") for x in upstream.get("variables",[])}; missing_vars=[x for x in body["variable_ids"] if x not in known_vars]
        if missing_vars: raise ValueError("Analysis step references an unknown variable_id.")
        known_steps={x["step_id"] for x in rec["analysis_steps"]}; missing_deps=[x for x in body["dependency_step_ids"] if x not in known_steps]
        if missing_deps: raise ValueError("Analysis step references an unknown dependency_step_id.")
        sid=_id("cstep-",{"label":body["label"],"objective":body["objective"],"runtime_target_id":body["runtime_target_id"],"dataset_ids":body["dataset_ids"],"variable_ids":body["variable_ids"],"dependency_step_ids":body["dependency_step_ids"]})
        item={"step_id":sid,**body,"human_authored":True,"execution_status":"not-executed","scientific_validity_certified":False,"created_utc":_now()}
        if not any(x["step_id"]==sid for x in rec["analysis_steps"]): rec["analysis_steps"].append(item); self._save(rec); self._event(pid,"analysis-step.added",actor,{"step_id":sid})
        return self.get(pid)
    def decide_step(self,pid,req:ComputationalStepDecisionRequest):
        rec=self.get(pid); known={x["step_id"] for x in rec["analysis_steps"]}
        if req.step_id not in known: raise ValueError("Step decision references an unknown step_id.")
        item={"step_id":req.step_id,"decision":req.decision,"rationale":req.rationale,"actor_ref":req.actor_ref,"human_recorded":True,"truth_or_validity_judgment":False,"updated_utc":_now()}
        old=next((x for x in rec["step_decisions"] if x["step_id"]==req.step_id),None)
        if old: old.update(item)
        else: rec["step_decisions"].append(item)
        self._save(rec); self._event(pid,"analysis-step.decision",req.actor_ref,{"step_id":req.step_id,"decision":req.decision}); return self.get(pid)
    def add_reproducibility_requirement(self,pid,req:ReproducibilityRequirementAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); rid=_id("repro-",body); item={"reproducibility_requirement_id":rid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["reproducibility_requirement_id"]==rid for x in rec["reproducibility_requirements"]): rec["reproducibility_requirements"].append(item); self._save(rec); self._event(pid,"reproducibility-requirement.added",actor,{"reproducibility_requirement_id":rid})
        return self.get(pid)
    def add_constraint(self,pid,req:ComputationalConstraintAddRequest):
        rec=self.get(pid); body=req.model_dump(); actor=body.pop("actor_ref"); cid=_id("constraint-",body); item={"constraint_id":cid,**body,"human_recorded":True,"created_utc":_now()}
        if not any(x["constraint_id"]==cid for x in rec["constraints"]): rec["constraints"].append(item); self._save(rec); self._event(pid,"constraint.added",actor,{"constraint_id":cid})
        return self.get(pid)
    def set_state(self,pid,req:ComputationalResearchPlanStateRequest):
        rec=self.get(pid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(pid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(pid)
    def execution_graph(self,pid):
        rec=self.get(pid); nodes=[]; edges=[]
        for s in rec["analysis_steps"]:
            nodes.append({"step_id":s["step_id"],"label":s["label"],"runtime_target_id":s["runtime_target_id"],"execution_status":s["execution_status"]})
            for dep in s["dependency_step_ids"]: edges.append({"from_step_id":dep,"to_step_id":s["step_id"],"relation":"precedes"})
        graph={n["step_id"]:[] for n in nodes}
        for e in edges: graph[e["from_step_id"]].append(e["to_step_id"])
        visiting=set(); visited=set(); cycle=False
        def dfs(x):
            nonlocal cycle
            if x in visiting: cycle=True; return
            if x in visited: return
            visiting.add(x)
            for y in graph.get(x,[]): dfs(y)
            visiting.remove(x); visited.add(x)
        for x in list(graph): dfs(x)
        return {"schema":COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA,"computational_plan_id":pid,"nodes":nodes,"edges":edges,"has_cycle":cycle,"governance":{"graph_is_declared_dependency_structure_not_execution_trace":True}}
    def readiness(self,pid):
        rec=self.get(pid); decisions={x["step_id"]:x["decision"] for x in rec["step_decisions"]}; blockers=[]
        if not rec["runtime_targets"]: blockers.append("no-runtime-targets")
        if not rec["analysis_steps"]: blockers.append("no-analysis-steps")
        if rec["analysis_steps"] and any(decisions.get(x["step_id"])!="approved-for-execution" for x in rec["analysis_steps"]): blockers.append("analysis-steps-not-human-approved")
        if not rec["reproducibility_requirements"]: blockers.append("no-reproducibility-requirements")
        if any(x.get("blocking") for x in rec["constraints"]): blockers.append("blocking-computational-constraint")
        if self.execution_graph(pid)["has_cycle"]: blockers.append("dependency-cycle")
        if rec["review"]["state"]!="approved": blockers.append("review-not-approved")
        if rec.get("data_fitness_id") and not rec.get("human_accepted_dataset_ids"): blockers.append("no-upstream-human-accepted-dataset")
        return {"schema":COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA,"computational_plan_id":pid,"ready_for_execution_handoff":not blockers,"blockers":blockers,"approved_step_ids":[x["step_id"] for x in rec["analysis_steps"] if decisions.get(x["step_id"])=="approved-for-execution"],"governance":{"readiness_is_plan_completeness_not_execution_success_or_scientific_validity":True}}
    def execution_handoffs(self,pid):
        rec=self.get(pid); decisions={x["step_id"]:x["decision"] for x in rec["step_decisions"]}; runtimes={x["runtime_target_id"]:x for x in rec["runtime_targets"]}; packets=[]
        for s in rec["analysis_steps"]:
            if decisions.get(s["step_id"])!="approved-for-execution": continue
            rt=runtimes[s["runtime_target_id"]]; packets.append({"handoff_id":_id("exec-",{"plan":pid,"step":s["step_id"]}),"target":rt["runtime_kind"],"runtime_target":rt,"step":s,"write_performed":False,"execution_performed":False})
        return {"schema":COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA,"computational_plan_id":pid,"packets":packets,"target_products":sorted(set(x["target"] for x in packets)),"governance":{"handoffs_are_specs_not_commands":True,"specialist_runtime_execution_required":True,"automatic_execution":False}}
    def plan_summary(self,pid):
        rec=self.get(pid); decisions={x["decision"]:0 for x in rec["step_decisions"]}
        for x in rec["step_decisions"]: decisions[x["decision"]]=decisions.get(x["decision"],0)+1
        return {"schema":COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA,"computational_plan_id":pid,"runtime_targets":len(rec["runtime_targets"]),"analysis_steps":len(rec["analysis_steps"]),"reproducibility_requirements":len(rec["reproducibility_requirements"]),"constraints":len(rec["constraints"]),"step_decisions":decisions,"execution_graph":self.execution_graph(pid),"readiness":self.readiness(pid)}
    def core_candidate(self,pid):
        rec=self.get(pid); return {"candidate_id":_id("corecand-",{"computational_plan_id":pid,"type":"computational-research-plan"}),"object_type":"computational-research-plan","source_computational_plan_id":pid,"payload":{"research_question":rec.get("research_question",""),"data_fitness_id":rec.get("data_fitness_id",""),"dataset_ids":rec.get("dataset_ids",[]),"runtime_targets":rec["runtime_targets"],"analysis_steps":rec["analysis_steps"],"step_decisions":rec["step_decisions"],"reproducibility_requirements":rec["reproducibility_requirements"],"constraints":rec["constraints"]},"handoff_status":"human-approved-candidate" if self.readiness(pid)["ready_for_execution_handoff"] else "draft-candidate","promotion_performed":False,"execution_performed":False,"governance":{"platform_core_remains_authoritative":True,"candidate_is_not_promoted_object":True}}
    def freeze_snapshot(self,req:ComputationalResearchPlanSnapshotRequest):
        rec=self.get(req.computational_plan_id); payload={"schema":COMPUTATIONAL_RESEARCH_PLANNING_SNAPSHOT_SCHEMA,"computational_plan_id":req.computational_plan_id,"record":rec,"summary":self.plan_summary(req.computational_plan_id),"execution_handoffs":self.execution_handoffs(req.computational_plan_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_plan_record_not_execution_or_validity_certification":True}}
        h=_sha(payload); sid="compplansnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_computational_research_plan_snapshots(snapshot_id,computational_plan_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.computational_plan_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO computational_research_plan_snapshots(snapshot_id,computational_plan_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.computational_plan_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.computational_plan_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid}); return payload

def capabilities():
    return {"schema":COMPUTATIONAL_RESEARCH_PLANNING_SCHEMA,"release":settings.release_version,"milestone":"10.9","durable":True,"analysis_step_registry":True,"runtime_target_registry":True,"dependency_graph":True,"reproducibility_requirement_registry":True,"execution_handoff_packets":True,"human_method_and_runtime_approval_required":True,"upstream_dataset_fitness_is_inherited_not_rejudged":True,"automatic_method_selection":False,"automatic_runtime_selection":False,"automatic_execution":False,"automatic_result_interpretation":False,"automatic_truth_promotion":False,"specialist_runtimes_own_execution":True,"platform_core_remains_research_object_authority":True}
_store=None
def get_computational_research_planning_store():
    global _store
    if _store is None: _store=ComputationalResearchPlanningStore()
    return _store
