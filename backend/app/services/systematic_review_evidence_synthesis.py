from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib, json, sqlite3, threading
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from ..database_identity import validate_schema_name
from ..contracts.systematic_review_evidence_synthesis import (
    SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,
    SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SNAPSHOT_SCHEMA,
    SystematicReviewCreateRequest, ReviewCandidateAddRequest,
    ReviewScreeningDecisionRequest, ReviewExtractionRequest,
    ReviewBiasAssessmentRequest, ReviewEvidenceGradeRequest,
    ReviewSynthesisPlanRequest, SystematicReviewStateRequest,
    SystematicReviewSnapshotRequest,
)
from .evidence_search_strategy import get_evidence_search_strategy_store
from .research_question_hypothesis import get_research_question_hypothesis_store
from .research_design_methodology import get_research_design_methodology_store

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

class SystematicReviewEvidenceSynthesisStore:
    def __init__(self, sqlite_path:Path|None=None, search_store:Any|None=None, question_store:Any|None=None, design_store:Any|None=None)->None:
        self.backend="postgres" if settings.database_backend=="postgres" and sqlite_path is None else "sqlite"
        self.sqlite_path=sqlite_path or (settings.data_dir/"systematic_review_evidence_synthesis.sqlite3")
        self.database_schema=validate_schema_name(settings.database_schema)
        self.search_store=search_store; self.question_store=question_store; self.design_store=design_store
        self._lock=threading.RLock()
        if self.backend=="postgres":
            if psycopg is None or Jsonb is None: raise RuntimeError("Postgres systematic-review storage requires psycopg.")
            self._migrate_postgres()
        else:
            self.sqlite_path.parent.mkdir(parents=True,exist_ok=True); self._migrate_sqlite()
    def _searches(self): return self.search_store or get_evidence_search_strategy_store()
    def _questions(self): return self.question_store or get_research_question_hypothesis_store()
    def _designs(self): return self.design_store or get_research_design_methodology_store()
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
CREATE TABLE IF NOT EXISTS systematic_reviews(review_id TEXT PRIMARY KEY,record_json TEXT NOT NULL,record_hash TEXT NOT NULL,created_utc TEXT NOT NULL,updated_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS systematic_review_events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,review_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload_json TEXT NOT NULL,event_hash TEXT NOT NULL,created_utc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS systematic_review_snapshots(snapshot_id TEXT PRIMARY KEY,review_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record_json TEXT NOT NULL,created_utc TEXT NOT NULL);
""")
    def _migrate_postgres(self)->None:
        with self._postgres(True) as c:
            for ddl in [
                "CREATE TABLE IF NOT EXISTS sc_rl_systematic_reviews(review_id TEXT PRIMARY KEY,record JSONB NOT NULL,record_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now(),updated_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE TABLE IF NOT EXISTS sc_rl_systematic_review_events(event_id BIGSERIAL PRIMARY KEY,review_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_ref TEXT NOT NULL,payload JSONB NOT NULL,event_hash TEXT NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
                "CREATE INDEX IF NOT EXISTS idx_sc_rl_systematic_review_events_review ON sc_rl_systematic_review_events(review_id)",
                "CREATE TABLE IF NOT EXISTS sc_rl_systematic_review_snapshots(snapshot_id TEXT PRIMARY KEY,review_id TEXT NOT NULL,snapshot_hash TEXT NOT NULL,record JSONB NOT NULL,created_utc TIMESTAMPTZ NOT NULL DEFAULT now())",
            ]: c.execute(ddl)
            c.commit()
    def _event(self,rid:str,typ:str,actor:str,payload:dict[str,Any])->None:
        created=_now(); h=_sha({"review_id":rid,"event_type":typ,"actor_ref":actor,"payload":payload,"created_utc":created})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_systematic_review_events(review_id,event_type,actor_ref,payload,event_hash,created_utc) VALUES(%s,%s,%s,%s,%s,%s)",(rid,typ,actor,Jsonb(payload),h,created)); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT INTO systematic_review_events(review_id,event_type,actor_ref,payload_json,event_hash,created_utc) VALUES(?,?,?,?,?,?)",(rid,typ,actor,_json(payload),h,created))
    def _save(self,rec:dict[str,Any])->dict[str,Any]:
        rec["updated_utc"]=_now(); rec["record_hash"]=_sha({k:v for k,v in rec.items() if k!="record_hash"})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_systematic_reviews(review_id,record,record_hash,created_utc,updated_utc) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(review_id) DO UPDATE SET record=EXCLUDED.record,record_hash=EXCLUDED.record_hash,updated_utc=EXCLUDED.updated_utc",(rec["review_id"],Jsonb(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"])); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR REPLACE INTO systematic_reviews(review_id,record_json,record_hash,created_utc,updated_utc) VALUES(?,?,?,?,?)",(rec["review_id"],_json(rec),rec["record_hash"],rec["created_utc"],rec["updated_utc"]))
        return rec
    def get(self,rid:str)->dict[str,Any]:
        if self.backend=="postgres":
            with self._postgres() as c: row=c.execute("SELECT record FROM sc_rl_systematic_reviews WHERE review_id=%s",(rid,)).fetchone()
            if not row: raise ValueError("Systematic review not found.")
            return dict(row["record"])
        with self._lock,self._sqlite() as c: row=c.execute("SELECT record_json FROM systematic_reviews WHERE review_id=?",(rid,)).fetchone()
        if not row: raise ValueError("Systematic review not found.")
        return json.loads(row["record_json"])
    def _search_context(self,sid:str)->dict[str,Any]:
        if not sid: return {}
        return self._searches().get(sid)
    def _scaffold_fields(self)->list[str]:
        return ["citation","publication_year","study_design","population","sample_size","exposure_or_intervention","comparator","outcomes","effect_estimates","follow_up","limitations","funding_or_conflicts","source_locator_refs"]
    def create(self,req:SystematicReviewCreateRequest)->dict[str,Any]:
        body=req.model_dump(); actor=body.pop("actor_ref"); search={}
        if body.get("evidence_search_strategy_id"):
            search=self._search_context(body["evidence_search_strategy_id"])
            body["question_plan_id"]=body.get("question_plan_id") or search.get("question_plan_id","")
            body["research_design_plan_id"]=body.get("research_design_plan_id") or search.get("research_design_plan_id","")
            body["review_question"]=body.get("review_question") or search.get("research_question","")
            body["inclusion_criteria"]=body.get("inclusion_criteria") or list(search.get("inclusion_criteria") or [])
            body["exclusion_criteria"]=body.get("exclusion_criteria") or list(search.get("exclusion_criteria") or [])
            body["evidence_requirements"]=body.get("evidence_requirements") or list(search.get("evidence_requirements") or [])
        if body.pop("scaffold_protocol"):
            body["extraction_fields"]=_uniq((body.get("extraction_fields") or [])+self._scaffold_fields())
        else: body["extraction_fields"]=_uniq(body.get("extraction_fields") or [])
        seed={k:v for k,v in body.items() if k not in {"metadata"}}; rid=_id("review-",seed)
        try: return self.get(rid)
        except ValueError: pass
        rec={"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"review_id":rid,**body,
             "search_protocol_fingerprint":search.get("record_hash","") if search else "",
             "candidates":[],"screening_decisions":[],"extractions":[],"bias_assessments":[],"evidence_grades":[],"synthesis_plans":[],
             "review":{"state":"draft","note":"","actor_ref":actor,"updated_utc":_now()},
             "created_utc":_now(),"updated_utc":_now(),
             "governance":{"human_screening_decisions_required":True,"human_bias_assessment_required":True,"human_evidence_grading_required":True,"automatic_study_inclusion":False,"automatic_risk_of_bias_judgment":False,"automatic_evidence_certainty_grading":False,"automatic_meta_analysis_execution":False,"automatic_truth_promotion":False,"knowledge_library_remains_source_authority":True,"platform_core_remains_governed_object_authority":True}}
        self._save(rec); self._event(rid,"review.created",actor,{"evidence_search_strategy_id":rec.get("evidence_search_strategy_id","")}); return self.get(rid)
    def add_candidate(self,rid:str,req:ReviewCandidateAddRequest)->dict[str,Any]:
        rec=self.get(rid); body=req.model_dump(); actor=body.pop("actor_ref"); cid=_id("review-study-",{"review_id":rid,"source_ref":body["source_ref"],"identifiers":body.get("identifiers",{})})
        item={"candidate_id":cid,**body,"screening_status":"unscreened","created_utc":_now()}
        if not any(x["candidate_id"]==cid for x in rec["candidates"]): rec["candidates"].append(item); self._save(rec); self._event(rid,"candidate.added",actor,{"candidate_id":cid,"source_ref":body["source_ref"]})
        return self.get(rid)
    def screen(self,rid:str,req:ReviewScreeningDecisionRequest)->dict[str,Any]:
        rec=self.get(rid)
        if not any(x["candidate_id"]==req.candidate_id for x in rec["candidates"]): raise ValueError("Review candidate not found.")
        body=req.model_dump(); actor=body.pop("actor_ref"); reviewer=body.get("reviewer_ref") or actor
        key={"review_id":rid,"candidate_id":body["candidate_id"],"stage":body["stage"],"reviewer_ref":reviewer,"decision":body["decision"],"reason_code":body.get("reason_code","")}
        did=_id("screening-",key); item={"decision_id":did,**body,"reviewer_ref":reviewer,"decided_utc":_now()}
        if not any(x["decision_id"]==did for x in rec["screening_decisions"]): rec["screening_decisions"].append(item)
        latest={(x["candidate_id"],x["stage"]):x for x in rec["screening_decisions"]}
        for cand in rec["candidates"]:
            if cand["candidate_id"]==req.candidate_id:
                full=latest.get((req.candidate_id,"full-text")); ta=latest.get((req.candidate_id,"title-abstract"))
                d=full or ta; cand["screening_status"]=(d or {}).get("decision","unscreened")
        self._save(rec); self._event(rid,"screening.decision-recorded",actor,{"decision_id":did,"candidate_id":req.candidate_id,"stage":req.stage,"decision":req.decision}); return self.get(rid)
    def add_extraction(self,rid:str,req:ReviewExtractionRequest)->dict[str,Any]:
        rec=self.get(rid)
        if not any(x["candidate_id"]==req.candidate_id for x in rec["candidates"]): raise ValueError("Review candidate not found.")
        body=req.model_dump(); actor=body.pop("actor_ref"); eid=_id("extract-",{"review_id":rid,"candidate_id":body["candidate_id"],"fields":body["fields"],"outcomes":body["outcomes"],"source_locator_refs":body["source_locator_refs"]})
        item={"extraction_id":eid,**body,"extracted_utc":_now(),"human_recorded":True}
        rec["extractions"]=[x for x in rec["extractions"] if x["candidate_id"]!=body["candidate_id"]]
        rec["extractions"].append(item); self._save(rec); self._event(rid,"extraction.recorded",actor,{"extraction_id":eid,"candidate_id":body["candidate_id"]}); return self.get(rid)
    def add_bias_assessment(self,rid:str,req:ReviewBiasAssessmentRequest)->dict[str,Any]:
        rec=self.get(rid)
        if not any(x["candidate_id"]==req.candidate_id for x in rec["candidates"]): raise ValueError("Review candidate not found.")
        body=req.model_dump(); actor=body.pop("actor_ref"); bid=_id("bias-",{"review_id":rid,**body})
        item={"assessment_id":bid,**body,"assessed_utc":_now(),"human_judgment":True}
        rec["bias_assessments"]=[x for x in rec["bias_assessments"] if not(x["candidate_id"]==body["candidate_id"] and x["instrument"]==body["instrument"] and x["domain"]==body["domain"])]
        rec["bias_assessments"].append(item); self._save(rec); self._event(rid,"bias-assessment.recorded",actor,{"assessment_id":bid,"candidate_id":body["candidate_id"],"judgment":body["judgment"]}); return self.get(rid)
    def add_evidence_grade(self,rid:str,req:ReviewEvidenceGradeRequest)->dict[str,Any]:
        rec=self.get(rid); body=req.model_dump(); actor=body.pop("actor_ref"); gid=_id("grade-",{"review_id":rid,**body})
        item={"grade_id":gid,**body,"graded_utc":_now(),"human_judgment":True}
        rec["evidence_grades"]=[x for x in rec["evidence_grades"] if not(x["outcome_ref"]==body["outcome_ref"] and x["framework"]==body["framework"])]
        rec["evidence_grades"].append(item); self._save(rec); self._event(rid,"evidence-grade.recorded",actor,{"grade_id":gid,"outcome_ref":body["outcome_ref"],"certainty":body["certainty"]}); return self.get(rid)
    def add_synthesis_plan(self,rid:str,req:ReviewSynthesisPlanRequest)->dict[str,Any]:
        rec=self.get(rid); body=req.model_dump(); actor=body.pop("actor_ref")
        known={x["candidate_id"] for x in rec["candidates"]}; missing=[x for x in body["included_candidate_ids"] if x not in known]
        if missing: raise ValueError("Unknown candidate IDs in synthesis plan: "+", ".join(missing))
        sid=_id("synthesis-",{"review_id":rid,**body}); item={"synthesis_plan_id":sid,**body,"created_utc":_now(),"execution_status":"not-executed"}
        if not any(x["synthesis_plan_id"]==sid for x in rec["synthesis_plans"]): rec["synthesis_plans"].append(item); self._save(rec); self._event(rid,"synthesis-plan.created",actor,{"synthesis_plan_id":sid,"synthesis_type":body["synthesis_type"]})
        return self.get(rid)
    def set_review_state(self,rid:str,req:SystematicReviewStateRequest)->dict[str,Any]:
        rec=self.get(rid); rec["review"]={"state":req.state,"note":req.note,"actor_ref":req.actor_ref,"updated_utc":_now()}; self._save(rec); self._event(rid,"review-state.changed",req.actor_ref,{"state":req.state,"note":req.note}); return self.get(rid)
    def flow(self,rid:str)->dict[str,Any]:
        rec=self.get(rid); candidates=rec.get("candidates",[]); decisions=rec.get("screening_decisions",[])
        latest={}
        for d in decisions: latest[(d["candidate_id"],d["stage"])]=d
        dup_groups={c.get("duplicate_group_ref") for c in candidates if c.get("duplicate_group_ref")}
        title_dec=[d for (cid,stage),d in latest.items() if stage=="title-abstract"]
        full_dec=[d for (cid,stage),d in latest.items() if stage=="full-text"]
        included=[]
        for c in candidates:
            full=latest.get((c["candidate_id"],"full-text")); ta=latest.get((c["candidate_id"],"title-abstract")); d=full or ta
            if d and d["decision"]=="include": included.append(c["candidate_id"])
        reported=sum(int(x.get("result_count",0)) for x in (self._search_context(rec.get("evidence_search_strategy_id","")) or {}).get("execution_receipts",[])) if rec.get("evidence_search_strategy_id") else 0
        return {"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"review_id":rid,"flow":{"search_results_reported":reported,"candidates_registered":len(candidates),"duplicate_groups_declared":len(dup_groups),"title_abstract_decisions":len(title_dec),"full_text_decisions":len(full_dec),"included_candidates":len(included),"included_candidate_ids":included},"governance":{"flow_is_accounting_not_prisma_certification":True,"screening_decisions_are_human_records":True}}
    def extraction_matrix(self,rid:str)->dict[str,Any]:
        rec=self.get(rid); rows=[]; cmap={x["candidate_id"]:x for x in rec.get("candidates",[])}
        for x in rec.get("extractions",[]): rows.append({"candidate":cmap.get(x["candidate_id"],{"candidate_id":x["candidate_id"]}),"extraction":x})
        return {"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"review_id":rid,"declared_fields":rec.get("extraction_fields",[]),"rows":rows,"governance":{"matrix_contains_recorded_extractions_not_verified_facts":True}}
    def bias_summary(self,rid:str)->dict[str,Any]:
        rec=self.get(rid); counts={}
        for x in rec.get("bias_assessments",[]): counts[x["judgment"]]=counts.get(x["judgment"],0)+1
        return {"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"review_id":rid,"assessment_count":len(rec.get("bias_assessments",[])),"judgment_counts":counts,"assessments":rec.get("bias_assessments",[]),"governance":{"summary_does_not_compute_or_override_bias_judgments":True,"human_bias_assessment_required":True}}
    def certainty_summary(self,rid:str)->dict[str,Any]:
        rec=self.get(rid); counts={}
        for x in rec.get("evidence_grades",[]): counts[x["certainty"]]=counts.get(x["certainty"],0)+1
        return {"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"review_id":rid,"grade_count":len(rec.get("evidence_grades",[])),"certainty_counts":counts,"grades":rec.get("evidence_grades",[]),"governance":{"summary_does_not_compute_or_override_certainty_grades":True,"human_evidence_grading_required":True}}
    def readiness(self,rid:str)->dict[str,Any]:
        rec=self.get(rid); flow=self.flow(rid); included=flow["flow"]["included_candidate_ids"]; extracted={x["candidate_id"] for x in rec.get("extractions",[])}
        dimensions={"search_strategy_bound":bool(rec.get("evidence_search_strategy_id")),"protocol_criteria_defined":bool(rec.get("inclusion_criteria")) and bool(rec.get("exclusion_criteria")),"candidates_registered":bool(rec.get("candidates")),"screening_recorded":bool(rec.get("screening_decisions")),"included_studies_present":bool(included),"included_studies_extracted":bool(included) and all(x in extracted for x in included),"synthesis_plan_defined":bool(rec.get("synthesis_plans")),"human_review_approved":rec.get("review",{}).get("state")=="approved"}
        review_required=["search_strategy_bound","protocol_criteria_defined"]
        synthesis_required=["included_studies_present","included_studies_extracted","synthesis_plan_defined","human_review_approved"]
        return {"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"review_id":rid,"ready_for_screening_review":all(dimensions[x] for x in review_required),"ready_for_synthesis_handoff":all(dimensions[x] for x in synthesis_required),"dimensions":dimensions,"blockers":[x.replace("_","-") for x in synthesis_required if not dimensions[x]],"governance":{"readiness_is_structural_not_evidence_sufficiency_or_scientific_validity":True,"human_approval_required_before_synthesis_handoff":True}}
    def synthesis_handoffs(self,rid:str)->dict[str,Any]:
        rec=self.get(rid); ready=self.readiness(rid)["ready_for_synthesis_handoff"]; packets=[]
        for plan in rec.get("synthesis_plans",[]):
            packets.append({"handoff_id":_id("synthesis-handoff-",{"review_id":rid,"synthesis_plan_id":plan["synthesis_plan_id"],"target":plan["execution_target"]}),"target":plan["execution_target"],"review_id":rid,"synthesis_plan":plan,"extraction_matrix":self.extraction_matrix(rid),"bias_summary":self.bias_summary(rid),"certainty_summary":self.certainty_summary(rid),"status":"human-approved-ready" if ready else "requires-human-review"})
        return {"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"review_id":rid,"handoffs":packets,"delivery_performed":False,"analysis_executed":False,"meta_analysis_executed":False,"governance":{"workspace_lab_or_analytics_runtime_executes_computation":True,"automatic_meta_analysis_execution":False,"automatic_effect_interpretation":False}}
    def core_candidate(self,rid:str)->dict[str,Any]:
        rec=self.get(rid); approved=rec.get("review",{}).get("state")=="approved"
        candidate={"candidate_id":_id("corecand-",{"review_id":rid,"type":"systematic-review-evidence-synthesis"}),"object_type":"systematic-review-evidence-synthesis","source_review_id":rid,"payload":{"question_plan_id":rec.get("question_plan_id",""),"research_design_plan_id":rec.get("research_design_plan_id",""),"evidence_search_strategy_id":rec.get("evidence_search_strategy_id",""),"review_question":rec.get("review_question",""),"flow":self.flow(rid),"extraction_matrix":self.extraction_matrix(rid),"bias_summary":self.bias_summary(rid),"certainty_summary":self.certainty_summary(rid),"synthesis_plans":rec.get("synthesis_plans",[])}}
        return {"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"review_id":rid,"candidate":candidate,"handoff_status":"human-approved-candidate" if approved else "requires-human-approval","promotion_performed":False,"governance":{"platform_core_remains_authority":True,"automatic_core_write":False,"systematic_review_record_is_not_truth_certification":True}}
    def freeze_snapshot(self,req:SystematicReviewSnapshotRequest)->dict[str,Any]:
        rec=self.get(req.review_id); payload={"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SNAPSHOT_SCHEMA,"review_id":req.review_id,"review":rec,"flow":self.flow(req.review_id),"extraction_matrix":self.extraction_matrix(req.review_id),"bias_summary":self.bias_summary(req.review_id),"certainty_summary":self.certainty_summary(req.review_id),"readiness":self.readiness(req.review_id),"synthesis_handoffs":self.synthesis_handoffs(req.review_id),"core_candidate":self.core_candidate(req.review_id),"label":req.label,"note":req.note,"frozen_utc":_now(),"governance":{"snapshot_is_reproducible_review_record_not_evidence_certification":True}}
        h=_sha(payload); sid="sres-snap-"+h[:32]; payload.update({"snapshot_id":sid,"snapshot_hash":h})
        if self.backend=="postgres":
            with self._postgres() as c: c.execute("INSERT INTO sc_rl_systematic_review_snapshots(snapshot_id,review_id,snapshot_hash,record) VALUES(%s,%s,%s,%s) ON CONFLICT(snapshot_id) DO NOTHING",(sid,req.review_id,h,Jsonb(payload))); c.commit()
        else:
            with self._lock,self._sqlite() as c: c.execute("INSERT OR IGNORE INTO systematic_review_snapshots(snapshot_id,review_id,snapshot_hash,record_json,created_utc) VALUES(?,?,?,?,?)",(sid,req.review_id,h,_json(payload),payload["frozen_utc"]))
        self._event(req.review_id,"snapshot.frozen",req.actor_ref,{"snapshot_id":sid,"snapshot_hash":h}); return payload

def capabilities()->dict[str,Any]:
    return {"schema":SYSTEMATIC_REVIEW_EVIDENCE_SYNTHESIS_SCHEMA,"release":settings.release_version,"milestone":"10.4","durable":True,"evidence_search_strategy_integration":True,"question_and_methodology_lineage":True,"screening_candidate_registry":True,"two_stage_screening":True,"review_flow_accounting":True,"structured_extraction_matrix":True,"risk_of_bias_assessment_registry":True,"evidence_certainty_grade_registry":True,"narrative_and_quantitative_synthesis_planning":True,"specialist_runtime_synthesis_handoffs":True,"platform_core_synthesis_candidate":True,"human_screening_decisions_required":True,"human_bias_assessment_required":True,"human_evidence_grading_required":True,"automatic_study_inclusion":False,"automatic_risk_of_bias_judgment":False,"automatic_evidence_certainty_grading":False,"automatic_meta_analysis_execution":False,"automatic_truth_promotion":False,"knowledge_library_remains_source_authority":True,"platform_core_remains_authority":True}

_store:SystematicReviewEvidenceSynthesisStore|None=None
def get_systematic_review_evidence_synthesis_store()->SystematicReviewEvidenceSynthesisStore:
    global _store
    if _store is None: _store=SystematicReviewEvidenceSynthesisStore()
    return _store
