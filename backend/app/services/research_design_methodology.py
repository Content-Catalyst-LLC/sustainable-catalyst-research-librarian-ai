from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.research_design_methodology import (
    RESEARCH_DESIGN_METHODOLOGY_SCHEMA, RESEARCH_DESIGN_METHODOLOGY_SNAPSHOT_SCHEMA,
    ResearchDesignPlanCreateRequest, MethodologyCandidateAddRequest, ResearchDesignValidityThreatRequest,
    ResearchDesignPreferenceRequest, ResearchDesignReviewStateRequest, ResearchDesignSnapshotRequest,
)
from .research_question_hypothesis import get_research_question_hypothesis_store

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

class ResearchDesignMethodologyStore:
    def __init__(self, sqlite_path:Path|None=None, question_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"research_design_methodology.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema); self.question_store=question_store
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres research-design storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _questions(self): return self.question_store or get_research_question_hypothesis_store()
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
CREATE TABLE IF NOT EXISTS research_design_plans(plan_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_design_plan_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,plan_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS research_design_plan_snapshots(snapshot_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_research_design_plans(plan_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_design_plan_events(event_id BIGSERIAL PRIMARY KEY,plan_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_research_design_plan_events_plan ON sc_rl_research_design_plan_events(plan_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_research_design_plan_snapshots(snapshot_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,pid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"plan_id":pid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_design_plan_events(plan_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(pid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO research_design_plan_events(plan_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(pid,typ,actor,_json(payload),h,created))
    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_design_plans(plan_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(plan_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["plan_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO research_design_plans(plan_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["plan_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,pid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_research_design_plans WHERE plan_id=%s",(pid,)).fetchone()
            if not row: raise ValueError("Research design plan not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM research_design_plans WHERE plan_id=?",(pid,)).fetchone()
        if not row: raise ValueError("Research design plan not found.")
        return json.loads(row["record_json"])
    def _question_context(self,qid:str)->dict[str,Any]:
        if not qid: return {}
        return self._questions().get(qid)
    def _candidate(self,label:str,family:str,design_type:str,rationale:str,q:dict[str,Any],data:list[str],assumptions:list[str],threats:list[str],analyses:list[str],targets:list[str],limitations:list[str])->dict[str,Any]:
        variables=[v.get("name","") for v in q.get("variables",[]) if v.get("name")]
        hypotheses=[h.get("hypothesis_id","") for h in q.get("hypotheses",[]) if h.get("hypothesis_id")]
        item={"label":label,"method_family":family,"design_type":design_type,"rationale":rationale,"question_alignment":[q.get("broad_question","")] if q.get("broad_question") else [],"hypothesis_refs":hypotheses,"variable_names":variables,"sampling_strategy":"Define the sampling frame, eligibility criteria, unit of analysis, and stopping rule before execution.","data_requirements":data,"assumptions":assumptions,"validity_threats":threats,"analysis_candidates":analyses,"execution_targets":targets,"limitations":limitations,"origin":"deterministic-scaffold","human_review_status":"unreviewed"}
        item["candidate_id"]=_id("method-",item); return item
    def _scaffold(self,q:dict[str,Any])->list[dict[str,Any]]:
        typ=q.get("question_type","unspecified")
        common_data=_uniq((q.get("evidence_requirements") or [])+["documented variable definitions and provenance","analysis-ready observations or source material appropriate to the design"])
        if typ=="causal":
            return [
                self._candidate("Candidate longitudinal observational design","observational","longitudinal observational cohort/panel","Useful when treatment assignment is not controlled and temporal ordering can be observed; causal interpretation still depends on an explicit identification strategy.",q,common_data+["repeated observations over time","candidate confounders and exposure timing"],["exchangeability/conditional ignorability if used for causal estimation","positivity/overlap","measurement consistency"],["unmeasured confounding","selection into exposure","time-varying confounding","measurement drift"],["descriptive diagnostics","adjusted regression or weighting candidate","sensitivity analysis"],["workspace","research-lab","analytics-r"],["Observational evidence alone does not establish causality without defensible identification assumptions."]),
                self._candidate("Candidate quasi-experimental design","quasi-experimental","natural experiment / difference-in-differences / interrupted time series","Consider when a plausibly exogenous policy, threshold, timing event, or comparison group exists. The specific estimator must be chosen only after design assumptions are evaluated.",q,common_data+["pre/post outcome history","comparison group or assignment mechanism","intervention/event timing"],["design-specific identification assumptions","stable measurement","no relevant simultaneous intervention unless modeled"],["parallel-trends failure","anticipation","spillovers","history effects"],["pre-trend diagnostics","design-specific effect estimation","placebo and falsification tests"],["research-lab","workspace","analytics-r"],["Not every exposure has a credible quasi-experimental assignment mechanism."]),
            ]
        if typ in {"comparative","relational","predictive"}:
            return [
                self._candidate("Candidate quantitative observational design","quantitative","cross-sectional or longitudinal analytical study","Supports estimation of differences, associations, or predictive relationships while keeping causal claims separate from associational evidence unless a causal design is added.",q,common_data,["sampling process is documented","measurement validity","analysis assumptions are checked"],["selection bias","confounding","model misspecification","data leakage for prediction"],["descriptive analysis","regression/association analysis","out-of-sample validation when predictive"],["workspace","analytics-r","research-lab"],["Association or predictive accuracy should not be described as causal effect."]),
                self._candidate("Candidate mixed-methods explanatory design","mixed-methods","explanatory sequential mixed-methods","Pairs quantitative patterns with qualitative inquiry into mechanisms, interpretation, or contextual variation.",q,common_data+["purposefully sampled qualitative material or interviews"],["integration logic is pre-specified","qualitative and quantitative units are meaningfully linked"],["integration bias","non-comparable samples","researcher interpretation bias"],["quantitative pattern analysis","coded qualitative analysis","triangulation matrix"],["workspace","research-lab"],["Mixed methods increases interpretive depth but also integration complexity."]),
            ]
        if typ in {"descriptive","exploratory"}:
            return [
                self._candidate("Candidate descriptive evidence-mapping design","systematic-review","scoping review / evidence map","Appropriate for mapping concepts, populations, methods, evidence density, and unresolved questions without forcing a hypothesis test.",q,common_data+["reproducible search strategy","eligibility criteria","screening and extraction fields"],["search coverage is documented","eligibility rules are consistently applied"],["publication bias","database coverage limits","screening inconsistency"],["descriptive synthesis","evidence mapping","gap characterization"],["knowledge-library","workspace"],["A scoping review characterizes available evidence; it does not by itself estimate causal effects."]),
                self._candidate("Candidate qualitative or case-study design","qualitative","comparative case study / thematic inquiry","Useful for mechanism discovery, context, construct refinement, and generation of testable propositions when the evidence base is heterogeneous or under-specified.",q,common_data+["case selection rationale","source triangulation plan"],["case boundaries are explicit","coding/interpretive procedures are documented"],["case-selection bias","confirmation bias","limited transferability"],["thematic coding","within-case analysis","cross-case comparison"],["workspace","research-lab"],["Findings may be analytically transferable without being statistically generalizable."]),
            ]
        if typ=="evaluative":
            return [
                self._candidate("Candidate program/policy evaluation design","mixed-methods","theory-based outcome and process evaluation","Combines outcome measurement with implementation/context evidence so effectiveness claims can be separated from delivery and mechanism questions.",q,common_data+["program theory or logic model","outcome and implementation measures"],["evaluation criteria are pre-specified","comparison strategy is defensible where effects are estimated"],["selection bias","implementation heterogeneity","outcome substitution"],["outcome analysis","process analysis","subgroup/context analysis"],["research-lab","workspace","analytics-r"],["Evaluation conclusions depend on both outcome evidence and implementation context."])
            ]
        if typ=="methodological":
            return [self._candidate("Candidate methodological validation design","methodological","measurement / benchmark / validation study","Tests the performance, reliability, validity, or reproducibility of a method rather than treating method choice as already established.",q,common_data+["reference standard or benchmark","repeatability/reliability observations"],["benchmark is appropriate","performance metrics are pre-specified"],["benchmark bias","spectrum effects","overfitting to validation data"],["agreement/reliability analysis","error analysis","external validation"],["research-lab","workspace"],["Validation performance is conditional on the tested data and benchmark."])]
        return [self._candidate("Candidate general research design","mixed-methods","structured multi-method inquiry","Provides a reviewable starting point when the question type does not yet determine a narrower design family.",q,common_data,["question scope is clarified before execution"],["design-question mismatch","scope drift"],["descriptive baseline","method-specific analysis after human design selection"],["workspace","research-lab"],["The design should be refined after the research question is reviewed."])]
    def create(self,req:ResearchDesignPlanCreateRequest)->dict[str,Any]:
        body=req.model_dump(); actor=body.pop("actor_ref"); scaffold=bool(body.pop("scaffold_candidates")); q=self._question_context(body.get("question_plan_id",""))
        if not body.get("research_question") and q: body["research_question"]=q.get("broad_question","")
        body["objectives"]=_uniq(body.get("objectives") or []); body["constraints"]=_uniq(body.get("constraints") or [])
        supplied=[]
        for x in body.get("candidate_designs") or []:
            item=dict(x); item.update({"origin":"user-supplied","human_review_status":"reviewed"}); item["data_requirements"]=_uniq(item.get("data_requirements") or []); item["assumptions"]=_uniq(item.get("assumptions") or []); item["validity_threats"]=_uniq(item.get("validity_threats") or []); item["analysis_candidates"]=_uniq(item.get("analysis_candidates") or []); item["execution_targets"]=_uniq(item.get("execution_targets") or []); item["limitations"]=_uniq(item.get("limitations") or []); item["candidate_id"]=_id("method-",item); supplied.append(item)
        body["candidate_designs"]=supplied or (self._scaffold(q or {"broad_question":body.get("research_question","")}) if scaffold else [])
        seed={k:v for k,v in body.items() if k not in {"metadata","preferred_candidate_id"}}; pid=_id("rdmp-",seed)
        try: return self.get(pid)
        except ValueError: pass
        rec={"schema":RESEARCH_DESIGN_METHODOLOGY_SCHEMA,"plan_id":pid,**body,"validity_threat_registry":[],"review":{"state":"draft","note":"","actor_ref":"","updated_utc":""},"created_utc":_now(),"updated_utc":_now(),"governance":{"method_candidates_are_planning_options_not_scientific_judgment":True,"human_method_selection_required":True,"platform_core_remains_governed_research_object_authority":True,"specialist_runtimes_retain_execution":True,"automatic_method_selection":False,"automatic_analysis_execution":False,"automatic_causal_identification":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(pid,"design-plan.created",actor,{"question_plan_id":body.get("question_plan_id"),"candidate_count":len(rec["candidate_designs"]),"scaffold_candidates":scaffold}); return self.get(pid)
    def add_candidate(self,pid:str,req:MethodologyCandidateAddRequest)->dict[str,Any]:
        rec=self.get(pid); item=req.model_dump(); actor=item.pop("actor_ref"); item.update({"origin":"user-supplied","human_review_status":"reviewed"}); item["candidate_id"]=_id("method-",item)
        if not any(x["candidate_id"]==item["candidate_id"] for x in rec["candidate_designs"]): rec["candidate_designs"].append(item); self._save(rec); self._event(pid,"method-candidate.added",actor,{"candidate_id":item["candidate_id"]})
        return self.get(pid)
    def add_validity_threat(self,pid:str,req:ResearchDesignValidityThreatRequest)->dict[str,Any]:
        rec=self.get(pid); item=req.model_dump(); actor=item.pop("actor_ref"); item["threat_id"]=_id("threat-",item)
        if not any(x["threat_id"]==item["threat_id"] for x in rec["validity_threat_registry"]): rec["validity_threat_registry"].append(item); self._save(rec); self._event(pid,"validity-threat.added",actor,{"threat_id":item["threat_id"]})
        return self.get(pid)
    def set_preference(self,pid:str,req:ResearchDesignPreferenceRequest)->dict[str,Any]:
        rec=self.get(pid)
        if not any(x["candidate_id"]==req.candidate_id for x in rec["candidate_designs"]): raise ValueError("Methodology candidate not found.")
        rec["preferred_candidate_id"]=req.candidate_id; rec["preference_rationale"]=req.rationale; self._save(rec); self._event(pid,"method-candidate.preferred",req.actor_ref,{"candidate_id":req.candidate_id,"rationale":req.rationale}); return self.get(pid)
    def set_review_state(self,pid:str,req:ResearchDesignReviewStateRequest)->dict[str,Any]:
        rec=self.get(pid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(pid,"review-state.changed",req.actor_ref,{"state":req.state,"note":req.note}); return self.get(pid)
    def comparison(self,pid:str)->dict[str,Any]:
        rec=self.get(pid); rows=[]
        for x in rec.get("candidate_designs",[]): rows.append({"candidate_id":x["candidate_id"],"label":x["label"],"method_family":x["method_family"],"design_type":x["design_type"],"assumption_count":len(x.get("assumptions",[])),"validity_threat_count":len(x.get("validity_threats",[])),"data_requirement_count":len(x.get("data_requirements",[])),"analysis_candidates":x.get("analysis_candidates",[]),"execution_targets":x.get("execution_targets",[]),"limitations":x.get("limitations",[])})
        return {"schema":RESEARCH_DESIGN_METHODOLOGY_SCHEMA,"plan_id":pid,"candidates":rows,"preferred_candidate_id":rec.get("preferred_candidate_id","") ,"governance":{"comparison_does_not_rank_or_select_methods":True,"human_method_selection_required":True}}
    def readiness(self,pid:str)->dict[str,Any]:
        rec=self.get(pid); preferred=rec.get("preferred_candidate_id",""); selected=next((x for x in rec.get("candidate_designs",[]) if x.get("candidate_id")==preferred),None)
        dimensions={"research_question_bound":bool(rec.get("question_plan_id") or rec.get("research_question")),"candidate_designs_present":bool(rec.get("candidate_designs")),"preferred_design_selected":bool(selected),"data_requirements_defined":bool(selected and selected.get("data_requirements")),"assumptions_documented":bool(selected and selected.get("assumptions")),"validity_threats_documented":bool(selected and selected.get("validity_threats")),"human_review_approved":rec.get("review",{}).get("state")=="approved"}
        required=["research_question_bound","candidate_designs_present","preferred_design_selected","data_requirements_defined","assumptions_documented","validity_threats_documented"]
        blockers=[x.replace("_","-") for x in required if not dimensions[x]]
        return {"schema":RESEARCH_DESIGN_METHODOLOGY_SCHEMA,"plan_id":pid,"ready_for_review":not blockers,"ready_for_execution_handoff":not blockers and dimensions["human_review_approved"],"dimensions":dimensions,"blockers":blockers+([] if dimensions["human_review_approved"] else ["human-review-approval"]),"governance":{"readiness_is_structural_not_methodological_validity":True,"human_approval_required_before_execution_handoff":True,"readiness_does_not_establish_causal_identification":True}}
    def execution_handoffs(self,pid:str)->dict[str,Any]:
        rec=self.get(pid); preferred=rec.get("preferred_candidate_id",""); selected=next((x for x in rec.get("candidate_designs",[]) if x.get("candidate_id")==preferred),None); approved=rec.get("review",{}).get("state")=="approved"
        packets=[]
        if selected:
            for target in selected.get("execution_targets",[]): packets.append({"handoff_id":_id("method-handoff-",{"plan_id":pid,"candidate_id":preferred,"target":target}),"target":target,"source_plan_id":pid,"candidate_id":preferred,"research_question":rec.get("research_question",""),"question_plan_id":rec.get("question_plan_id",""),"design":selected,"status":"human-approved-candidate" if approved else "requires-human-approval"})
        return {"schema":RESEARCH_DESIGN_METHODOLOGY_SCHEMA,"plan_id":pid,"handoffs":packets,"delivery_performed":False,"execution_performed":False,"governance":{"specialist_runtime_acceptance_is_separate":True,"automatic_execution":False,"automatic_method_selection":False}}
    def core_candidate(self,pid:str)->dict[str,Any]:
        rec=self.get(pid); preferred=rec.get("preferred_candidate_id",""); selected=next((x for x in rec.get("candidate_designs",[]) if x.get("candidate_id")==preferred),None); approved=rec.get("review",{}).get("state")=="approved"
        candidate={"candidate_id":_id("corecand-",{"plan_id":pid,"type":"research-design"}),"object_type":"research-design","payload":{"question_plan_id":rec.get("question_plan_id",""),"research_question":rec.get("research_question",""),"selected_methodology":selected,"validity_threat_registry":rec.get("validity_threat_registry",[])},"source_plan_id":pid} if selected else None
        return {"schema":RESEARCH_DESIGN_METHODOLOGY_SCHEMA,"plan_id":pid,"candidate":candidate,"handoff_status":"human-approved-candidate" if approved and candidate else "requires-human-approval","promotion_performed":False,"governance":{"platform_core_remains_authority":True,"automatic_core_write":False,"methodology_candidate_is_not_scientific_validation":True}}
    def freeze_snapshot(self,req:ResearchDesignSnapshotRequest)->dict[str,Any]:
        rec=self.get(req.plan_id); payload={"schema":RESEARCH_DESIGN_METHODOLOGY_SNAPSHOT_SCHEMA,"plan_id":req.plan_id,"plan":rec,"comparison":self.comparison(req.plan_id),"readiness":self.readiness(req.plan_id),"execution_handoffs":self.execution_handoffs(req.plan_id),"core_candidate":self.core_candidate(req.plan_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_methodology_planning_record_not_scientific_certification":True}}
        h=_sha(payload); sid="rdm-snap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_research_design_plan_snapshots(snapshot_id,plan_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.plan_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO research_design_plan_snapshots(snapshot_id,plan_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.plan_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.plan_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":RESEARCH_DESIGN_METHODOLOGY_SCHEMA,"release":settings.release_version,"milestone":"10.2","durable":True,"question_plan_integration":True,"candidate_methodology_scaffolding":True,"method_comparison_without_auto_ranking":True,"sampling_and_data_requirements":True,"assumption_registry":True,"validity_threat_registry":True,"analysis_candidate_planning":True,"execution_target_handoffs":True,"platform_core_candidate_handoff":True,"human_method_selection_required":True,"automatic_method_selection":False,"automatic_execution":False,"automatic_causal_identification":False,"automatic_truth_promotion":False,"specialist_runtimes_retain_execution":True}

_store:ResearchDesignMethodologyStore|None=None
def get_research_design_methodology_store()->ResearchDesignMethodologyStore:
    global _store
    if _store is None: _store=ResearchDesignMethodologyStore()
    return _store
