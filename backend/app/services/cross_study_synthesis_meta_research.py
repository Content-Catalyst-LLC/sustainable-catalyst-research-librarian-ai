from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator
from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.cross_study_synthesis_meta_research import *
from .systematic_review_evidence_synthesis import get_systematic_review_evidence_synthesis_store
from .reproduction_replication_intelligence import get_reproduction_replication_intelligence_store
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

class CrossStudySynthesisMetaResearchStore:
    def __init__(self,sqlite_path:Path|None=None,systematic_review_store:Any|None=None,reproduction_replication_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"cross_study_synthesis_meta_research.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self.systematic_review_store=systematic_review_store; self.reproduction_replication_store=reproduction_replication_store; self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres cross-study synthesis storage requires psycopg.")
            self._migrate_postgres()
        else: self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _reviews(self): return self.systematic_review_store or get_systematic_review_evidence_synthesis_store()
    def _reproductions(self): return self.reproduction_replication_store or get_reproduction_replication_intelligence_store()
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
CREATE TABLE IF NOT EXISTS cross_study_synthesis_projects(cross_study_synthesis_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cross_study_synthesis_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,cross_study_synthesis_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cross_study_synthesis_snapshots(snapshot_id TEXT PRIMARY KEY,cross_study_synthesis_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self):
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_cross_study_synthesis_projects(cross_study_synthesis_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_cross_study_synthesis_events(event_id BIGSERIAL PRIMARY KEY,cross_study_synthesis_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_cross_study_synthesis_events_project ON sc_rl_cross_study_synthesis_events(cross_study_synthesis_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_cross_study_synthesis_snapshots(snapshot_id TEXT PRIMARY KEY,cross_study_synthesis_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())"]: c.execute(ddl)
            c.commit()
    def _event(self,sid,typ,actor,payload):
        created=_now(); h=_sha({"cross_study_synthesis_id":sid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_cross_study_synthesis_events(cross_study_synthesis_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(sid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO cross_study_synthesis_events(cross_study_synthesis_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(sid,typ,actor,_json(payload),h,created))
    def _save(self,rec):
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_cross_study_synthesis_projects(cross_study_synthesis_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(cross_study_synthesis_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["cross_study_synthesis_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO cross_study_synthesis_projects(cross_study_synthesis_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["cross_study_synthesis_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,sid):
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_cross_study_synthesis_projects WHERE cross_study_synthesis_id=%s",(sid,)).fetchone()
            if not row: raise ValueError("Cross-study synthesis project not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM cross_study_synthesis_projects WHERE cross_study_synthesis_id=?",(sid,)).fetchone()
        if not row: raise ValueError("Cross-study synthesis project not found.")
        return json.loads(row["record_json"])
    def create(self,req:CrossStudySynthesisCreateRequest):
        body=req.model_dump(); actor=body.pop("actor_ref"); review=None; repl=[]
        if body.get("systematic_review_id"):
            try: review=self._reviews().get(body["systematic_review_id"])
            except Exception as exc: raise ValueError("systematic_review_id is not available in Systematic Review & Evidence Synthesis Intelligence.") from exc
        for rid in _uniq(body.get("reproduction_replication_ids",[])):
            try: repl.append(self._reproductions().get(rid))
            except Exception as exc: raise ValueError(f"reproduction_replication_id is not available: {rid}") from exc
        body["reproduction_replication_ids"]=_uniq(body.get("reproduction_replication_ids",[]))
        sid=_id("xstudy-",{k:v for k,v in body.items() if k!="metadata"})
        try: return self.get(sid)
        except ValueError: pass
        rec={"schema":CROSS_STUDY_SYNTHESIS_SCHEMA,"cross_study_synthesis_id":sid,**body,
             "upstream_lineage":{"systematic_review_id":body.get("systematic_review_id",""),"systematic_review_fingerprint":(review or {}).get("record_hash",""),"reproduction_replication_fingerprints":[{"id":x.get("reproduction_replication_id",""),"record_hash":x.get("record_hash","")} for x in repl]},
             "studies":[],"synthesis_dimensions":[],"bias_assessments":[],"meta_research_observations":[],"synthesis_plans":[],"execution_receipts":[],"human_interpretations":[],"decisions":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},"created_utc":_now(),"updated_utc":_now(),
             "governance":{"study_level_differences_remain_explicit":True,"risk_of_bias_judgments_are_human_authored":True,"meta_research_observations_are_descriptive_not_accusatory":True,"pooled_estimates_are_execution_receipts_not_truth":True,"human_interpretation_required_for_scholarly_conclusions":True,"specialist_runtimes_own_meta_analysis_execution":True,"platform_core_remains_governed_research_object_authority":True,"automatic_study_inclusion":False,"automatic_risk_of_bias_judgment":False,"automatic_meta_analysis":False,"automatic_publication_bias_verdict":False,"automatic_claim_acceptance":False,"automatic_causal_inference":False,"automatic_execution":False,"automatic_truth_promotion":False}}
        self._save(rec); self._event(sid,"cross-study-synthesis.created",actor,{"synthesis_kind":body["synthesis_kind"],"systematic_review_id":body.get("systematic_review_id","")}); return self.get(sid)
    def _append(self,sid,key,idkey,prefix,body,event,extra=None):
        rec=self.get(sid); actor=body.pop("actor_ref"); oid=_id(prefix,body); item={idkey:oid,**body,**(extra or {}),"created_utc":_now()}
        if not any(x[idkey]==oid for x in rec[key]): rec[key].append(item); self._save(rec); self._event(sid,event,actor,{idkey:oid})
        return self.get(sid)
    def add_study(self,sid,req:CrossStudyEvidenceAddRequest):
        body=req.model_dump(); rrid=body.get("reproduction_replication_id","")
        if rrid and rrid not in self.get(sid).get("reproduction_replication_ids",[]): raise ValueError("reproduction_replication_id must be declared on the cross-study synthesis project.")
        return self._append(sid,"studies","study_id","study-",body,"study.added",{"disposition":"pending","disposition_rationale":"","disposition_actor_ref":"","disposition_updated_utc":"","effect_is_descriptive_input_not_pooled_result":True})
    def set_study_disposition(self,sid,req:CrossStudyDispositionRequest):
        rec=self.get(sid); found=False
        for item in rec["studies"]:
            if item["study_id"]==req.study_id:
                item.update({"disposition":req.disposition,"disposition_rationale":req.rationale,"disposition_actor_ref":req.actor_ref,"disposition_updated_utc":_now()}); found=True; break
        if not found: raise ValueError("study_id is not registered in this project.")
        self._save(rec); self._event(sid,"study.disposition",req.actor_ref,{"study_id":req.study_id,"disposition":req.disposition}); return self.get(sid)
    def add_dimension(self,sid,req:CrossStudySynthesisDimensionAddRequest): return self._append(sid,"synthesis_dimensions","synthesis_dimension_id","dim-",req.model_dump(),"synthesis-dimension.added",{"difference_is_declared_not_auto_judged":True})
    def add_bias_assessment(self,sid,req:CrossStudyBiasAssessmentAddRequest):
        rec=self.get(sid)
        if req.study_id not in {x["study_id"] for x in rec["studies"]}: raise ValueError("study_id is not registered in this project.")
        return self._append(sid,"bias_assessments","bias_assessment_id","bias-",req.model_dump(),"bias-assessment.added",{"human_authored":True,"judgment_not_global_truth":True})
    def add_meta_research_observation(self,sid,req:MetaResearchObservationAddRequest): return self._append(sid,"meta_research_observations","meta_research_observation_id","metaobs-",req.model_dump(),"meta-research-observation.added",{"descriptive_observation_only":True,"causal_or_motive_inference_not_generated":True})
    def add_synthesis_plan(self,sid,req:CrossStudySynthesisPlanAddRequest): return self._append(sid,"synthesis_plans","synthesis_plan_id","synplan-",req.model_dump(),"synthesis-plan.added",{"execution_performed":False,"pooled_result_not_generated":True})
    def decide(self,sid,req:CrossStudyDecisionRequest):
        rec=self.get(sid); mapping={"synthesis-plan":("synthesis_plans","synthesis_plan_id"),"synthesis-dimension":("synthesis_dimensions","synthesis_dimension_id"),"bias-assessment":("bias_assessments","bias_assessment_id")}; key,idkey=mapping[req.object_type]
        if req.object_id not in {x[idkey] for x in rec[key]}: raise ValueError(f"{req.object_type} object is not registered in this project.")
        item={"decision_id":_id("decision-",req.model_dump()),**req.model_dump(),"human_authored":True,"created_utc":_now()}
        if not any(x["decision_id"]==item["decision_id"] for x in rec["decisions"]): rec["decisions"].append(item); self._save(rec); self._event(sid,"human-decision.recorded",req.actor_ref,{"decision_id":item["decision_id"],"decision":req.decision})
        return self.get(sid)
    def _approved(self,rec,typ,oid):
        ds=[x for x in rec.get("decisions",[]) if x.get("object_type")==typ and x.get("object_id")==oid]; return bool(ds and ds[-1].get("decision") in {"approved","waived"})
    def add_execution_receipt(self,sid,req:CrossStudySynthesisReceiptAddRequest):
        rec=self.get(sid); plans={x["synthesis_plan_id"] for x in rec["synthesis_plans"]}
        if req.synthesis_plan_id not in plans: raise ValueError("synthesis_plan_id is not registered in this project.")
        if not self._approved(rec,"synthesis-plan",req.synthesis_plan_id): raise ValueError("synthesis plan requires human approval before an execution receipt can be attached.")
        return self._append(sid,"execution_receipts","execution_receipt_id","receipt-",req.model_dump(),"execution-receipt.added",{"receipt_is_observation_not_scholarly_verdict":True,"pooled_estimates_not_truth_promoted":True})
    def add_human_interpretation(self,sid,req:CrossStudyHumanInterpretationAddRequest): return self._append(sid,"human_interpretations","human_interpretation_id","interp-",req.model_dump(),"human-interpretation.added",{"human_authored":True,"scope_bounded":True,"truth_not_promoted":True})
    def set_state(self,sid,req:CrossStudyStateRequest):
        rec=self.get(sid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(sid,"review.state",req.actor_ref,{"state":req.state}); return self.get(sid)
    def study_matrix(self,sid):
        rec=self.get(sid); rows=[]
        for s in rec["studies"]:
            rows.append({k:s.get(k) for k in ["study_id","study_ref","label","design","population_context","sample_size","intervention_exposure","comparator","outcome","effect_measure","estimate","standard_error","ci_lower","ci_upper","direction","disposition","reproduction_replication_id"]})
        return {"schema":CROSS_STUDY_SYNTHESIS_SCHEMA,"cross_study_synthesis_id":sid,"rows":rows,"governance":{"matrix_is_descriptive_not_meta_analytic_result":True,"cross_study_comparability_not_inferred":True}}
    def evidence_landscape(self,sid):
        rec=self.get(sid); included=[x for x in rec["studies"] if x.get("disposition")=="included"]
        def counts(key):
            out={}
            for x in included:
                v=str(x.get(key) or "unspecified"); out[v]=out.get(v,0)+1
            return out
        return {"schema":CROSS_STUDY_SYNTHESIS_SCHEMA,"cross_study_synthesis_id":sid,"included_study_count":len(included),"directions":counts("direction"),"designs":counts("design"),"outcomes":counts("outcome"),"effect_measures":counts("effect_measure"),"governance":{"counts_are_descriptive":True,"strength_of_evidence_not_inferred":True,"publication_bias_not_inferred":True}}
    def contradiction_map(self,sid):
        rec=self.get(sid); groups={}
        for x in rec["studies"]:
            if x.get("disposition")!="included": continue
            key=(str(x.get("outcome") or "unspecified"),str(x.get("effect_measure") or "unspecified")); groups.setdefault(key,[]).append({"study_id":x["study_id"],"direction":x.get("direction","not-assessed"),"estimate":x.get("estimate")})
        items=[]
        for (outcome,measure),studies in groups.items():
            dirs=sorted({x["direction"] for x in studies if x["direction"]!="not-assessed"}); items.append({"outcome":outcome,"effect_measure":measure,"studies":studies,"observed_directions":dirs,"directional_variation":len(dirs)>1,"contradiction_not_inferred":True})
        return {"schema":CROSS_STUDY_SYNTHESIS_SCHEMA,"cross_study_synthesis_id":sid,"groups":items,"governance":{"directional_variation_is_signal_for_review_not_contradiction_verdict":True}}
    def meta_research_summary(self,sid):
        rec=self.get(sid); by={}
        for x in rec["meta_research_observations"]: by.setdefault(x["category"],[]).append(x)
        return {"schema":CROSS_STUDY_SYNTHESIS_SCHEMA,"cross_study_synthesis_id":sid,"categories":by,"governance":{"observations_remain_attributed_and_scope_bounded":True,"researcher_motive_not_inferred":True,"misconduct_not_inferred":True}}
    def readiness(self,sid):
        rec=self.get(sid); included=[x for x in rec["studies"] if x.get("disposition")=="included"]; approved=[x for x in rec["synthesis_plans"] if self._approved(rec,"synthesis-plan",x["synthesis_plan_id"])]
        blockers=[]
        if len(included)<2: blockers.append("fewer-than-two-human-included-studies")
        if not rec["synthesis_dimensions"]: blockers.append("cross-study-comparability-dimensions-not-declared")
        if not approved: blockers.append("synthesis-plan-awaits-human-approval")
        return {"schema":CROSS_STUDY_SYNTHESIS_SCHEMA,"cross_study_synthesis_id":sid,"ready_for_execution_handoff":not blockers,"included_study_count":len(included),"approved_synthesis_plan_count":len(approved),"blockers":blockers,"governance":{"readiness_is_structural_not_scientific_validity":True,"execution_and_scholarly_judgment_remain_external":True}}
    def runtime_handoffs(self,sid):
        rec=self.get(sid); included=[x for x in rec["studies"] if x.get("disposition")=="included"]; packets=[]
        for p in rec["synthesis_plans"]:
            if not self._approved(rec,"synthesis-plan",p["synthesis_plan_id"]): continue
            packets.append({"schema":"sc-research-librarian-cross-study-synthesis-runtime-handoff/1.0","handoff_id":_id("handoff-",{"sid":sid,"pid":p["synthesis_plan_id"]}),"cross_study_synthesis_id":sid,"synthesis_plan":p,"included_studies":included,"synthesis_dimensions":rec["synthesis_dimensions"],"bias_assessments":rec["bias_assessments"],"target":p.get("runtime_target") or "workspace","execution_performed":False,"scholarly_interpretation_performed":False,"truth_promoted":False})
        return {"cross_study_synthesis_id":sid,"packets":packets,"governance":{"specialist_runtime_executes":True,"librarian_does_not_execute_meta_analysis":True}}
    def core_candidate(self,sid):
        rec=self.get(sid); return {"schema":"sc-research-librarian-core-candidate/1.0","object_type":"cross-study-synthesis-plan","source_id":sid,"source_hash":rec["record_hash"],"payload":{"project":rec,"study_matrix":self.study_matrix(sid),"evidence_landscape":self.evidence_landscape(sid),"contradiction_map":self.contradiction_map(sid),"meta_research_summary":self.meta_research_summary(sid)},"requires_core_governance":True,"pooled_effect_not_computed":True,"scientific_validity_not_certified":True,"truth_promoted":False}
    def freeze_snapshot(self,req:CrossStudySnapshotRequest):
        rec=self.get(req.cross_study_synthesis_id); payload={"schema":CROSS_STUDY_SYNTHESIS_SNAPSHOT_SCHEMA,"cross_study_synthesis_id":req.cross_study_synthesis_id,"record":rec,"study_matrix":self.study_matrix(req.cross_study_synthesis_id),"evidence_landscape":self.evidence_landscape(req.cross_study_synthesis_id),"contradiction_map":self.contradiction_map(req.cross_study_synthesis_id),"meta_research_summary":self.meta_research_summary(req.cross_study_synthesis_id),"readiness":self.readiness(req.cross_study_synthesis_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_record_not_truth_certification":True}}
        h=_sha(payload); sn="xstudysnap-"+h[:32]; payload.update({"snapshot_id":sn,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_cross_study_synthesis_snapshots(snapshot_id,cross_study_synthesis_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sn,req.cross_study_synthesis_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO cross_study_synthesis_snapshots(snapshot_id,cross_study_synthesis_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sn,req.cross_study_synthesis_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.cross_study_synthesis_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sn,"snapshot_hash":h}); return payload

def capabilities():
    return {"schema":CROSS_STUDY_SYNTHESIS_SCHEMA,"release":settings.release_version,"milestone":"11.6","durable":True,"study_registry":True,"human_study_disposition":True,"cross_study_comparability_dimensions":True,"human_risk_of_bias_assessment":True,"meta_research_observations":True,"synthesis_planning":True,"descriptive_evidence_landscape":True,"directional_variation_mapping":True,"specialist_runtime_handoffs":True,"human_interpretation":True,"core_candidate":True,"immutable_snapshot":True,"specialist_runtimes_own_meta_analysis_execution":True,"platform_core_remains_governed_research_object_authority":True,"automatic_study_inclusion":False,"automatic_risk_of_bias_judgment":False,"automatic_meta_analysis":False,"automatic_publication_bias_verdict":False,"automatic_claim_acceptance":False,"automatic_causal_inference":False,"automatic_execution":False,"automatic_truth_promotion":False}

_store:CrossStudySynthesisMetaResearchStore|None=None
def get_cross_study_synthesis_meta_research_store()->CrossStudySynthesisMetaResearchStore:
    global _store
    if _store is None: _store=CrossStudySynthesisMetaResearchStore()
    return _store
