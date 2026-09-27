from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.causal_research_design_intelligence import *
from .statistical_analysis_planning_intelligence import get_statistical_analysis_planning_intelligence_store
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

class CausalResearchDesignIntelligenceStore:
    def __init__(self,sqlite_path:Path|None=None,statistical_analysis_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"causal_research_design_intelligence.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self.statistical_analysis_store=statistical_analysis_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres causal research design storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _statistics(self): return self.statistical_analysis_store or get_statistical_analysis_planning_intelligence_store()
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
CREATE TABLE IF NOT EXISTS causal_research_designs(causal_design_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS causal_research_design_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,causal_design_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS causal_research_design_snapshots(snapshot_id TEXT PRIMARY KEY,causal_design_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_causal_research_designs(causal_design_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_causal_research_design_events(event_id BIGSERIAL PRIMARY KEY,causal_design_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_causal_research_design_events_design ON sc_rl_causal_research_design_events(causal_design_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_causal_research_design_snapshots(snapshot_id TEXT PRIMARY KEY,causal_design_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,cid,typ,actor,payload):
        created=_now(); h=_sha({"causal_design_id":cid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_causal_research_design_events(causal_design_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(cid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO causal_research_design_events(causal_design_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(cid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_causal_research_designs(causal_design_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(causal_design_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["causal_design_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO causal_research_designs(causal_design_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["causal_design_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,cid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_causal_research_designs WHERE causal_design_id=%s",(cid,)).fetchone()
            if not row: raise ValueError("Causal research design not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM causal_research_designs WHERE causal_design_id=?",(cid,)).fetchone()
        if not row: raise ValueError("Causal research design not found.")
        return json.loads(row["record_json"])
    def create(self,req:CausalResearchDesignCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref")
        try: stat=self._statistics().get(body["statistical_analysis_plan_id"])
        except Exception as exc: raise ValueError("statistical_analysis_plan_id is not available in Statistical Analysis Planning Intelligence.") from exc
        body["core_project_id"]=body.get("core_project_id") or stat.get("core_project_id","")
        cid=_id("causaldesign-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(cid)
        except ValueError: pass
        rec={"schema":CAUSAL_RESEARCH_DESIGN_SCHEMA,"causal_design_id":cid,**body,
             "study_protocol_id":stat.get("study_protocol_id","") ,"research_program_id":stat.get("research_program_id","") ,"statistical_analysis_plan_fingerprint":stat.get("record_hash",""),
             "preregistration_baseline_snapshot_hash":stat.get("preregistration_baseline_snapshot_hash",""),"statistical_estimands":stat.get("estimands",[]),"statistical_model_specifications":stat.get("model_specifications",[]),
             "variable_roles":[],"causal_edges":[],"causal_assumptions":[],"identification_strategies":[],"diagnostic_plans":[],"negative_control_plans":[],"sensitivity_plans":[],"design_decisions":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),
             "governance":{"causal_design_is_prospective_identification_plan_not_causal_result":True,"statistical_plan_lineage_is_inherited_not_rewritten":True,"human_causal_design_approval_required":True,
             "dag_represents_assumptions_not_proven_structure":True,"untestable_assumptions_remain_explicit":True,"research_lab_and_specialist_runtimes_own_causal_execution":True,"platform_core_remains_governed_causal_object_authority":True,
             "automatic_causal_identification":False,"automatic_adjustment_set_selection":False,"automatic_instrument_validation":False,"automatic_causal_estimation":False,"automatic_causality_inference":False,"automatic_execution":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(cid,"causal-research-design.created",actor,{"statistical_analysis_plan_id":body["statistical_analysis_plan_id"]}); return self.get(cid)
    def _known(self,rec,key,idkey): return {x[idkey] for x in rec.get(key,[])}
    def add_variable_role(self,cid,req:CausalVariableRoleAddRequest):
        rec=self.get(cid); body=req.model_dump(); actor=body.pop("actor_ref"); rid=_id("causalrole-",body); item={"causal_role_id":rid,**body,"human_specified":True,"role_not_inferred":True,"created_utc":_now()}
        if not any(x["causal_role_id"]==rid for x in rec["variable_roles"]): rec["variable_roles"].append(item); self._save(rec); self._event(cid,"causal-variable-role.added",actor,{"causal_role_id":rid})
        return self.get(cid)
    def _would_cycle(self,rec,source,target):
        graph={x["causal_role_id"]:[] for x in rec["variable_roles"]}
        for e in rec["causal_edges"]: graph.setdefault(e["source_role_id"],[]).append(e["target_role_id"])
        graph.setdefault(source,[]).append(target)
        seen=set(); active=set()
        def visit(n):
            if n in active: return True
            if n in seen: return False
            seen.add(n); active.add(n)
            for nxt in graph.get(n,[]):
                if visit(nxt): return True
            active.remove(n); return False
        return any(visit(n) for n in list(graph))
    def add_edge(self,cid,req:CausalEdgeAddRequest):
        rec=self.get(cid); body=req.model_dump(); actor=body.pop("actor_ref"); body["evidence_refs"]=_uniq(body["evidence_refs"]); known=self._known(rec,"variable_roles","causal_role_id")
        if body["source_role_id"] not in known or body["target_role_id"] not in known: raise ValueError("Causal edge references an unknown causal_role_id.")
        if body["source_role_id"]==body["target_role_id"]: raise ValueError("Causal DAG cannot contain a self-loop.")
        if self._would_cycle(rec,body["source_role_id"],body["target_role_id"]): raise ValueError("Causal edge would introduce a directed cycle into the DAG.")
        eid=_id("causedge-",body); item={"causal_edge_id":eid,**body,"human_specified":True,"causal_relation_not_empirically_established":True,"created_utc":_now()}
        if not any(x["causal_edge_id"]==eid for x in rec["causal_edges"]): rec["causal_edges"].append(item); self._save(rec); self._event(cid,"causal-edge.added",actor,{"causal_edge_id":eid})
        return self.get(cid)
    def add_assumption(self,cid,req:CausalAssumptionAddRequest):
        rec=self.get(cid); body=req.model_dump(); actor=body.pop("actor_ref"); body["linked_role_ids"]=_uniq(body["linked_role_ids"]); known=self._known(rec,"variable_roles","causal_role_id")
        if any(x not in known for x in body["linked_role_ids"]): raise ValueError("Causal assumption references an unknown causal_role_id.")
        aid=_id("causalassumption-",body); item={"causal_assumption_id":aid,**body,"human_specified":True,"assumption_not_proven":True,"created_utc":_now()}
        if not any(x["causal_assumption_id"]==aid for x in rec["causal_assumptions"]): rec["causal_assumptions"].append(item); self._save(rec); self._event(cid,"causal-assumption.added",actor,{"causal_assumption_id":aid})
        return self.get(cid)
    def add_identification_strategy(self,cid,req:CausalIdentificationStrategyAddRequest):
        rec=self.get(cid); body=req.model_dump(); actor=body.pop("actor_ref")
        for k in ["estimand_ids","treatment_or_exposure_role_ids","outcome_role_ids","adjustment_role_ids","instrument_role_ids","assumption_ids","statistical_model_specification_ids","limitations"]: body[k]=_uniq(body[k])
        roles=self._known(rec,"variable_roles","causal_role_id"); assumptions=self._known(rec,"causal_assumptions","causal_assumption_id"); estimands={x.get("estimand_id") for x in rec["statistical_estimands"]}; models={x.get("model_specification_id") for x in rec["statistical_model_specifications"]}
        if any(x not in estimands for x in body["estimand_ids"]): raise ValueError("Identification strategy references an unknown estimand_id.")
        if any(x not in roles for k in ["treatment_or_exposure_role_ids","outcome_role_ids","adjustment_role_ids","instrument_role_ids"] for x in body[k]): raise ValueError("Identification strategy references an unknown causal_role_id.")
        if any(x not in assumptions for x in body["assumption_ids"]): raise ValueError("Identification strategy references an unknown causal_assumption_id.")
        if any(x not in models for x in body["statistical_model_specification_ids"]): raise ValueError("Identification strategy references an unknown model_specification_id.")
        sid=_id("idstrategy-",body); item={"identification_strategy_id":sid,**body,"human_specified":True,"identification_not_established":True,"estimation_not_executed":True,"created_utc":_now()}
        if not any(x["identification_strategy_id"]==sid for x in rec["identification_strategies"]): rec["identification_strategies"].append(item); self._save(rec); self._event(cid,"identification-strategy.added",actor,{"identification_strategy_id":sid})
        return self.get(cid)
    def add_diagnostic_plan(self,cid,req:CausalDiagnosticPlanAddRequest):
        rec=self.get(cid); body=req.model_dump(); actor=body.pop("actor_ref"); body["identification_strategy_ids"]=_uniq(body["identification_strategy_ids"]); known=self._known(rec,"identification_strategies","identification_strategy_id")
        if any(x not in known for x in body["identification_strategy_ids"]): raise ValueError("Diagnostic plan references an unknown identification_strategy_id.")
        did=_id("causaldiag-",body); item={"diagnostic_plan_id":did,**body,"human_specified":True,"diagnostic_not_executed":True,"created_utc":_now()}
        if not any(x["diagnostic_plan_id"]==did for x in rec["diagnostic_plans"]): rec["diagnostic_plans"].append(item); self._save(rec); self._event(cid,"causal-diagnostic-plan.added",actor,{"diagnostic_plan_id":did})
        return self.get(cid)
    def add_negative_control_plan(self,cid,req:CausalNegativeControlPlanAddRequest):
        rec=self.get(cid); body=req.model_dump(); actor=body.pop("actor_ref"); body["identification_strategy_ids"]=_uniq(body["identification_strategy_ids"]); known=self._known(rec,"identification_strategies","identification_strategy_id")
        if any(x not in known for x in body["identification_strategy_ids"]): raise ValueError("Negative control plan references an unknown identification_strategy_id.")
        nid=_id("negcontrol-",body); item={"negative_control_plan_id":nid,**body,"human_specified":True,"control_not_executed":True,"created_utc":_now()}
        if not any(x["negative_control_plan_id"]==nid for x in rec["negative_control_plans"]): rec["negative_control_plans"].append(item); self._save(rec); self._event(cid,"negative-control-plan.added",actor,{"negative_control_plan_id":nid})
        return self.get(cid)
    def add_sensitivity_plan(self,cid,req:CausalSensitivityPlanAddRequest):
        rec=self.get(cid); body=req.model_dump(); actor=body.pop("actor_ref"); body["identification_strategy_ids"]=_uniq(body["identification_strategy_ids"]); body["target_assumption_ids"]=_uniq(body["target_assumption_ids"])
        if any(x not in self._known(rec,"identification_strategies","identification_strategy_id") for x in body["identification_strategy_ids"]): raise ValueError("Causal sensitivity plan references an unknown identification_strategy_id.")
        if any(x not in self._known(rec,"causal_assumptions","causal_assumption_id") for x in body["target_assumption_ids"]): raise ValueError("Causal sensitivity plan references an unknown causal_assumption_id.")
        sid=_id("causalsens-",body); item={"causal_sensitivity_plan_id":sid,**body,"human_specified":True,"sensitivity_not_executed":True,"created_utc":_now()}
        if not any(x["causal_sensitivity_plan_id"]==sid for x in rec["sensitivity_plans"]): rec["sensitivity_plans"].append(item); self._save(rec); self._event(cid,"causal-sensitivity-plan.added",actor,{"causal_sensitivity_plan_id":sid})
        return self.get(cid)
    def _object_exists(self,rec,typ,oid):
        maps={"identification-strategy":("identification_strategies","identification_strategy_id"),"causal-assumption":("causal_assumptions","causal_assumption_id"),"diagnostic-plan":("diagnostic_plans","diagnostic_plan_id"),"negative-control-plan":("negative_control_plans","negative_control_plan_id"),"sensitivity-plan":("sensitivity_plans","causal_sensitivity_plan_id")}
        key,idkey=maps[typ]; return oid in self._known(rec,key,idkey)
    def decide(self,cid,req:CausalDesignDecisionRequest):
        rec=self.get(cid)
        if not self._object_exists(rec,req.object_type,req.object_id): raise ValueError("Causal design decision references an unknown object_id.")
        item={"object_type":req.object_type,"object_id":req.object_id,"decision":req.decision,"rationale":req.rationale,"actor_ref":req.actor_ref,"decided_utc":_now()}
        rec["design_decisions"]=[x for x in rec["design_decisions"] if not(x["object_type"]==req.object_type and x["object_id"]==req.object_id)]+[item]; self._save(rec); self._event(cid,"causal-design-object.decision",req.actor_ref,item); return self.get(cid)
    def causal_graph(self,cid):
        rec=self.get(cid); return {"schema":"sc-research-librarian-causal-dag/1.0","causal_design_id":cid,"nodes":rec["variable_roles"],"edges":rec["causal_edges"],"acyclic":True,"governance":{"graph_encodes_human_declared_causal_assumptions_not_established_causal_facts":True}}
    def design_matrix(self,cid):
        rec=self.get(cid); decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["design_decisions"]}
        rows=[{"identification_strategy_id":x["identification_strategy_id"],"label":x["label"],"strategy":x["strategy"],"estimand_ids":x["estimand_ids"],"assumption_ids":x["assumption_ids"],"adjustment_role_ids":x["adjustment_role_ids"],"instrument_role_ids":x["instrument_role_ids"],"decision":decisions.get(("identification-strategy",x["identification_strategy_id"]),"pending")} for x in rec["identification_strategies"]]
        return {"schema":CAUSAL_RESEARCH_DESIGN_SCHEMA,"causal_design_id":cid,"rows":rows,"diagnostic_plans":rec["diagnostic_plans"],"negative_control_plans":rec["negative_control_plans"],"sensitivity_plans":rec["sensitivity_plans"],"governance":{"matrix_is_design_comparison_not_strategy_ranking_or_causal_result":True}}
    def readiness(self,cid):
        rec=self.get(cid); blockers=[]; decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["design_decisions"]}; roles={x["role"] for x in rec["variable_roles"]}
        if not ({"treatment","exposure"}&roles): blockers.append("no-treatment-or-exposure-role")
        if "outcome" not in roles: blockers.append("no-outcome-role")
        if not rec["causal_assumptions"]: blockers.append("no-causal-assumptions")
        if not rec["identification_strategies"]: blockers.append("no-identification-strategies")
        if rec["identification_strategies"] and any(decisions.get(("identification-strategy",x["identification_strategy_id"]),"pending")!="approved" for x in rec["identification_strategies"]): blockers.append("identification-strategies-await-human-approval")
        if not rec["diagnostic_plans"]: blockers.append("no-diagnostic-plans")
        return {"schema":CAUSAL_RESEARCH_DESIGN_SCHEMA,"causal_design_id":cid,"ready_for_causal_handoff":not blockers,"blockers":blockers,"dimensions":{"treatment_or_exposure_declared":bool({"treatment","exposure"}&roles),"outcome_declared":"outcome" in roles,"dag_declared":bool(rec["causal_edges"]),"assumptions_declared":bool(rec["causal_assumptions"]),"identification_strategies_declared":bool(rec["identification_strategies"]),"identification_strategies_human_approved":bool(rec["identification_strategies"]) and all(decisions.get(("identification-strategy",x["identification_strategy_id"]))=="approved" for x in rec["identification_strategies"]),"diagnostics_declared":bool(rec["diagnostic_plans"]),"negative_controls_declared":bool(rec["negative_control_plans"]),"sensitivity_plans_declared":bool(rec["sensitivity_plans"])} ,"governance":{"readiness_is_structural_design_completeness_not_causal_identification_or_validity":True,"automatic_execution":False}}
    def runtime_handoffs(self,cid):
        rec=self.get(cid); ready=self.readiness(cid); decisions={(x["object_type"],x["object_id"]):x["decision"] for x in rec["design_decisions"]}; approved=[x for x in rec["identification_strategies"] if decisions.get(("identification-strategy",x["identification_strategy_id"]))=="approved"]
        return {"schema":CAUSAL_RESEARCH_DESIGN_SCHEMA,"causal_design_id":cid,"packets":[{"schema":"sc-research-librarian-causal-runtime-handoff/1.0","handoff_id":_id("causalhand-",{"design":cid,"strategy":s["identification_strategy_id"]}),"target":"research-lab-causal-inference","secondary_target":"statistical-analysis-plan","preferred_runtime":"research-lab","identification_strategy":s,"causal_graph":self.causal_graph(cid),"assumptions":[a for a in rec["causal_assumptions"] if a["causal_assumption_id"] in s["assumption_ids"]],"diagnostic_plans":[d for d in rec["diagnostic_plans"] if not d["identification_strategy_ids"] or s["identification_strategy_id"] in d["identification_strategy_ids"]],"negative_control_plans":[d for d in rec["negative_control_plans"] if not d["identification_strategy_ids"] or s["identification_strategy_id"] in d["identification_strategy_ids"]],"sensitivity_plans":[d for d in rec["sensitivity_plans"] if not d["identification_strategy_ids"] or s["identification_strategy_id"] in d["identification_strategy_ids"]],"statistical_analysis_plan_id":rec["statistical_analysis_plan_id"],"handoff_ready":ready["ready_for_causal_handoff"],"execution_performed":False,"adjustment_set_selected_automatically":False,"identification_established":False,"causality_inferred":False} for s in approved],"governance":{"handoffs_are_causal_execution_inputs_not_causal_results":True,"research_lab_and_specialist_runtimes_own_execution":True}}
    def core_candidate(self,cid):
        rec=self.get(cid); return {"schema":"sc-research-librarian-core-causal-research-design-candidate/1.0","candidate_id":_id("corecand-",{"causal_design_id":cid,"type":"causal-research-design"}),"object_type":"causal-research-design","source_causal_design_id":cid,"payload":{"title":rec["title"],"statistical_analysis_plan_id":rec["statistical_analysis_plan_id"],"causal_graph":self.causal_graph(cid),"assumptions":rec["causal_assumptions"],"identification_strategies":rec["identification_strategies"],"diagnostic_plans":rec["diagnostic_plans"],"negative_control_plans":rec["negative_control_plans"],"sensitivity_plans":rec["sensitivity_plans"],"record_hash":rec["record_hash"]},"promotion_performed":False,"execution_performed":False,"causality_inferred":False,"governance":{"platform_core_remains_governed_causal_object_authority":True}}
    def set_state(self,cid,req:CausalResearchDesignStateRequest):
        rec=self.get(cid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(cid,"review-state.changed",req.actor_ref,{"state":req.state}); return self.get(cid)
    def freeze_snapshot(self,req:CausalResearchDesignSnapshotRequest):
        rec=self.get(req.causal_design_id); payload={"schema":CAUSAL_RESEARCH_DESIGN_SNAPSHOT_SCHEMA,"causal_design_id":req.causal_design_id,"design":rec,"causal_graph":self.causal_graph(req.causal_design_id),"design_matrix":self.design_matrix(req.causal_design_id),"readiness":self.readiness(req.causal_design_id),"runtime_handoffs":self.runtime_handoffs(req.causal_design_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_causal_design_record_not_causal_validity_or_effect_certification":True}}
        h=_sha(payload); sid="causaldesignsnap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_causal_research_design_snapshots(snapshot_id,causal_design_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.causal_design_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO causal_research_design_snapshots(snapshot_id,causal_design_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.causal_design_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.causal_design_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities():
    return {"schema":CAUSAL_RESEARCH_DESIGN_SCHEMA,"release":settings.release_version,"milestone":"11.3","durable":True,"statistical_analysis_plan_lineage":True,"causal_variable_role_registry":True,"directed_acyclic_graph":True,"causal_assumption_registry":True,"identification_strategy_registry":True,"diagnostic_planning":True,"negative_control_planning":True,"causal_sensitivity_planning":True,"design_matrix":True,"runtime_handoffs":True,"human_causal_design_approval_required":True,"statistical_plan_lineage_is_inherited_not_rewritten":True,"research_lab_and_specialist_runtimes_own_causal_execution":True,"platform_core_remains_governed_causal_object_authority":True,"automatic_causal_identification":False,"automatic_adjustment_set_selection":False,"automatic_instrument_validation":False,"automatic_causal_estimation":False,"automatic_causality_inference":False,"automatic_execution":False,"automatic_truth_promotion":False}
_store=None
def get_causal_research_design_intelligence_store():
    global _store
    if _store is None: _store=CausalResearchDesignIntelligenceStore()
    return _store
